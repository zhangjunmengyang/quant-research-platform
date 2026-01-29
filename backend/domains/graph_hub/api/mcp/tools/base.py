"""
MCP Tool 基类

从 mcp_core 导入基类，并提供 graph_hub 模块专用的扩展。
"""

from domains.mcp_core import (
    DomainBaseTool,
    ToolResult,
    ToolDefinition,
    ToolRegistry,
    get_tool_registry,
    register_tool,
)


class BaseTool(DomainBaseTool):
    """
    图谱模块 MCP 工具基类

    继承 DomainBaseTool，配置 GraphStore 延迟加载。
    """

    # 服务配置
    service_configs = {
        "graph_store": "domains.graph_hub.core.store:get_graph_store",
    }


# 重新导出供其他模块使用
__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolDefinition",
    "ToolRegistry",
    "get_tool_registry",
    "register_tool",
]
