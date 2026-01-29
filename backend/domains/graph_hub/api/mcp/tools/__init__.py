"""
MCP 工具模块

提供图谱管理的 MCP 工具，包括关联管理、图查询和标签管理。
"""

from .base import (
    BaseTool,
    ToolDefinition,
    ToolRegistry,
    ToolResult,
    get_tool_registry,
)
from .link_tools import (
    CreateLinkTool,
    DeleteLinkTool,
)
from .query_tools import (
    FindPathTool,
    GetEdgesTool,
    TraceLineageTool,
)
from .tag_tools import (
    AddTagTool,
    GetEntitiesByTagTool,
    GetEntityTagsTool,
    ListAllTagsTool,
    RemoveTagTool,
)

__all__ = [
    # 基类
    "BaseTool",
    "ToolResult",
    "ToolDefinition",
    "ToolRegistry",
    "get_tool_registry",
    # 关联管理
    "CreateLinkTool",
    "DeleteLinkTool",
    # 图查询
    "GetEdgesTool",
    "TraceLineageTool",
    "FindPathTool",
    # 标签管理
    "AddTagTool",
    "RemoveTagTool",
    "GetEntityTagsTool",
    "GetEntitiesByTagTool",
    "ListAllTagsTool",
]
