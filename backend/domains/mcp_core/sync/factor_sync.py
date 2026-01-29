"""
因子同步服务

将因子元数据在数据库和 YAML 文件之间同步。
注意：因子代码文件由 factor_store.sync_code_from_files() 处理，本服务只处理元数据。
"""

import logging
from pathlib import Path
from typing import Any

from .base import BaseSyncService

logger = logging.getLogger(__name__)


class FactorSyncService(BaseSyncService):
    """
    因子元数据同步服务

    文件结构：
        private/metadata/{filename}.yaml

    同步字段（不含 code_content）：
        - 基础：filename, factor_type, uuid
        - 元数据：style, formula, input_data, value_range, description, analysis
        - 评分：llm_score, ic, rank_ic
        - 回测：backtest_sharpe, backtest_ic, backtest_ir, turnover, decay, last_backtest_date
        - 分类：market_regime, best_holding_period, tags
        - 状态：verification_status, verify_note, excluded, exclude_reason
        - 代码质量：code_complexity
        - 参数分析：param_analysis
        - 时间戳：created_at, updated_at
    """

    # 需要同步的字段（不含 code_content 和 code_path）
    SYNC_FIELDS = [
        'filename', 'factor_type', 'uuid',
        'style', 'formula', 'input_data', 'value_range', 'description', 'analysis',
        'llm_score', 'ic', 'rank_ic',
        'backtest_sharpe', 'backtest_ic', 'backtest_ir', 'turnover', 'decay', 'last_backtest_date',
        'market_regime', 'best_holding_period', 'tags',
        'verification_status', 'verify_note', 'excluded', 'exclude_reason',
        'code_complexity',
        'param_analysis',
        'created_at', 'updated_at',
    ]

    def __init__(self, data_dir: Path, store: Any = None):
        """
        初始化因子同步服务

        Args:
            data_dir: 私有数据目录 (private/)
            store: FactorStore 实例
        """
        super().__init__(data_dir, store)
        self.metadata_dir = data_dir / "metadata"

    def export_all(self, overwrite: bool = False) -> dict[str, int]:
        """
        导出所有因子元数据到 YAML 文件

        Args:
            overwrite: 是否覆盖已存在的文件

        Returns:
            {"exported": N, "skipped": M, "errors": K}
        """
        stats = {"exported": 0, "skipped": 0, "errors": 0}

        if self.store is None:
            logger.warning("factor_sync_export_skipped: store is None")
            return stats

        try:
            factors = self.store.get_all(include_excluded=True)
        except Exception as e:
            logger.error(f"factor_sync_export_error: {e}")
            stats["errors"] = 1
            return stats

        self.ensure_dir(self.metadata_dir)

        for factor in factors:
            filepath = self.metadata_dir / f"{factor.filename}.yaml"

            try:
                # 检查是否需要更新
                if filepath.exists() and not overwrite:
                    file_mtime = self.get_file_mtime(filepath)
                    db_mtime = self.get_db_mtime(factor)
                    if not self.should_update_file(file_mtime, db_mtime):
                        stats["skipped"] += 1
                        continue

                # 转换为 YAML 数据
                data = self._factor_to_yaml_data(factor)
                self.write_yaml(filepath, data)
                stats["exported"] += 1

            except Exception as e:
                logger.error(f"factor_export_error: {factor.filename}, {e}")
                stats["errors"] += 1

        logger.info(f"factor_metadata_exported: {stats}")
        return stats

    def import_all(self) -> dict[str, int]:
        """
        从 YAML 文件导入因子元数据

        Returns:
            {"created": N, "updated": M, "unchanged": K, "errors": L}
        """
        stats = {"created": 0, "updated": 0, "unchanged": 0, "errors": 0}

        if self.store is None:
            logger.warning("factor_sync_import_skipped: store is None")
            return stats

        if not self.metadata_dir.exists():
            logger.info("factor_sync_import_skipped: metadata_dir not exists")
            return stats

        for yaml_file in self.metadata_dir.glob("*.yaml"):
            filename = yaml_file.stem

            try:
                # 读取 YAML
                data = self.read_yaml(yaml_file)
                if not data:
                    continue

                # 确保 filename 一致
                data['filename'] = filename

                # 查找现有记录
                existing = self.store.get(filename, include_excluded=True)

                if existing is None:
                    # 创建新记录（需要有代码文件才能创建）
                    # 这里只更新元数据，不创建新因子
                    logger.debug(f"factor_import_skipped_no_code: {filename}")
                    stats["unchanged"] += 1
                    continue

                # 比较时间戳
                file_mtime = self.get_file_mtime(yaml_file)
                db_mtime = self.get_db_mtime(existing)

                if self.should_update_db(file_mtime, db_mtime):
                    # 更新数据库
                    update_data = self._yaml_data_to_update_dict(data)
                    self.store.update(filename, **update_data)
                    stats["updated"] += 1
                else:
                    stats["unchanged"] += 1

            except Exception as e:
                logger.error(f"factor_import_error: {filename}, {e}")
                stats["errors"] += 1

        logger.info(f"factor_metadata_imported: {stats}")
        return stats

    def _factor_to_yaml_data(self, factor: Any) -> dict[str, Any]:
        """将因子对象转换为 YAML 数据"""
        data = {}

        for field in self.SYNC_FIELDS:
            value = getattr(factor, field, None)

            # 特殊处理
            if field in ('created_at', 'updated_at'):
                value = self.datetime_to_iso(value)
            elif field == 'param_analysis':
                # 将 JSON 字符串解析为结构化数据
                value = self.parse_json_field(value)
            elif field == 'excluded':
                # 转换为布尔值
                value = bool(value)
            elif field == 'verification_status':
                # 保持整数值（0=未验证, 1=通过, 2=废弃）
                value = int(value) if value is not None else 0

            if value is not None:
                data[field] = value

        return data

    def _yaml_data_to_update_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """将 YAML 数据转换为数据库更新字典"""
        update = {}

        for field in self.SYNC_FIELDS:
            if field in data and field not in ('filename', 'created_at'):
                value = data[field]

                # 特殊处理
                if field == 'updated_at':
                    value = self.iso_to_datetime(value)
                elif field == 'param_analysis':
                    # 将结构化数据序列化为 JSON 字符串
                    value = self.serialize_json_field(value)
                elif field == 'excluded':
                    # 转换为整数
                    value = 1 if value else 0
                elif field == 'verification_status':
                    # 保持整数值（0=未验证, 1=通过, 2=废弃）
                    value = int(value) if value is not None else 0

                update[field] = value

        return update

    def export_single(self, filename: str) -> bool:
        """
        导出单个因子的元数据

        Args:
            filename: 因子文件名

        Returns:
            是否成功
        """
        if self.store is None:
            return False

        try:
            factor = self.store.get(filename, include_excluded=True)
            if factor is None:
                return False

            filepath = self.metadata_dir / f"{filename}.yaml"
            data = self._factor_to_yaml_data(factor)
            self.write_yaml(filepath, data)
            return True

        except Exception as e:
            logger.error(f"factor_export_single_error: {filename}, {e}")
            return False

    def import_single(self, filename: str) -> bool:
        """
        导入单个因子的元数据

        Args:
            filename: 因子文件名

        Returns:
            是否成功
        """
        if self.store is None:
            return False

        filepath = self.metadata_dir / f"{filename}.yaml"
        if not filepath.exists():
            return False

        try:
            data = self.read_yaml(filepath)
            if not data:
                return False

            data['filename'] = filename
            update_data = self._yaml_data_to_update_dict(data)
            self.store.update(filename, **update_data)
            return True

        except Exception as e:
            logger.error(f"factor_import_single_error: {filename}, {e}")
            return False

    def get_status(self) -> dict[str, Any]:
        """
        获取同步状态

        Returns:
            {
                "db_count": 数据库中的因子数,
                "file_count": 文件中的因子数,
                "synced": 已同步数,
                "pending_export": 待导出数,
                "pending_import": 待导入数,
            }
        """
        status = {
            "db_count": 0,
            "file_count": 0,
            "synced": 0,
            "pending_export": 0,
            "pending_import": 0,
        }

        if self.store is None:
            return status

        try:
            factors = self.store.get_all(include_excluded=True)
            status["db_count"] = len(factors)
            db_filenames = {f.filename for f in factors}
        except Exception:
            return status

        if self.metadata_dir.exists():
            file_filenames = {f.stem for f in self.metadata_dir.glob("*.yaml")}
            status["file_count"] = len(file_filenames)
        else:
            file_filenames = set()

        # 计算同步状态
        status["synced"] = len(db_filenames & file_filenames)
        status["pending_export"] = len(db_filenames - file_filenames)
        status["pending_import"] = len(file_filenames - db_filenames)

        return status
