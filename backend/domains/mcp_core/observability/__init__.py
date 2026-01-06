"""
可观测性模块

提供结构化日志、LLM/MCP 调用追踪功能。

使用示例:

    # 基础日志
    from mcp_core.observability import get_logger
    logger = get_logger(__name__)
    logger.info("Processing request", request_id="123")

    # LLM 调用日志（系统内部 LLM 调用）
    from mcp_core.observability import get_llm_logger, logged_llm_call

    @logged_llm_call(caller="my_service", purpose="analysis")
    async def call_openai(messages, model="gpt-4"):
        ...

    # MCP 请求日志（外部 MCP 协议调用）
    from mcp_core.observability import get_mcp_logger

    mcp_logger = get_mcp_logger()
    request_id = mcp_logger.log_request(...)
    mcp_logger.log_response(request_id, ...)

    # 会话管理
    from mcp_core.observability import Session

    with Session(metadata={"task": "field_fill"}) as sess:
        # 所有调用都会关联到这个会话
        result = await process()
        summary = sess.get_summary()
"""

from ..logging import (
    get_logger,
    configure_logging,
    bind_request_context,
    clear_request_context,
)

# LLM 调用日志
from .models import (
    CallStatus,
    SessionStatus,
    LogSource,
    LLMCallRecord,
    LLMCallRequest,
    LLMCallResponse,
    ToolCallRecord,
    ToolCallRequest,
    ToolCallResponse,
    SessionRecord,
    MCPRequestRecord,
    TokenUsage,
    Message,
)
from .storage import (
    LogStorage,
    MemoryStorage,
    StdoutStorage,
    get_log_storage,
    reset_storage,
)
from .llm_logger import (
    LLMLogger,
    LogConfig,
    LogSanitizer,
    get_llm_logger,
    configure_llm_logger,
    logged_llm_call,
    LLMCallContext,
    set_trace_id,
    get_trace_id,
    set_session_id,
    get_session_id,
)
# tool_logger 已合并到 mcp_logger，保留 summarize_result 工具函数
from .tool_logger import summarize_result
from .session_logger import (
    SessionLogger,
    get_session_logger,
    configure_session_logger,
    Session,
    estimate_cost,
)
from .mcp_logger import (
    MCPRequestLogger,
    MCPRequestContext,
    get_mcp_logger,
    configure_mcp_logger,
)

__all__ = [
    # Logging
    "get_logger",
    "configure_logging",
    "bind_request_context",
    "clear_request_context",
    # Models
    "CallStatus",
    "SessionStatus",
    "LLMCallRecord",
    "LLMCallRequest",
    "LLMCallResponse",
    "ToolCallRecord",
    "ToolCallRequest",
    "ToolCallResponse",
    "SessionRecord",
    "TokenUsage",
    "Message",
    "MCPRequestRecord",
    "LogSource",
    # Storage
    "LogStorage",
    "MemoryStorage",
    "StdoutStorage",
    "get_log_storage",
    "reset_storage",
    # LLM Logger
    "LLMLogger",
    "LogConfig",
    "LogSanitizer",
    "get_llm_logger",
    "configure_llm_logger",
    "logged_llm_call",
    "LLMCallContext",
    "set_trace_id",
    "get_trace_id",
    "set_session_id",
    "get_session_id",
    # Utils
    "summarize_result",
    # Session Logger
    "SessionLogger",
    "get_session_logger",
    "configure_session_logger",
    "Session",
    "estimate_cost",
    # MCP Logger
    "MCPRequestLogger",
    "MCPRequestContext",
    "get_mcp_logger",
    "configure_mcp_logger",
]
