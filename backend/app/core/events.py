"""Application lifecycle event handlers.

使用 ServiceRegistry 统一管理生命周期，替代手动清理 lru_cache。
"""

import logging
from typing import Callable

from domains.mcp_core.logging import init_log_store, shutdown_log_store, get_logger
from domains.mcp_core.server.sse import get_task_manager
from domains.core import get_service_registry, register_core_services

logger = get_logger(__name__)


def create_start_handler() -> Callable:
    """Create startup event handler."""

    async def start_app() -> None:
        logger.info("api_starting", component="api")

        # Initialize log store for PostgreSQL logging
        try:
            await init_log_store()
            logger.info("log_store_initialized", component="log_store")
        except Exception as e:
            logger.warning("log_store_init_skipped", component="log_store", error=str(e))

        # Initialize SSE task manager (background cleanup)
        try:
            task_manager = get_task_manager()
            await task_manager.start()
            logger.info("sse_task_manager_initialized", component="sse")
        except Exception as e:
            logger.warning("sse_task_manager_init_skipped", component="sse", error=str(e))

        # 注册并初始化核心服务
        try:
            registry = register_core_services()

            # 预热关键服务
            factor_store = registry.get("factor_store")

            # Sync factor code from files to database
            sync_stats = factor_store.sync_code_from_files()
            logger.info(
                "factor_code_synced",
                component="factor_store",
                created=sync_stats.get("created", 0),
                updated=sync_stats.get("updated", 0),
                unchanged=sync_stats.get("unchanged", 0),
            )

            # Sync private data from files (factors metadata, notes, strategies, experiences, tags)
            # 使用 full_sync=True 完全同步，以文件为准
            try:
                from domains.mcp_core.sync import SyncManager
                sync_manager = SyncManager()

                # Only restore if private-data directory exists
                if sync_manager.data_dir.exists():
                    restore_stats = sync_manager.restore(full_sync=True)
                    for data_type, stats in restore_stats.items():
                        created = stats.get("created", 0)
                        updated = stats.get("updated", 0)
                        deleted = stats.get("deleted", 0)
                        if created > 0 or updated > 0 or deleted > 0:
                            logger.info(
                                f"{data_type}_synced",
                                component="sync_manager",
                                created=created,
                                updated=updated,
                                deleted=deleted,
                            )
            except Exception as e:
                logger.warning("private_data_sync_skipped", component="sync_manager", error=str(e))

            stats = factor_store.get_stats()
            logger.info(
                "factor_store_initialized",
                component="factor_store",
                total_factors=stats.get("total", 0),
            )

            # Initialize data loader (optional, may fail if data not present)
            try:
                loader = registry.get("data_loader")
                symbols = loader.get_symbols()
                logger.info(
                    "data_loader_initialized",
                    component="data_loader",
                    symbol_count=len(symbols),
                )
            except Exception as e:
                logger.warning("data_loader_init_skipped", component="data_loader", error=str(e))

            logger.info(
                "services_initialized",
                component="registry",
                services=registry.initialized_services,
            )

        except Exception as e:
            logger.error("service_initialization_error", component="registry", error=str(e))

        logger.info("api_started", component="api", status="success")

    return start_app


def create_stop_handler() -> Callable:
    """Create shutdown event handler."""

    async def stop_app() -> None:
        logger.info("api_stopping", component="api")

        # Export private data to files before shutdown
        try:
            from domains.mcp_core.sync import SyncManager
            sync_manager = SyncManager()
            export_stats = sync_manager.export_all()
            total_exported = sum(s.get("exported", 0) for s in export_stats.values())
            if total_exported > 0:
                logger.info(
                    "private_data_exported",
                    component="sync_manager",
                    total=total_exported,
                )
        except Exception as e:
            logger.warning("private_data_export_error", component="sync_manager", error=str(e))

        # Stop SSE task manager
        try:
            task_manager = get_task_manager()
            await task_manager.stop()
            logger.info("sse_task_manager_stopped", component="sse")
        except Exception as e:
            logger.warning("sse_task_manager_stop_error", component="sse", error=str(e))

        # Shutdown log store (flush pending logs)
        try:
            await shutdown_log_store()
            logger.info("log_store_stopped", component="log_store")
        except Exception as e:
            logger.warning("log_store_stop_error", component="log_store", error=str(e))

        # 使用 ServiceRegistry 统一关闭所有服务
        try:
            registry = get_service_registry()
            await registry.shutdown()
        except Exception as e:
            logger.warning("service_registry_stop_error", component="registry", error=str(e))

        logger.info("api_stopped", component="api", status="success")

    return stop_app
