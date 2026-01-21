"""
策略工具定义

提供策略查询、管理等 MCP 工具。
与 REST API 统一使用 StrategyService 服务层，遵循分层架构规范。
"""

from typing import Any, Dict, Optional
import logging

from domains.mcp_core import BaseTool, ToolResult
from domains.mcp_core.base.tool import ExecutionMode

from domains.strategy_hub.services import get_strategy_service, Strategy

logger = logging.getLogger(__name__)


class ListStrategiesTool(BaseTool):
    """列出策略工具"""

    category = "query"

    @property
    def name(self) -> str:
        return "list_strategies"

    @property
    def description(self) -> str:
        return "列出所有策略，支持按验证、上线状态筛选"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "verified": {
                    "type": "boolean",
                    "description": "是否已验证",
                },
                "order_by": {
                    "type": "string",
                    "description": "排序字段",
                    "enum": ["created_at", "annual_return", "sharpe_ratio", "max_drawdown"],
                    "default": "created_at",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制",
                    "default": 20,
                },
            },
        }

    async def execute(
        self,
        verified: Optional[bool] = None,
        order_by: str = "created_at",
        limit: int = 20,
    ) -> ToolResult:
        try:
            service = get_strategy_service()

            filters = {}
            if verified is not None:
                filters["verified"] = verified

            strategies, total = service.list_strategies(
                filters=filters if filters else None,
                order_by=order_by,
                order_desc=True,
                limit=limit,
            )

            return ToolResult.ok({
                "count": len(strategies),
                "total": total,
                "strategies": [s.to_dict() for s in strategies],
            })
        except Exception as e:
            logger.exception("列出策略失败")
            return ToolResult.fail(str(e))


class GetStrategyTool(BaseTool):
    """获取策略详情工具"""

    category = "query"

    @property
    def name(self) -> str:
        return "get_strategy"

    @property
    def description(self) -> str:
        return "获取指定策略的详细信息"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "strategy_id": {
                    "type": "string",
                    "description": "策略ID",
                },
            },
            "required": ["strategy_id"],
        }

    async def execute(self, strategy_id: str) -> ToolResult:
        try:
            service = get_strategy_service()
            strategy = service.get_strategy(strategy_id)

            if not strategy:
                return ToolResult.fail(f"策略不存在: {strategy_id}")

            return ToolResult.ok(strategy.to_dict())
        except Exception as e:
            logger.exception("获取策略失败")
            return ToolResult.fail(str(e))


class SearchStrategiesTool(BaseTool):
    """搜索策略工具"""

    category = "query"

    @property
    def name(self) -> str:
        return "search_strategies"

    @property
    def description(self) -> str:
        return "按名称、描述或因子搜索策略"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str) -> ToolResult:
        try:
            service = get_strategy_service()
            strategies = service.search_strategies(query)

            return ToolResult.ok({
                "count": len(strategies),
                "strategies": [s.to_dict() for s in strategies],
            })
        except Exception as e:
            logger.exception("搜索策略失败")
            return ToolResult.fail(str(e))


class GetStrategyStatsTool(BaseTool):
    """获取策略统计工具"""

    category = "query"

    @property
    def name(self) -> str:
        return "get_strategy_stats"

    @property
    def description(self) -> str:
        return "获取策略库的统计信息"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self) -> ToolResult:
        try:
            service = get_strategy_service()
            stats = service.get_stats()
            return ToolResult.ok(stats)
        except Exception as e:
            logger.exception("获取统计失败")
            return ToolResult.fail(str(e))


class RunBacktestTool(BaseTool):
    """运行回测工具"""

    category = "mutation"
    execution_mode = ExecutionMode.COMPUTE  # CPU 密集型任务，由 BacktestRunner 管理
    # execution_timeout 不设置，使用 COMPUTE_TOOL_TIMEOUT 默认值 (300s)
    # 注意：实际回测在 BacktestRunner 中异步执行，此超时仅控制任务提交阶段

    @property
    def name(self) -> str:
        return "run_backtest"

    @property
    def description(self) -> str:
        return """运行因子策略回测。

执行回测并等待完成，直接返回回测结果。
回测完成后策略会自动入库，可通过 get_strategy 查看详情。

策略配置说明:
- factor_list: 因子列表，每个因子格式为 [因子名, 排序方式, 参数]
  - 排序方式: True=升序(小值优先), False=降序(大值优先)
- long_select_coin_num: 多头选币数量（比例或绝对数量）
- short_select_coin_num: 空头选币数量（0=不做空）
- hold_period: 持仓周期（如 "1H", "4H", "24H"）
- market: 市场类型（"swap_swap", "spot_swap", "spot_spot"）

示例:
```json
{
  "name": "动量策略",
  "strategy_list": [{
    "factor_list": [["Momentum", true, {"n": 20}]],
    "long_select_coin_num": 0.1,
    "short_select_coin_num": 0,
    "hold_period": "1H",
    "market": "swap_swap"
  }],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "策略名称",
                },
                "strategy_list": {
                    "type": "array",
                    "description": "策略配置列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "factor_list": {
                                "type": "array",
                                "description": "因子列表，每个因子为 [名称, 排序方向, 参数]",
                            },
                            "long_select_coin_num": {
                                "type": "number",
                                "description": "多头选币数量（比例或绝对数）",
                                "default": 0.1,
                            },
                            "short_select_coin_num": {
                                "type": "number",
                                "description": "空头选币数量（0表示不做空）",
                                "default": 0,
                            },
                            "hold_period": {
                                "type": "string",
                                "description": "持仓周期",
                                "default": "1H",
                            },
                            "market": {
                                "type": "string",
                                "description": "市场类型",
                                "default": "swap_swap",
                            },
                        },
                    },
                },
                "start_date": {
                    "type": "string",
                    "description": "回测开始日期 (YYYY-MM-DD)",
                },
                "end_date": {
                    "type": "string",
                    "description": "回测结束日期 (YYYY-MM-DD)",
                },
                "initial_usdt": {
                    "type": "number",
                    "description": "初始资金",
                    "default": 10000,
                },
                "leverage": {
                    "type": "number",
                    "description": "杠杆倍数",
                    "default": 1.0,
                },
                "description": {
                    "type": "string",
                    "description": "策略描述（可选）",
                },
            },
            "required": ["name", "strategy_list"],
        }

    async def execute(
        self,
        name: str,
        strategy_list: list,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_usdt: float = 10000,
        leverage: float = 1.0,
        description: Optional[str] = None,
    ) -> ToolResult:
        try:
            from domains.strategy_hub.services.backtest_runner import (
                BacktestRequest,
                get_backtest_runner,
            )

            # 构建回测请求
            request = BacktestRequest(
                name=name,
                strategy_list=strategy_list,
                start_date=start_date,
                end_date=end_date,
                initial_usdt=initial_usdt,
                leverage=leverage,
                description=description,
            )

            # 执行回测并等待完成
            runner = get_backtest_runner()
            strategy = await runner.run_and_wait(request)

            # 返回回测结果摘要
            return ToolResult.ok({
                "strategy_id": strategy.id,
                "name": strategy.name,
                "status": "completed",
                "summary": {
                    "annual_return": strategy.annual_return,
                    "max_drawdown": strategy.max_drawdown,
                    "sharpe_ratio": strategy.sharpe_ratio,
                    "win_rate": strategy.win_rate,
                    "cumulative_return": strategy.cumulative_return,
                },
                "message": f"回测完成: {name}",
            })
        except Exception as e:
            logger.exception("回测执行失败")
            return ToolResult.fail(str(e))


