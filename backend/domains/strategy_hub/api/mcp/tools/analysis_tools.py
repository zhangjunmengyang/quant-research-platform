"""
分析工具定义

提供策略对比等 MCP 工具。
注意: 参数搜索/分析工具已移至 factor-hub，实现因子粒度的参数敏感性分析。
"""

import logging
from typing import Any

from domains.mcp_core import BaseTool, ToolResult
from domains.strategy_hub.services import (
    get_backtest_comparison_service,
    get_coin_similarity_service,
    get_equity_correlation_service,
)

logger = logging.getLogger(__name__)


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
    def input_schema(self) -> dict[str, Any]:
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
    def input_schema(self) -> dict[str, Any]:
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

    async def execute(self, strategy_list: list[str]) -> ToolResult:
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
    def input_schema(self) -> dict[str, Any]:
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

    async def execute(self, strategy_list: list[str]) -> ToolResult:
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
