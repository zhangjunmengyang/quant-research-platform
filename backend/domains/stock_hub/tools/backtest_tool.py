"""回测执行 MCP 工具"""
from typing import Dict, Any

from domains.mcp_core import ToolResult, ExecutionMode
from domains.mcp_core.base.tool import DomainBaseTool


class BacktestBaseTool(DomainBaseTool):
    """回测工具基类 - 延迟加载backtest_service"""
    service_path = "domains.stock_hub.services.stock_backtest_service:get_stock_backtest_service"
    service_attr = "backtest_service"
    execution_mode = ExecutionMode.COMPUTE


class RunBacktestTool(BacktestBaseTool):
    """执行A股选股回测"""

    @property
    def name(self) -> str:
        return "stock_backtest_run"

    @property
    def description(self) -> str:
        return """执行A股选股回测。

配置因子组合、时间范围、选股参数，通过Fuel环境子进程运行回测。
回测耗时取决于因子数量和时间范围（通常1-30分钟）。

因子列表格式: 每个因子需指定name(名称)、ascending(升序选小值)、param(参数)、weight(权重)。
常见因子: 市值、H估值_市盈率TTM、Rsi、Macd等（用stock_factor_list工具查看全部）。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "backtest_name": {
                    "type": "string",
                    "description": "回测名称",
                    "default": "AI框架回测",
                },
                "start_date": {
                    "type": "string",
                    "description": "回测开始日期 YYYY-MM-DD",
                    "default": "2024-01-01",
                },
                "end_date": {
                    "type": "string",
                    "description": "回测结束日期 YYYY-MM-DD（为空则到最新）",
                },
                "strategies": {
                    "type": "array",
                    "description": "策略列表（通常1个）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "default": "默认策略"},
                            "hold_period": {
                                "type": "string",
                                "enum": ["W", "M", "W2"],
                                "default": "W",
                                "description": "持仓周期: W=周, M=月, W2=双周",
                            },
                            "offset_list": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "default": [0],
                                "description": "偏移量列表",
                            },
                            "select_num": {
                                "type": "integer",
                                "default": 3,
                                "description": "选股数量",
                            },
                            "factor_list": {
                                "type": "array",
                                "description": "因子列表",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "因子名称"},
                                        "ascending": {"type": "boolean", "default": True, "description": "True=选值小的"},
                                        "param": {"type": "string", "default": ""},
                                        "weight": {"type": "number", "default": 1},
                                    },
                                    "required": ["name"],
                                },
                            },
                            "filter_list": {
                                "type": "array",
                                "description": "过滤条件列表",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "param": {"type": "string"},
                                        "condition": {"type": "string"},
                                        "keep": {"type": "boolean", "default": True},
                                    },
                                    "required": ["name", "condition"],
                                },
                                "default": [],
                            },
                        },
                        "required": ["factor_list"],
                    },
                },
                "performance_mode": {
                    "type": "string",
                    "enum": ["ECO", "BAL", "MAX"],
                    "default": "ECO",
                },
                "stay_real": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否使用真实交易模式（多进程）",
                },
                "excluded_boards": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["bj"],
                },
                "select_num": {
                    "type": "integer",
                    "default": 3,
                    "description": "快捷参数：选股数量（优先级低于strategies内的设置）",
                },
            },
            "required": ["strategies"],
        }

    async def execute(self, **params) -> ToolResult:
        try:
            from domains.stock_hub.models.backtest_config_model import (
                BacktestRequest,
                StrategyConfig,
                FactorConfig,
                FilterConfig,
            )

            # 构建策略配置
            strategies = []
            for s in params.get("strategies", []):
                factor_list = [
                    FactorConfig(
                        name=f["name"],
                        ascending=f.get("ascending", True),
                        param=f.get("param", ""),
                        weight=f.get("weight", 1),
                    )
                    for f in s.get("factor_list", [])
                ]
                filter_list = [
                    FilterConfig(
                        name=fl["name"],
                        param=fl.get("param"),
                        condition=fl["condition"],
                        keep=fl.get("keep", True),
                    )
                    for fl in s.get("filter_list", [])
                ]
                strategies.append(StrategyConfig(
                    name=s.get("name", "默认策略"),
                    hold_period=s.get("hold_period", "W"),
                    offset_list=s.get("offset_list", [0]),
                    select_num=s.get("select_num", params.get("select_num", 3)),
                    factor_list=factor_list,
                    filter_list=filter_list,
                ))

            request = BacktestRequest(
                backtest_name=params.get("backtest_name", "AI框架回测"),
                start_date=params.get("start_date", "2024-01-01"),
                end_date=params.get("end_date"),
                strategies=strategies,
                performance_mode=params.get("performance_mode", "ECO"),
                stay_real=params.get("stay_real", True),
                excluded_boards=params.get("excluded_boards", ["bj"]),
            )

            task_id = self.backtest_service.submit_backtest(request)
            task = self.backtest_service.get_task(task_id)

            if task and task["result"]:
                result = task["result"]
                return ToolResult.ok({
                    "task_id": task_id,
                    "status": result["status"],
                    "message": result["message"],
                    "result_path": result.get("result_path"),
                })
            else:
                return ToolResult.fail("回测任务未返回结果")

        except Exception as e:
            return ToolResult.fail(str(e))


class GetBacktestResultTool(BacktestBaseTool):
    """查询回测结果"""

    @property
    def name(self) -> str:
        return "stock_backtest_result"

    @property
    def description(self) -> str:
        return "查询回测任务的状态和结果。"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "回测任务ID",
                },
                "list_all": {
                    "type": "boolean",
                    "description": "列出所有任务",
                    "default": False,
                },
            },
        }

    async def execute(self, **params) -> ToolResult:
        try:
            if params.get("list_all"):
                tasks = self.backtest_service.list_tasks()
                return ToolResult.ok({"tasks": tasks})

            task_id = params.get("task_id")
            if not task_id:
                return ToolResult.fail("请提供 task_id 或设置 list_all=true")

            task = self.backtest_service.get_task(task_id)
            if not task:
                return ToolResult.fail(f"任务不存在: {task_id}")

            return ToolResult.ok(task)
        except Exception as e:
            return ToolResult.fail(str(e))
