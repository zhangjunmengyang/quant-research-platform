"""
MCP 基础组件

提供 Tool、Resource、Prompt、Store 的基类定义。
"""

from .prompt import (
    BasePromptProvider,
    PromptDefinition,
    PromptMessage,
)
from .resource import (
    BaseResourceProvider,
    ResourceContent,
    ResourceDefinition,
)
from .store import (
    BaseStore,
    ThreadSafeConnectionMixin,
    get_database_url,
    get_store_instance,
    reset_all_stores,
    reset_store_instance,
)
from .tool import (
    BaseTool,
    DomainBaseTool,
    ToolDefinition,
    ToolRegistry,
    ToolResult,
    get_tool_registry,
    register_tool,
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
