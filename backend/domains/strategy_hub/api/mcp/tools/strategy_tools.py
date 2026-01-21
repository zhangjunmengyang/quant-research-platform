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
        return "运行因子策略回测"

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
                                "description": (
                                    "因子列表，每个因子为 [名称, 排序方向, 参数, 权重]。"
                                    "排序方向: True=因子值小的做多/大的做空, False=反之。"
                                    "参数: 计算窗口(小时)，如 1200。权重: 固定为 1。"
                                    "示例: [[\"Momentum\", true, 1200, 1]]"
                                ),
                            },
                            "long_select_coin_num": {
                                "type": "number",
                                "description": "多头选币数量。[0,1): 比例(如 0.1=10%); >=1: 绝对数量",
                                "default": 0.1,
                            },
                            "short_select_coin_num": {
                                "type": "number",
                                "description": "空头选币数量(0=不做空)。[0,1): 比例; >=1: 绝对数量",
                                "default": 0,
                            },
                            "long_cap_weight": {
                                "type": "number",
                                "description": "多头仓位权重。实际占比=long/(long+short)。纯多头: long=1,short=0",
                                "default": 1,
                            },
                            "short_cap_weight": {
                                "type": "number",
                                "description": "空头仓位权重。多空平衡: long=1,short=1; 纯空头: long=0,short=1",
                                "default": 0,
                            },
                            "hold_period": {
                                "type": "string",
                                "description": "持仓周期，如 \"1H\", \"4H\", \"24H\"",
                                "default": "1H",
                            },
                            "market": {
                                "type": "string",
                                "description": (
                                    "币池与交易类型: "
                                    "spot_spot(现货币池+现货交易), "
                                    "swap_swap(合约币池+合约交易), "
                                    "spot_swap(现货币池+优先合约), "
                                    "mix_spot(合并币池+优先现货), "
                                    "mix_swap(合并币池+优先合约)"
                                ),
                                "default": "swap_swap",
                            },
                        },
                    },
                },
                "start_date": {
                    "type": "string",
                    "description": "回测开始日期 (YYYY-MM-DD)，不传则使用数据最早日期",
                },
                "end_date": {
                    "type": "string",
                    "description": "回测结束日期 (YYYY-MM-DD)，不传则使用数据最新日期",
                },
                "leverage": {
                    "type": "number",
                    "description": "杠杆倍数，仅合约交易有效",
                    "default": 1,
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
        leverage: float = 1.0,
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
                leverage=leverage,
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


