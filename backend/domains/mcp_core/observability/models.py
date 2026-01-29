"""
日志数据模型

定义 LLM 调用、工具调用、会话等日志记录的数据结构。
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CallStatus(str, Enum):
    """调用状态"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class SessionStatus(str, Enum):
    """会话状态"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


def generate_id(prefix: str = "") -> str:
    """生成唯一 ID"""
    uid = str(uuid.uuid4())[:8]
    return f"{prefix}_{uid}" if prefix else uid


@dataclass
class Message:
    """消息"""
    role: str
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenUsage:
    """Token 使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class LLMCallRequest:
    """LLM 调用请求记录"""
    call_id: str = field(default_factory=lambda: generate_id("llm"))
    trace_id: str = ""
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # 模型信息
    model: str = ""
    provider: str = ""

    # 输入内容
    messages: list[Message] = field(default_factory=list)
    system_prompt: str = ""
    user_prompt: str = ""

    # 配置参数
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: list[ToolDefinition] = field(default_factory=list)
    extra_params: dict[str, Any] = field(default_factory=dict)

    # 上下文信息
    caller: str = ""  # 调用方（函数/服务名）
    purpose: str = ""  # 调用目的

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "model": self.model,
            "provider": self.provider,
            "messages_count": len(self.messages),
            "system_prompt_length": len(self.system_prompt),
            "user_prompt_length": len(self.user_prompt),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "tools_count": len(self.tools),
            "caller": self.caller,
            "purpose": self.purpose,
        }


@dataclass
class LLMCallResponse:
    """LLM 调用响应记录"""
    call_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # 输出内容
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = ""

    # Token 统计
    usage: TokenUsage = field(default_factory=TokenUsage)

    # 性能指标
    duration_ms: float = 0
    first_token_ms: float = 0  # 流式模式下首 token 延迟

    # 状态信息
    status: CallStatus = CallStatus.PENDING
    error_message: str = ""
    error_type: str = ""
    retry_count: int = 0

    # 服务端信息
    provider_request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "timestamp": self.timestamp.isoformat(),
            "content_length": len(self.content),
            "tool_calls_count": len(self.tool_calls),
            "finish_reason": self.finish_reason,
            "usage": self.usage.to_dict(),
            "duration_ms": self.duration_ms,
            "first_token_ms": self.first_token_ms,
            "status": self.status.value,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "provider_request_id": self.provider_request_id,
        }


@dataclass
class LLMCallRecord:
    """完整的 LLM 调用记录（请求 + 响应）"""
    request: LLMCallRequest
    response: LLMCallResponse | None = None

    @property
    def call_id(self) -> str:
        return self.request.call_id

    @property
    def success(self) -> bool:
        return self.response is not None and self.response.status == CallStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        result = {
            "request": self.request.to_dict(),
        }
        if self.response:
            result["response"] = self.response.to_dict()
        return result


@dataclass
class ToolCallRequest:
    """工具调用请求记录"""
    call_id: str = field(default_factory=lambda: generate_id("tool"))
    trace_id: str = ""
    llm_call_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # 工具信息
    tool_name: str = ""
    tool_version: str = ""

    # 输入
    arguments: dict[str, Any] = field(default_factory=dict)
    arguments_raw: str = ""  # 原始参数字符串

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "trace_id": self.trace_id,
            "llm_call_id": self.llm_call_id,
            "timestamp": self.timestamp.isoformat(),
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "arguments": self.arguments,
        }


@dataclass
class ToolCallResponse:
    """工具调用响应记录"""
    call_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # 输出
    result: Any = None
    result_summary: str = ""  # 结果摘要（用于日志展示）
    result_type: str = ""  # 结果类型

    # 性能
    duration_ms: float = 0

    # 状态
    status: CallStatus = CallStatus.PENDING
    error_message: str = ""
    error_type: str = ""

    # 额外信息（特定工具）
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "timestamp": self.timestamp.isoformat(),
            "result_summary": self.result_summary[:500] if self.result_summary else "",
            "result_type": self.result_type,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "error_message": self.error_message,
            "extra": self.extra,
        }


