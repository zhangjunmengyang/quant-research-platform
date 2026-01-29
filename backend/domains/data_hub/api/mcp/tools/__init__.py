"""
MCP 工具模块

提供数据查询和因子计算工具。
"""

from .base import BaseTool, ToolDefinition, ToolRegistry, ToolResult, get_tool_registry
from .data_tools import (
    GetCoinMetadataTool,
    GetSymbolInfoTool,
    ListSymbolsTool,
)
from .factor_tools import (
    CalculateFactorTool,
    GetFactorRankingTool,
    GetSymbolRankAtTool,
    ListFactorsTool,
)
from .market_tools import (
    DetectKlinePatternsTool,
    GetMarketOverviewTool,
)
from .research_tools import (
    CalculateDrawdownTool,
    CalculateReturnsTool,
    CalculateStageStatsTool,
    FindPeaksTroughsTool,
)
from .signal_tools import (
    DetectSymbolEventsTool,
    ScreenMarketTool,
    SimulateHoldingStrategyTool,
)

__all__ = [
    # 基类
    "BaseTool",
    "ToolResult",
    "ToolDefinition",
    "ToolRegistry",
    "get_tool_registry",
    # 数据工具
    "ListSymbolsTool",
    "GetSymbolInfoTool",
    "GetCoinMetadataTool",
    # 因子工具
    "ListFactorsTool",
    "CalculateFactorTool",
    "GetSymbolRankAtTool",
    "GetFactorRankingTool",
    # 市场工具
    "GetMarketOverviewTool",
    "DetectKlinePatternsTool",
    # 信号工具
    "DetectSymbolEventsTool",
    "ScreenMarketTool",
    "SimulateHoldingStrategyTool",
    # 研究工具
    "CalculateReturnsTool",
    "CalculateDrawdownTool",
    "FindPeaksTroughsTool",
    "CalculateStageStatsTool",
]
