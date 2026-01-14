"""
分析工具定义

提供参数分析、策略对比等 MCP 工具。
"""

from typing import Any, Dict, List, Optional
import logging

from domains.mcp_core import BaseTool, ToolResult, ExecutionMode

from domains.strategy_hub.services import (
    get_param_search_service,
    get_param_analysis_service,
    get_backtest_comparison_service,
    get_coin_similarity_service,
    get_equity_correlation_service,
)

logger = logging.getLogger(__name__)


class RunParamSearchTool(BaseTool):
    """运行参数搜索工具"""

    category = "mutation"
    execution_mode = ExecutionMode.COMPUTE  # 参数搜索是计算密集型任务

    @property
    def name(self) -> str:
        return "run_param_search"

    @property
    def description(self) -> str:
        return "运行策略参数搜索，遍历参数组合找到最优配置"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "搜索任务名称",
                },
                "batch_params": {
                    "type": "object",
                    "description": "参数搜索范围 {参数名: [参数值列表]}",
                },
                "strategy_template": {
                    "type": "object",
                    "description": "策略模板配置",
                },
                "max_workers": {
                    "type": "integer",
                    "description": "最大并行数",
                    "default": 4,
                },
            },
            "required": ["name", "batch_params", "strategy_template"],
        }

    async def execute(
        self,
        name: str,
        batch_params: Dict[str, List[Any]],
        strategy_template: Dict[str, Any],
        max_workers: int = 4,
    ) -> ToolResult:
        try:
            service = get_param_search_service()
            result = service.run_search(
                name=name,
                batch_params=batch_params,
                strategy_template=strategy_template,
                max_workers=max_workers,
            )
            return ToolResult.ok({
                "name": result.name,
                "total_combinations": result.total_combinations,
                "status": result.status,
                "output_path": result.output_path,
            })
        except Exception as e:
            logger.exception("参数搜索失败")
            return ToolResult.fail(str(e))


class AnalyzeParamsTool(BaseTool):
    """参数分析工具"""

    category = "query"

    @property
    def name(self) -> str:
        return "analyze_params"

    @property
    def description(self) -> str:
        return "分析参数遍历结果，生成热力图或平原图"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "trav_name": {
                    "type": "string",
                    "description": "遍历结果名称",
                },
                "batch_params": {
                    "type": "object",
                    "description": "参数范围",
                },
                "param_x": {
                    "type": "string",
                    "description": "X轴参数",
                },
                "param_y": {
                    "type": "string",
                    "description": "Y轴参数（可选，为空则单参数分析）",
                },
                "limit_dict": {
                    "type": "object",
                    "description": "固定参数条件",
                },
                "indicator": {
                    "type": "string",
                    "description": "评价指标",
                    "default": "annual_return",
                },
            },
            "required": ["trav_name", "batch_params", "param_x"],
        }

    async def execute(
        self,
        trav_name: str,
        batch_params: Dict[str, List[Any]],
        param_x: str,
        param_y: Optional[str] = None,
        limit_dict: Optional[Dict[str, List[Any]]] = None,
        indicator: str = "annual_return",
    ) -> ToolResult:
        try:
            service = get_param_analysis_service()
            result = service.analyze(
                trav_name=trav_name,
                batch_params=batch_params,
                param_x=param_x,
                param_y=param_y,
                limit_dict=limit_dict,
                indicator=indicator,
            )
            return ToolResult.ok({
                "name": result.name,
                "analysis_type": result.analysis_type,
                "indicator": result.indicator,
                "html_path": result.html_path,
            })
        except Exception as e:
            logger.exception("参数分析失败")
            return ToolResult.fail(str(e))


class CompareBacktestLiveTool(BaseTool):
    """回测实盘对比工具"""

    category = "query"

    @property
    def name(self) -> str:
        return "compare_backtest_live"

    @property
    def description(self) -> str:
        return "对比回测和实盘的资金曲线、选币结果"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "backtest_name": {
                    "type": "string",
                    "description": "回测策略名称",
                },
                "start_time": {
                    "type": "string",
                    "description": "对比开始时间",
                },
                "end_time": {
                    "type": "string",
                    "description": "对比结束时间",
                },
            },
            "required": ["backtest_name", "start_time", "end_time"],
        }

    async def execute(
        self,
        backtest_name: str,
        start_time: str,
        end_time: str,
    ) -> ToolResult:
        try:
            service = get_backtest_comparison_service()
            result = service.compare(
                backtest_name=backtest_name,
                start_time=start_time,
                end_time=end_time,
            )
            return ToolResult.ok({
                "backtest_name": result.backtest_name,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "coin_selection_similarity": result.coin_selection_similarity,
                "html_path": result.html_path,
            })
        except Exception as e:
            logger.exception("回测实盘对比失败")
            return ToolResult.fail(str(e))


class CompareStrategyCoinsTool(BaseTool):
    """选币相似度对比工具"""

    category = "query"

    @property
    def name(self) -> str:
        return "compare_strategy_coins"

    @property
    def description(self) -> str:
        return "计算多策略之间的选币重合度"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "strategy_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "策略名称列表",
                },
            },
            "required": ["strategy_list"],
        }

    async def execute(self, strategy_list: List[str]) -> ToolResult:
        try:
            service = get_coin_similarity_service()
            result = service.analyze(strategy_list)
            return ToolResult.ok({
                "strategies": result.strategies,
                "html_path": result.html_path,
            })
        except Exception as e:
            logger.exception("选币相似度分析失败")
            return ToolResult.fail(str(e))


class CompareEquityCurvesTool(BaseTool):
    """资金曲线相关性对比工具"""

    category = "query"

    @property
    def name(self) -> str:
        return "compare_equity_curves"

    @property
    def description(self) -> str:
        return "计算多策略资金曲线涨跌幅之间的相关性"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "strategy_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "策略名称列表",
                },
            },
            "required": ["strategy_list"],
        }

    async def execute(self, strategy_list: List[str]) -> ToolResult:
        try:
            service = get_equity_correlation_service()
            result = service.analyze(strategy_list)
            return ToolResult.ok({
                "strategies": result.strategies,
                "html_path": result.html_path,
            })
        except Exception as e:
            logger.exception("资金曲线相关性分析失败")
            return ToolResult.fail(str(e))
