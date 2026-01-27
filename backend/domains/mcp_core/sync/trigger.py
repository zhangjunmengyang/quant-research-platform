"""
同步触发器

提供从 Store 层触发实时同步的统一接口。
同步操作采用 Fire-and-Forget 模式：
- 同步失败不影响主业务逻辑
- 记录日志便于问题排查
"""

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SyncTrigger:
    """
    同步触发器

    封装对各 SyncService 的调用，提供统一的错误处理和日志。
    使用延迟初始化避免循环导入。
    """

    def __init__(self, private_data_dir: Optional[Path] = None):
        """
        初始化同步触发器

        Args:
            private_data_dir: 私有数据目录，默认为 private/
        """
        if private_data_dir is None:
            from domains.mcp_core.paths import get_private_data_dir
            private_data_dir = get_private_data_dir()

        self.data_dir = private_data_dir
        self._services: dict[str, Any] = {}

    def _get_service(self, service_type: str) -> Optional[Any]:
        """
        延迟初始化并获取同步服务

        Args:
            service_type: 服务类型 (strategy, factor, note, experience)

        Returns:
            对应的 SyncService 实例，或 None
        """
        if service_type in self._services:
            return self._services[service_type]

        try:
            if service_type == "strategy":
                from .strategy_sync import StrategySyncService
                from domains.strategy_hub.services.strategy_store import StrategyStore
                from domains.mcp_core.base import get_store_instance
                store = get_store_instance(StrategyStore)
                self._services["strategy"] = StrategySyncService(self.data_dir, store)

            elif service_type == "factor":
                from .factor_sync import FactorSyncService
                from domains.factor_hub.core.store import get_factor_store
                self._services["factor"] = FactorSyncService(self.data_dir, get_factor_store())

            elif service_type == "note":
                from .note_sync import NoteSyncService
                from domains.note_hub.core.store import get_note_store
                self._services["note"] = NoteSyncService(self.data_dir, get_note_store())

            elif service_type == "experience":
                from .experience_sync import ExperienceSyncService
                from domains.experience_hub.core.store import get_experience_store
                self._services["experience"] = ExperienceSyncService(self.data_dir, get_experience_store())

            elif service_type == "edge":
                from .edge_sync import EdgeSyncService
                from domains.mcp_core.edge.store import get_edge_store
                self._services["edge"] = EdgeSyncService(self.data_dir, get_edge_store())

        except Exception as e:
            logger.debug(f"sync_service_init_skipped: {service_type}, {e}")
            return None

        return self._services.get(service_type)

    def sync_strategy(self, strategy_id: str) -> bool:
        """
        同步策略到文件

        Args:
            strategy_id: 策略 UUID

        Returns:
            是否成功（失败不影响调用方）
        """
        try:
            service = self._get_service("strategy")
            if service and hasattr(service, 'export_single'):
                result = service.export_single(strategy_id)
                if result:
                    logger.debug(f"strategy_synced: {strategy_id}")
                return result
        except Exception as e:
            logger.warning(f"sync_strategy_failed: {strategy_id}, {e}")
        return False

    def sync_factor_metadata(self, filename: str) -> bool:
        """
        同步因子元数据到文件

        Args:
            filename: 因子文件名

        Returns:
            是否成功
        """
        try:
            service = self._get_service("factor")
            if service and hasattr(service, 'export_single'):
                result = service.export_single(filename)
                if result:
                    logger.debug(f"factor_metadata_synced: {filename}")
                return result
        except Exception as e:
            logger.warning(f"sync_factor_metadata_failed: {filename}, {e}")
        return False

    def sync_note(self, note_id: int) -> bool:
        """
        同步笔记到文件

        Args:
            note_id: 笔记 ID

        Returns:
            是否成功
        """
        try:
            service = self._get_service("note")
            if service and hasattr(service, 'export_single'):
                result = service.export_single(note_id)
                if result:
                    logger.debug(f"note_synced: {note_id}")
                return result
        except Exception as e:
            logger.warning(f"sync_note_failed: {note_id}, {e}")
        return False

    def sync_experience(self, experience_id: int) -> bool:
        """
        同步经验到文件

        Args:
            experience_id: 经验 ID

        Returns:
            是否成功
        """
        try:
            service = self._get_service("experience")
            if service and hasattr(service, 'export_single'):
                result = service.export_single(experience_id)
                if result:
                    logger.debug(f"experience_synced: {experience_id}")
                return result
        except Exception as e:
            logger.warning(f"sync_experience_failed: {experience_id}, {e}")
        return False

    def sync_tag(self, entity_type: str, entity_id: str) -> bool:
        """
        同步标签到文件

        Args:
            entity_type: 实体类型（data, factor, strategy 等）
            entity_id: 实体 ID

        Returns:
            是否成功
        """
        try:
            service = self._get_service("edge")
            if service and hasattr(service, 'export_single'):
                result = service.export_single(entity_type, entity_id)
                if result:
                    logger.debug(f"tag_synced: {entity_type}:{entity_id}")
                return result
        except Exception as e:
            logger.warning(f"sync_tag_failed: {entity_type}:{entity_id}, {e}")
        return False

    def sync_edge(self, edge: Any) -> bool:
        """
        同步知识边到文件

        Args:
            edge: KnowledgeEdge 对象

        Returns:
            是否成功
        """
        try:
            service = self._get_service("edge")
            if service and hasattr(service, 'export_edge'):
                result = service.export_edge(edge)
                if result:
                    logger.debug(f"edge_synced: {edge.source_id} -> {edge.target_id}")
                return result
        except Exception as e:
            logger.warning(f"sync_edge_failed: {edge.source_id} -> {edge.target_id}, {e}")
        return False


# 单例
_trigger: Optional[SyncTrigger] = None


def get_sync_trigger() -> SyncTrigger:
    """获取同步触发器单例"""
    global _trigger
    if _trigger is None:
        _trigger = SyncTrigger()
    return _trigger
