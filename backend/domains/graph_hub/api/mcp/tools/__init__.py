"""
MCP 工具模块

提供图谱管理的 MCP 工具，包括关联管理、图查询和标签管理。
"""

from .base import (
    BaseTool,
    ToolResult,
    ToolDefinition,
    ToolRegistry,
    get_tool_registry,
)
from .link_tools import (
    CreateLinkTool,
    DeleteLinkTool,
)
from .query_tools import (
    GetEdgesTool,
    TraceLineageTool,
    FindPathTool,
)
from .tag_tools import (
    AddTagTool,
    RemoveTagTool,
    GetEntityTagsTool,
    GetEntitiesByTagTool,
    ListAllTagsTool,
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
