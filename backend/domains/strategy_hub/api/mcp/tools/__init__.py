"""
MCP 工具模块

提供策略查询和管理工具。
"""

from .strategy_tools import (
    ListStrategiesTool,
    GetStrategyTool,
    SearchStrategiesTool,
    GetStrategyStatsTool,
    UpdateStrategyTool,
    DeleteStrategyTool,
    RunBacktestTool,
)
from .analysis_tools import (
    CompareBacktestLiveTool,
    CompareStrategyCoinsTool,
    CompareEquityCurvesTool,
)

__all__ = [
    # 查询工具
    "ListStrategiesTool",
    "GetStrategyTool",
    "SearchStrategiesTool",
    "GetStrategyStatsTool",
    # 修改工具
    "UpdateStrategyTool",
    "DeleteStrategyTool",
    "RunBacktestTool",
    # 分析工具
    "CompareBacktestLiveTool",
    "CompareStrategyCoinsTool",
    "CompareEquityCurvesTool",
]
