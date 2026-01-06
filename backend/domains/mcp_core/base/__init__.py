"""
MCP 基础组件

提供 Tool、Resource、Prompt、Store 的基类定义。
"""

from .tool import (
    BaseTool,
    DomainBaseTool,
    ToolResult,
    ToolDefinition,
    ToolRegistry,
    get_tool_registry,
    register_tool,
)
from .resource import (
    BaseResourceProvider,
    ResourceDefinition,
    ResourceContent,
)
from .prompt import (
    BasePromptProvider,
    PromptDefinition,
    PromptMessage,
)
from .store import (
    BaseStore,
    ThreadSafeConnectionMixin,
    get_database_url,
    get_store_instance,
    reset_store_instance,
    reset_all_stores,
)

__all__ = [
    # Tool
    "BaseTool",
    "DomainBaseTool",
    "ToolResult",
    "ToolDefinition",
    "ToolRegistry",
    "get_tool_registry",
    "register_tool",
    # Resource
    "BaseResourceProvider",
    "ResourceDefinition",
    "ResourceContent",
    # Prompt
    "BasePromptProvider",
    "PromptDefinition",
    "PromptMessage",
    # Store
    "BaseStore",
    "ThreadSafeConnectionMixin",
    "get_database_url",
    "get_store_instance",
    "reset_store_instance",
    "reset_all_stores",
]
