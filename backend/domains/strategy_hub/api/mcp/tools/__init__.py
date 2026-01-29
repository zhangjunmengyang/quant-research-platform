"""
MCP 工具模块

提供策略查询和管理工具。
"""

from .analysis_tools import (
    CompareBacktestLiveTool,
    CompareEquityCurvesTool,
    CompareStrategyCoinsTool,
)
from .strategy_tools import (
    DeleteStrategyTool,
    GetStrategyStatsTool,
    GetStrategyTool,
    ListStrategiesTool,
    RunBacktestTool,
    SearchStrategiesTool,
    UpdateStrategyTool,
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
