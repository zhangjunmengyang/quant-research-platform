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
        logger.info("Starting Quant Platform API...")

        # Initialize log store for PostgreSQL logging
        try:
            await init_log_store()
            logger.info("Log store initialized")
        except Exception as e:
            logger.warning(f"Log store init skipped: {e}")

        # Initialize SSE task manager (background cleanup)
        try:
            task_manager = get_task_manager()
            await task_manager.start()
            logger.info("SSE task manager initialized")
        except Exception as e:
            logger.warning(f"SSE task manager init skipped: {e}")

        # 注册并初始化核心服务
        try:
            registry = register_core_services()

            # 预热关键服务
            factor_store = registry.get("factor_store")

            # Sync factor code from files to database
            sync_stats = factor_store.sync_code_from_files()
            logger.info(
                f"Factor code synced: {sync_stats.get('created', 0)} created, "
                f"{sync_stats.get('updated', 0)} updated, "
                f"{sync_stats.get('unchanged', 0)} unchanged"
            )

            stats = factor_store.get_stats()
            logger.info(f"Factor store initialized: {stats.get('total', 0)} factors")

            # Initialize data loader (optional, may fail if data not present)
            try:
                loader = registry.get("data_loader")
                symbols = loader.get_symbols()
                logger.info(f"Data loader initialized: {len(symbols)} symbols")
            except Exception as e:
                logger.warning(f"Data loader init skipped: {e}")

            logger.info(f"Services initialized: {registry.initialized_services}")

        except Exception as e:
            logger.error(f"Service initialization error: {e}")

        logger.info("Quant Platform API started successfully")

    return start_app


def create_stop_handler() -> Callable:
    """Create shutdown event handler."""

    async def stop_app() -> None:
        logger.info("Shutting down Quant Platform API...")

        # Stop SSE task manager
        try:
            task_manager = get_task_manager()
            await task_manager.stop()
            logger.info("SSE task manager shutdown complete")
        except Exception as e:
            logger.warning(f"SSE task manager shutdown error: {e}")

        # Shutdown log store (flush pending logs)
        try:
            await shutdown_log_store()
            logger.info("Log store shutdown complete")
        except Exception as e:
            logger.warning(f"Log store shutdown error: {e}")

        # 使用 ServiceRegistry 统一关闭所有服务
        try:
            registry = get_service_registry()
            await registry.shutdown()
        except Exception as e:
            logger.warning(f"Service registry shutdown error: {e}")

        logger.info("Quant Platform API shutdown complete")

    return stop_app
