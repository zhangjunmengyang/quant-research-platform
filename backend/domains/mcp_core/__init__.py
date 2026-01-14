"""
MCP Core - Model Context Protocol 基础设施

提供 MCP 协议相关的组件:
- 工具基类和注册器
- 资源提供者基类
- Prompt 提供者基类
- 服务器基类和协议处理
- MCP 错误处理

注意: 通用应用基础设施（异常、生命周期）在 domains.core 模块中。
"""

from .base.tool import (
    BaseTool,
    DomainBaseTool,
    ToolResult,
    ToolDefinition,
    ToolRegistry,
    get_tool_registry,
    register_tool,
    ExecutionMode,
)
from .base.resource import (
    BaseResourceProvider,
    ResourceDefinition,
    ResourceContent,
)
from .base.prompt import (
    BasePromptProvider,
    PromptDefinition,
    PromptMessage,
)
from .server.protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    MCP_PROTOCOL_VERSION,
)
from .server.server import (
    BaseMCPServer,
    create_mcp_app,
)
from .server.streamable_http import (
    create_streamable_http_app,
    run_streamable_http_server,
    MCPServerAdapter,
)
from .server.sse import (
    TaskStatus,
    TaskProgress,
    TaskProgressManager,
    get_task_manager,
)

# Middleware - Error handling only
from .middleware.error_handler import (
    ErrorCode,
    MCPError,
    ParseError,
    InvalidRequestError,
    MethodNotFoundError,
    InvalidParamsError,
    ToolNotFoundError,
    ToolExecutionError,
    ResourceNotFoundError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    ErrorHandler,
)

# Observability
from .observability import (
    get_logger,
    configure_logging,
    bind_request_context,
)

# Config & Paths
from .config import (
    MCPConfig,
    get_config,
    set_config,
    get_project_root,
    get_data_dir,
)
from .settings import (
    MCPSettings,
    ServerSettings,
    LoggingSettings,
    get_settings,
    reload_settings,
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
    "ExecutionMode",
    # Resource
    "BaseResourceProvider",
    "ResourceDefinition",
    "ResourceContent",
    # Prompt
    "BasePromptProvider",
    "PromptDefinition",
    "PromptMessage",
    # Protocol
    "JSONRPCRequest",
    "JSONRPCResponse",
    "JSONRPCError",
    "MCP_PROTOCOL_VERSION",
    # Server
    "BaseMCPServer",
    "create_mcp_app",
    # Streamable HTTP
    "create_streamable_http_app",
    "run_streamable_http_server",
    "MCPServerAdapter",
    # SSE
    "TaskStatus",
    "TaskProgress",
    "TaskProgressManager",
    "get_task_manager",
    # Middleware - Error handling
    "ErrorCode",
    "MCPError",
    "ParseError",
    "InvalidRequestError",
    "MethodNotFoundError",
    "InvalidParamsError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "ResourceNotFoundError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "ErrorHandler",
    # Observability
    "get_logger",
    "configure_logging",
    "bind_request_context",
    # Config & Paths
    "MCPConfig",
    "get_config",
    "set_config",
    "get_project_root",
    "get_data_dir",
    # Settings (pydantic-settings)
    "MCPSettings",
    "ServerSettings",
    "LoggingSettings",
    "get_settings",
    "reload_settings",
]

__version__ = "2.1.0"
