"""
MCP 工具模块

提供数据查询和因子计算工具。
"""

from .base import BaseTool, ToolResult, ToolDefinition, ToolRegistry, get_tool_registry
from .data_tools import (
    ListSymbolsTool,
    GetSymbolInfoTool,
    GetCoinMetadataTool,
)
from .factor_tools import (
    ListFactorsTool,
    CalculateFactorTool,
    GetSymbolRankAtTool,
    GetFactorRankingTool,
)
from .market_tools import (
    GetMarketOverviewTool,
    DetectKlinePatternsTool,
)
from .signal_tools import (
    DetectSymbolEventsTool,
    ScreenMarketTool,
    SimulateHoldingStrategyTool,
)
from .research_tools import (
    CalculateReturnsTool,
    CalculateDrawdownTool,
    FindPeaksTroughsTool,
    CalculateStageStatsTool,
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
