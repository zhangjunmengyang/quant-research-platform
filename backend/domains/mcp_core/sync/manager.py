"""
同步管理器

统一管理所有数据类型的同步操作。
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .factor_sync import FactorSyncService
from .note_sync import NoteSyncService
from .strategy_sync import StrategySyncService
from .experience_sync import ExperienceSyncService

logger = logging.getLogger(__name__)


class SyncManager:
    """
    数据同步管理器

    统一管理因子、笔记、策略、经验的同步操作。

    使用方式：
        manager = SyncManager()
        manager.export_all()       # 导出所有数据
        manager.import_all()       # 导入所有数据
        manager.export("factors")  # 导出指定类型
        manager.get_status()       # 获取同步状态
    """

    # 支持的数据类型
    DATA_TYPES = ["factors", "notes", "strategies", "experiences"]

    def __init__(self, private_data_dir: Optional[Path] = None):
        """
        初始化同步管理器

        Args:
            private_data_dir: 私有数据目录，默认为项目根目录下的 private-data/
        """
        if private_data_dir is None:
            from domains.mcp_core.paths import get_private_data_dir
            private_data_dir = get_private_data_dir()

        self.data_dir = private_data_dir
        self._services: Dict[str, Any] = {}
        self._initialized = False

    def _init_services(self) -> None:
        """延迟初始化同步服务"""
        if self._initialized:
            return

        try:
            # 因子同步
            from domains.factor_hub.core.store import get_factor_store
            factor_store = get_factor_store()
            self._services["factors"] = FactorSyncService(self.data_dir, factor_store)
        except Exception as e:
            logger.warning(f"factor_sync_service_init_error: {e}")
            self._services["factors"] = FactorSyncService(self.data_dir, None)

        try:
            # 笔记同步
            from domains.note_hub.core.store import get_note_store
            note_store = get_note_store()
            self._services["notes"] = NoteSyncService(self.data_dir, note_store)
        except Exception as e:
            logger.warning(f"note_sync_service_init_error: {e}")
            self._services["notes"] = NoteSyncService(self.data_dir, None)

        try:
            # 策略同步
            from domains.strategy_hub.services.strategy_store import get_strategy_store
            strategy_store = get_strategy_store()
            self._services["strategies"] = StrategySyncService(self.data_dir, strategy_store)
        except Exception as e:
            logger.warning(f"strategy_sync_service_init_error: {e}")
            self._services["strategies"] = StrategySyncService(self.data_dir, None)

        try:
            # 经验同步
            from domains.experience_hub.core.store import get_experience_store
            experience_store = get_experience_store()
            self._services["experiences"] = ExperienceSyncService(self.data_dir, experience_store)
        except Exception as e:
            logger.warning(f"experience_sync_service_init_error: {e}")
            self._services["experiences"] = ExperienceSyncService(self.data_dir, None)

        self._initialized = True

    def _get_service(self, data_type: str) -> Optional[Any]:
        """获取指定类型的同步服务"""
        self._init_services()
        return self._services.get(data_type)

    def export_all(self, overwrite: bool = False) -> Dict[str, Dict[str, int]]:
        """
        导出所有数据类型

        Args:
            overwrite: 是否覆盖已存在的文件

        Returns:
            {
                "factors": {"exported": N, "skipped": M, "errors": K},
                "notes": {...},
                ...
            }
        """
        results = {}
        for data_type in self.DATA_TYPES:
            service = self._get_service(data_type)
            if service:
                try:
                    results[data_type] = service.export_all(overwrite=overwrite)
                except Exception as e:
                    logger.error(f"export_{data_type}_error: {e}")
                    results[data_type] = {"errors": 1}
            else:
                results[data_type] = {"errors": 1}

        return results

    def import_all(self) -> Dict[str, Dict[str, int]]:
        """
        导入所有数据类型

        Returns:
            {
                "factors": {"created": N, "updated": M, "unchanged": K, "errors": L},
                "notes": {...},
                ...
            }
        """
        results = {}
        for data_type in self.DATA_TYPES:
            service = self._get_service(data_type)
            if service:
                try:
                    results[data_type] = service.import_all()
                except Exception as e:
                    logger.error(f"import_{data_type}_error: {e}")
                    results[data_type] = {"errors": 1}
            else:
                results[data_type] = {"errors": 1}

        return results

    def export(self, *data_types: str, overwrite: bool = False) -> Dict[str, Dict[str, int]]:
        """
        导出指定数据类型

        Args:
            data_types: 要导出的数据类型（factors, notes, strategies, experiences）
            overwrite: 是否覆盖已存在的文件

        Returns:
            导出统计
        """
        results = {}
        for data_type in data_types:
            if data_type not in self.DATA_TYPES:
                logger.warning(f"unknown_data_type: {data_type}")
                results[data_type] = {"errors": 1}
                continue

            service = self._get_service(data_type)
            if service:
                try:
                    results[data_type] = service.export_all(overwrite=overwrite)
                except Exception as e:
                    logger.error(f"export_{data_type}_error: {e}")
                    results[data_type] = {"errors": 1}
            else:
                results[data_type] = {"errors": 1}

        return results

    def import_(self, *data_types: str) -> Dict[str, Dict[str, int]]:
        """
        导入指定数据类型

        Args:
            data_types: 要导入的数据类型

        Returns:
            导入统计
        """
        results = {}
        for data_type in data_types:
            if data_type not in self.DATA_TYPES:
                logger.warning(f"unknown_data_type: {data_type}")
                results[data_type] = {"errors": 1}
                continue

            service = self._get_service(data_type)
            if service:
                try:
                    results[data_type] = service.import_all()
                except Exception as e:
                    logger.error(f"import_{data_type}_error: {e}")
                    results[data_type] = {"errors": 1}
            else:
                results[data_type] = {"errors": 1}

        return results

    def get_status(self) -> Dict[str, Any]:
        """
        获取所有数据类型的同步状态

        Returns:
            {
                "data_dir": "/path/to/private-data",
                "exists": True,
                "factors": {"db_count": N, "file_count": M, ...},
                "notes": {...},
                ...
            }
        """
        status = {
            "data_dir": str(self.data_dir),
            "exists": self.data_dir.exists(),
        }

        for data_type in self.DATA_TYPES:
            service = self._get_service(data_type)
            if service:
                try:
                    status[data_type] = service.get_status()
                except Exception as e:
                    logger.error(f"get_status_{data_type}_error: {e}")
                    status[data_type] = {"error": str(e)}
            else:
                status[data_type] = {"error": "service not available"}

        return status


# 便捷函数

def get_sync_manager(private_data_dir: Optional[Path] = None) -> SyncManager:
    """获取同步管理器实例"""
    return SyncManager(private_data_dir)