@dataclass
class ToolCallRecord:
    """完整的工具调用记录"""
    request: ToolCallRequest
    response: ToolCallResponse | None = None

    @property
    def call_id(self) -> str:
        return self.request.call_id

    @property
    def success(self) -> bool:
        return self.response is not None and self.response.status == CallStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        result = {
            "request": self.request.to_dict(),
        }
        if self.response:
            result["response"] = self.response.to_dict()
        return result


@dataclass
class SessionRecord:
    """会话记录"""
    session_id: str = field(default_factory=lambda: generate_id("sess"))
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None

    # 统计信息
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0

    # 状态
    status: SessionStatus = SessionStatus.RUNNING
    error_message: str = ""

    # 关联的调用记录
    llm_call_ids: list[str] = field(default_factory=list)
    tool_call_ids: list[str] = field(default_factory=list)

    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_llm_calls": self.total_llm_calls,
            "total_tool_calls": self.total_tool_calls,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "status": self.status.value,
            "error_message": self.error_message,
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.end_time else None
            ),
        }


# ============================================
# MCP 请求日志模型
# ============================================


class LogSource(str, Enum):
    """日志来源"""
    MCP_REQUEST = "mcp_request"  # 外部 MCP 请求
    INTERNAL_LLM = "internal_llm"  # 内部 LLM 调用
    INTERNAL_TOOL = "internal_tool"  # 内部工具调用


@dataclass
class MCPRequestRecord:
    """
    MCP 请求记录

    记录外部对 MCP 服务器的每次请求，包含完整的排查信息。
    """
    request_id: str = field(default_factory=lambda: generate_id("mcp"))
    timestamp: datetime = field(default_factory=datetime.now)

    # 服务器信息
    server_name: str = ""  # 服务名 (factor-hub, data-hub, strategy-hub)
    server_port: int = 0

    # 客户端信息
    client_ip: str = ""
    client_name: str = ""  # MCP 客户端名称 (如 Claude Code, Cursor 等)
    user_agent: str = ""

    # 请求信息
    method: str = ""  # JSON-RPC 方法 (initialize, tools/call, resources/read 等)
    jsonrpc_id: Any | None = None  # JSON-RPC 请求 ID
    params: dict[str, Any] = field(default_factory=dict)  # 请求参数

    # 工具/资源特定信息
    tool_name: str = ""  # 如果是 tools/call，记录工具名
    tool_arguments: dict[str, Any] = field(default_factory=dict)  # 工具调用入参（排查必需）
    resource_uri: str = ""  # 如果是 resources/read，记录资源 URI

    # 响应信息
    response_timestamp: datetime | None = None
    duration_ms: float = 0
    status: CallStatus = CallStatus.PENDING
    error_code: int | None = None
    error_message: str = ""

    # 响应数据（排查必需）
    response_size: int = 0  # 响应数据大小 (字节)
    response_summary: str = ""  # 响应摘要
    response_data: dict[str, Any] = field(default_factory=dict)  # 结构化响应数据

    # 追踪
    trace_id: str = ""
    session_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "server_name": self.server_name,
            "server_port": self.server_port,
            "client_ip": self.client_ip,
            "client_name": self.client_name,
            "method": self.method,
            "jsonrpc_id": self.jsonrpc_id,
            "tool_name": self.tool_name,
            "tool_arguments": self.tool_arguments,
            "resource_uri": self.resource_uri,
            "response_timestamp": self.response_timestamp.isoformat() if self.response_timestamp else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "response_size": self.response_size,
            "response_summary": self.response_summary[:500] if self.response_summary else "",
            "response_data": self.response_data,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
        }

    def to_summary(self) -> dict[str, Any]:
        """返回简化的摘要信息"""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "server_name": self.server_name,
            "method": self.method,
            "tool_name": self.tool_name or None,
            "tool_arguments": self.tool_arguments if self.tool_arguments else None,
            "resource_uri": self.resource_uri or None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "response_data": self.response_data if self.response_data else None,
            "error_message": self.error_message if self.status == CallStatus.FAILED else None,
        }
