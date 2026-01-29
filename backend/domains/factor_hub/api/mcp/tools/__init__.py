"""
MCP Tools - 工具定义模块

包含所有可供 LLM 调用的工具函数。
"""

from .analysis_tools import (
    # 因子分箱分析工具
    AnalyzeFactorGroupsTool,
    CompareFactorsTool,
    # 多因子分析工具 (placeholder)
    GetFactorCorrelationTool,
    GetFactorICTool,
    MultiFactorAnalyzeTool,
    # 因子参数分析工具（支持一维柱状图和二维热力图）
    RunFactorParamAnalysisTool,
)
from .base import BaseTool, ToolDefinition, ToolRegistry, ToolResult
from .mutation_tools import (
    CreateFactorTool,
    DeleteFactorTool,
    UpdateFactorTool,
)
from .query_tools import (
    GetFactorTool,
    GetStatsTool,
    GetStylesTool,
    ListFactorsTool,
    SearchByCodeTool,
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
    # 多因子分析工具 (placeholder)
    'GetFactorCorrelationTool',
    'MultiFactorAnalyzeTool',
    # 因子分箱分析工具
    'AnalyzeFactorGroupsTool',
    # 因子参数分析工具（支持一维柱状图和二维热力图）
    'RunFactorParamAnalysisTool',
]
