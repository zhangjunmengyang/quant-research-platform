"""
策略同步服务

将策略配置和回测结果在数据库和文件之间同步。
策略配置使用 YAML 格式，资金曲线使用单独的 JSON 文件。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseSyncService

logger = logging.getLogger(__name__)


class StrategySyncService(BaseSyncService):
    """
    策略同步服务

    文件结构：
        private-data/strategies/
            configs/{name}.yaml          # 策略配置
            equity_curves/{name}.json    # 资金曲线（大文件分离）

    YAML 格式包含：
        - 基础信息：id, name, description
        - 因子配置：factor_list, filter_list, strategy_config
        - 回测配置：start_date, end_date, leverage, hold_period, market 等
        - 绩效指标：annual_return, sharpe_ratio, max_drawdown 等
        - 元数据：verified, tags, created_at, updated_at
    """

    # 配置字段（存入 YAML）
    CONFIG_FIELDS = [
        'id', 'name', 'description',
        'factor_list', 'factor_params', 'strategy_config',
        'start_date', 'end_date', 'leverage', 'trade_type',
        'long_select_coin_num', 'short_select_coin_num',
        'long_cap_weight', 'short_cap_weight',
        'hold_period', 'offset', 'market',
        'sort_directions',
        'account_type', 'initial_usdt', 'margin_rate',
        'swap_c_rate', 'spot_c_rate',
        'swap_min_order_limit', 'spot_min_order_limit',
        'avg_price_col', 'min_kline_num',
        'black_list', 'white_list',
    ]

    # 绩效字段（存入 YAML）
    PERFORMANCE_FIELDS = [
        'cumulative_return', 'annual_return', 'max_drawdown',
        'max_drawdown_start', 'max_drawdown_end',
        'sharpe_ratio', 'recovery_rate', 'recovery_time',
        'win_periods', 'loss_periods', 'win_rate',
        'avg_return_per_period', 'profit_loss_ratio',
        'max_single_profit', 'max_single_loss',
        'max_consecutive_wins', 'max_consecutive_losses',
        'return_std',
        'year_return', 'quarter_return', 'month_return',
    ]

    # 元数据字段
    META_FIELDS = [
        'verified', 'tags', 'notes',
        'task_id', 'task_status', 'error_message',
        'created_at', 'updated_at',
    ]

    def __init__(self, data_dir: Path, store: Any = None):
        """
        初始化策略同步服务

        Args:
            data_dir: 私有数据目录 (private-data/)
            store: StrategyStore 实例
        """
        super().__init__(data_dir, store)
        self.configs_dir = data_dir / "strategies" / "configs"
        self.equity_dir = data_dir / "strategies" / "equity_curves"

    def export_all(self, overwrite: bool = False) -> Dict[str, int]:
        """
        导出所有策略

        Args:
            overwrite: 是否覆盖已存在的文件

        Returns:
            {"exported": N, "skipped": M, "errors": K}
        """
        stats = {"exported": 0, "skipped": 0, "errors": 0}

        if self.store is None:
            logger.warning("strategy_sync_export_skipped: store is None")
            return stats

        try:
            strategies = self.store.list_all()
        except Exception as e:
            logger.error(f"strategy_sync_export_error: {e}")
            stats["errors"] = 1
            return stats

        self.ensure_dir(self.configs_dir)
        self.ensure_dir(self.equity_dir)

        for strategy in strategies:
            try:
                # 使用 UUID (strategy.id) 作为文件名，保证唯一性
                filename = strategy.id
                config_path = self.configs_dir / f"{filename}.yaml"

                # 检查是否需要更新
                if config_path.exists() and not overwrite:
                    file_mtime = self.get_file_mtime(config_path)
                    db_mtime = self.get_db_mtime(strategy)
                    if not self.should_update_file(file_mtime, db_mtime):
                        stats["skipped"] += 1
                        continue

                # 导出配置
                config_data = self._strategy_to_yaml(strategy, filename)
                self.write_yaml(config_path, config_data)

                # 导出资金曲线（如果有）
                if strategy.equity_curve:
                    equity_path = self.equity_dir / f"{filename}.json"
                    equity_data = self.parse_json_field(strategy.equity_curve)
                    if equity_data:
                        self.write_json(equity_path, equity_data)

                stats["exported"] += 1

            except Exception as e:
                logger.error(f"strategy_export_error: {strategy.id}, {e}")
                stats["errors"] += 1

        logger.info(f"strategies_exported: {stats}")
        return stats

    def import_all(self) -> Dict[str, int]:
        """
        从文件导入策略

        Returns:
            {"created": N, "updated": M, "unchanged": K, "errors": L}
        """
        stats = {"created": 0, "updated": 0, "unchanged": 0, "errors": 0}

        if self.store is None:
            logger.warning("strategy_sync_import_skipped: store is None")
            return stats

        if not self.configs_dir.exists():
            logger.info("strategy_sync_import_skipped: configs_dir not exists")
            return stats

        for yaml_file in self.configs_dir.glob("*.yaml"):
            try:
                result = self._import_strategy_file(yaml_file)
                stats[result] += 1
            except Exception as e:
                logger.error(f"strategy_import_error: {yaml_file}, {e}")
                stats["errors"] += 1

        logger.info(f"strategies_imported: {stats}")
        return stats

    def _get_safe_filename(self, name: str) -> str:
        """获取安全的文件名"""
        if not name:
            return "unnamed"
        # 移除非法字符
        safe = "".join(c if c.isalnum() or c in '_-' else '_' for c in name)
        return safe[:100] or "unnamed"

    def _strategy_to_yaml(self, strategy: Any, filename: str) -> Dict[str, Any]:
        """将策略转换为 YAML 数据"""
        data = {}

        # 配置字段
        for field in self.CONFIG_FIELDS:
            value = getattr(strategy, field, None)
            if value is not None:
                # 解析 JSON 字段
                if field in ('factor_list', 'factor_params', 'strategy_config',
                            'sort_directions', 'black_list', 'white_list'):
                    value = self.parse_json_field(value)
                data[field] = value

        # 绩效字段
        for field in self.PERFORMANCE_FIELDS:
            value = getattr(strategy, field, None)
            if value is not None:
                # 解析 JSON 字段
                if field in ('year_return', 'quarter_return', 'month_return'):
                    value = self.parse_json_field(value)
                data[field] = value

        # 元数据字段
        for field in self.META_FIELDS:
            value = getattr(strategy, field, None)
            if value is not None:
                if field in ('created_at', 'updated_at'):
                    value = self.datetime_to_iso(value) if hasattr(value, 'isoformat') else value
                elif field == 'tags':
                    value = self.parse_json_field(value)
                data[field] = value

        # 标记资金曲线文件
        if strategy.equity_curve:
            data['equity_curve_file'] = f"{filename}.json"

        return data

    def _import_strategy_file(self, filepath: Path) -> str:
        """
        导入单个策略文件

        Returns:
            "created", "updated", "unchanged", 或 "errors"
        """
        data = self.read_yaml(filepath)
        if not data:
            return "errors"

        strategy_id = data.get('id')
        name = filepath.stem

        # 加载资金曲线
        equity_curve_file = data.pop('equity_curve_file', None)
        if equity_curve_file:
            equity_path = self.equity_dir / equity_curve_file
            if equity_path.exists():
                try:
                    equity_data = self.read_json(equity_path)
                    data['equity_curve'] = json.dumps(equity_data, ensure_ascii=False)
                except Exception:
                    pass

        # 序列化 JSON 字段
        for field in ('factor_list', 'factor_params', 'strategy_config',
                     'sort_directions', 'black_list', 'white_list',
                     'year_return', 'quarter_return', 'month_return', 'tags'):
            if field in data and not isinstance(data[field], str):
                data[field] = json.dumps(data[field], ensure_ascii=False)

        if strategy_id:
            # 尝试更新现有策略
            existing = self.store.get(strategy_id)
            if existing:
                file_mtime = self.get_file_mtime(filepath)
                db_mtime = self.get_db_mtime(existing)

                if self.should_update_db(file_mtime, db_mtime):
                    self.store.update(strategy_id, **data)
                    return "updated"
                else:
                    return "unchanged"

        # 创建新策略
        from domains.strategy_hub.services.models import Strategy
        strategy = Strategy.from_dict(data)
        self.store.add(strategy)
        return "created"

    def export_single(self, strategy_id: str) -> bool:
        """
        导出单个策略

        Args:
            strategy_id: 策略 UUID

        Returns:
            是否成功
        """
        if self.store is None:
            return False

        try:
            strategy = self.store.get(strategy_id)
            if strategy is None:
                return False

            self.ensure_dir(self.configs_dir)
            self.ensure_dir(self.equity_dir)

            filename = strategy.id
            config_path = self.configs_dir / f"{filename}.yaml"

            # 导出配置
            config_data = self._strategy_to_yaml(strategy, filename)
            self.write_yaml_atomic(config_path, config_data)

            # 导出资金曲线（如果有）
            if strategy.equity_curve:
                equity_path = self.equity_dir / f"{filename}.json"
                equity_data = self.parse_json_field(strategy.equity_curve)
                if equity_data:
                    self.write_json_atomic(equity_path, equity_data)

            return True

        except Exception as e:
            logger.error(f"strategy_export_single_error: {strategy_id}, {e}")
            return False

    def import_single(self, strategy_id: str) -> bool:
        """
        导入单个策略

        Args:
            strategy_id: 策略 UUID

        Returns:
            是否成功
        """
        if self.store is None:
            return False

        filepath = self.configs_dir / f"{strategy_id}.yaml"
        if not filepath.exists():
            return False

        try:
            result = self._import_strategy_file(filepath)
            return result in ("created", "updated", "unchanged")
        except Exception as e:
            logger.error(f"strategy_import_single_error: {strategy_id}, {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        status = {
            "db_count": 0,
            "file_count": 0,
            "equity_file_count": 0,
        }

        if self.store is None:
            return status

        try:
            strategies = self.store.list_all()
            status["db_count"] = len(strategies)
        except Exception:
            return status

        if self.configs_dir.exists():
            status["file_count"] = len(list(self.configs_dir.glob("*.yaml")))

        if self.equity_dir.exists():
            status["equity_file_count"] = len(list(self.equity_dir.glob("*.json")))

        return status
