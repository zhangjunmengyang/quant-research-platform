"""因子分析 MCP 工具"""
from typing import Dict, Any

from domains.mcp_core import ToolResult, ExecutionMode
from domains.mcp_core.base.tool import DomainBaseTool


class AnalysisBaseTool(DomainBaseTool):
    """分析工具基类"""
    service_path = "domains.stock_hub.services.stock_analysis_service:get_stock_analysis_service"
    service_attr = "analysis_service"
    execution_mode = ExecutionMode.COMPUTE


class FactorICAnalysisTool(AnalysisBaseTool):
    """因子IC/分组分析"""

    @property
    def name(self) -> str:
        return "stock_factor_ic_analysis"

    @property
    def description(self) -> str:
        return """对A股因子进行IC/ICIR分析和分组收益分析。

需要先通过stock_backtest_run执行回测获得结果路径，然后用此工具分析因子有效性。
返回: IC均值、ICIR、t统计量、各分组累计收益等。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "result_path": {
                    "type": "string",
                    "description": "回测结果文件夹路径（从stock_backtest_run获取）",
                },
                "factor_name": {
                    "type": "string",
                    "description": "要分析的因子名称",
                },
                "hold_period": {
                    "type": "string",
                    "enum": ["W", "M"],
                    "default": "W",
                },
                "group_num": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 2,
                    "maximum": 20,
                },
            },
            "required": ["result_path", "factor_name"],
        }

    async def execute(self, **params) -> ToolResult:
        try:
            result = self.analysis_service.analyze_factor(
                result_path=params["result_path"],
                factor_name=params["factor_name"],
                hold_period=params.get("hold_period", "W"),
                group_num=params.get("group_num", 10),
            )

            if result.get("status") == "ok":
                return ToolResult.ok(result.get("data", {}))
            else:
                return ToolResult.fail(result.get("message", "分析失败"))
        except Exception as e:
            return ToolResult.fail(str(e))
