"""
MCP Tools - 工具定义模块

包含所有可供 LLM 调用的工具函数。
"""

from .base import BaseTool, ToolRegistry, ToolResult, ToolDefinition
from .query_tools import (
    ListFactorsTool,
    GetFactorTool,
    GetStatsTool,
    GetStylesTool,
    SearchByCodeTool,
)
from .mutation_tools import (
    CreateFactorTool,
    UpdateFactorTool,
    DeleteFactorTool,
)
from .analysis_tools import (
    GetFactorICTool,
    CompareFactorsTool,
    SuggestSimilarFactorsTool,
    # 多因子分析工具
    GetFactorCorrelationTool,
    MultiFactorAnalyzeTool,
    # 因子分箱分析工具
    AnalyzeFactorGroupsTool,
)

__all__ = [
    'BaseTool',
    'ToolRegistry',
    'ToolResult',
    'ToolDefinition',
    # Query tools
    'ListFactorsTool',
    'GetFactorTool',
    'GetStatsTool',
    'GetStylesTool',
    'SearchByCodeTool',
    # Mutation tools
    'CreateFactorTool',
    'UpdateFactorTool',
    'DeleteFactorTool',
    # 分析工具
    'GetFactorICTool',
    'CompareFactorsTool',
    'SuggestSimilarFactorsTool',
    # 多因子分析工具
    'GetFactorCorrelationTool',
    'MultiFactorAnalyzeTool',
    # 因子分箱分析工具
    'AnalyzeFactorGroupsTool',
]
