"""
参数搜索服务

执行策略参数遍历搜索，找到最优参数组合。
"""

import itertools
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

from domains.mcp_core.paths import get_data_dir
from domains.engine.core.backtest import find_best_params
from domains.engine.core.model.backtest_config import BacktestConfigFactory

logger = logging.getLogger(__name__)


@dataclass
class ParamSearchResult:
    """参数搜索结果"""
    name: str
    total_combinations: int
    completed: int = 0
    best_params: Optional[Dict[str, Any]] = None
    all_results: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending"
    error: Optional[str] = None
    output_path: Optional[str] = None


class ParamSearchService:
    """
    参数搜索服务

    支持多参数组合的策略回测搜索，找到最优参数。
    """

    def __init__(self, data_path: Optional[Path] = None):
        """
        初始化服务

        Args:
            data_path: 数据根路径
        """
        self.data_path = data_path or get_data_dir()
        self.output_path = self.data_path / "traversal_results"
        self.output_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _generate_param_combinations(batch_params: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        生成参数组合

        Args:
            batch_params: 参数字典 {参数名: [参数值列表]}

        Returns:
            参数组合列表
        """
        keys = list(batch_params.keys())
        values = list(batch_params.values())
        return [dict(zip(keys, combo)) for combo in itertools.product(*values)]

    def run_search(
        self,
        name: str,
        batch_params: Dict[str, List[Any]],
        strategy_template: Dict[str, Any],
        max_workers: int = 4
    ) -> ParamSearchResult:
        """
        运行参数搜索

        Args:
            name: 搜索任务名称
            batch_params: 参数搜索范围 {参数名: [参数值列表]}
            strategy_template: 策略模板配置
            max_workers: 最大并行数

        Returns:
            搜索结果
        """
        result = ParamSearchResult(
            name=name,
            total_combinations=1
        )

        try:
            # 生成参数组合
            param_combinations = self._generate_param_combinations(batch_params)
            result.total_combinations = len(param_combinations)
            result.status = "running"

            logger.info(f"Starting param search: {name}, {result.total_combinations} combinations")

            # 生成策略配置列表
            strategies = []
            for params_dict in param_combinations:
                strategy_config = strategy_template.copy()
                # 替换模板中的参数
                strategy_config = self._apply_params(strategy_config, params_dict)
                strategies.append([strategy_config])

            # 使用回测引擎执行搜索
            factory = BacktestConfigFactory(backtest_name=name)
            factory.generate_configs_by_strategies(strategies=strategies)

            # 执行参数搜索
            find_best_params(factory)

            result.status = "completed"
            result.output_path = str(self.output_path / name)

            logger.info(f"Param search completed: {name}")

        except Exception as e:
            logger.error(f"Param search failed: {e}")
            result.status = "failed"
            result.error = str(e)

        return result

    def _apply_params(
        self,
        template: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        将参数应用到模板

        Args:
            template: 策略模板
            params: 参数字典

        Returns:
            应用参数后的配置
        """
        import copy
        config = copy.deepcopy(template)

        for key, value in params.items():
            if key in config:
                config[key] = value
            # 处理嵌套参数 (factor_list, filter_list)
            elif '.' in key:
                parts = key.split('.')
                self._set_nested_value(config, parts, value)

        return config

    def _set_nested_value(
        self,
        config: Dict[str, Any],
        path: List[str],
        value: Any
    ) -> None:
        """
        设置嵌套值

        Args:
            config: 配置字典
            path: 路径列表
            value: 要设置的值
        """
        current = config
        for key in path[:-1]:
            if key.isdigit():
                current = current[int(key)]
            else:
                current = current.get(key, {})
        last_key = path[-1]
        if last_key.isdigit():
            current[int(last_key)] = value
        else:
            current[last_key] = value


# 单例模式
_param_search_service: Optional[ParamSearchService] = None


def get_param_search_service() -> ParamSearchService:
    """获取参数搜索服务单例"""
    global _param_search_service
    if _param_search_service is None:
        _param_search_service = ParamSearchService()
    return _param_search_service


def reset_param_search_service() -> None:
    """重置服务单例"""
    global _param_search_service
    _param_search_service = None
