"""
LLM 调用日志记录器

提供 LLM 调用的完整日志记录能力，包括：
- 请求/响应记录
- Token 统计
- 性能指标
- 错误追踪
"""

import logging
import re
import time
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any, TypeVar

from .models import (
    CallStatus,
    LLMCallRecord,
    LLMCallRequest,
    LLMCallResponse,
    Message,
    TokenUsage,
    ToolDefinition,
    generate_id,
)
from .storage import LogStorage, get_log_storage

# 当前追踪 ID 的上下文变量
_current_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_current_session_id: ContextVar[str] = ContextVar("session_id", default="")

logger = logging.getLogger(__name__)


def set_trace_id(trace_id: str) -> None:
    """设置当前追踪 ID"""
    _current_trace_id.set(trace_id)


def get_trace_id() -> str:
    """获取当前追踪 ID"""
    return _current_trace_id.get()


def set_session_id(session_id: str) -> None:
    """设置当前会话 ID"""
    _current_session_id.set(session_id)


def get_session_id() -> str:
    """获取当前会话 ID"""
    return _current_session_id.get()


@dataclass
class LogConfig:
    """日志配置"""
    enabled: bool = True
    log_messages: bool = True  # 是否记录完整消息
    log_prompts: bool = True  # 是否记录 prompt
    log_content: bool = True  # 是否记录响应内容
    max_content_length: int = 50000  # 内容截断长度
    sanitize_sensitive: bool = True  # 是否脱敏敏感信息
    console_output: bool = True  # 是否输出到控制台


class LogSanitizer:
    """日志脱敏处理器"""

    SENSITIVE_PATTERNS = [
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?[\w-]+', 'api_key=***'),
        (r'password["\']?\s*[:=]\s*["\']?[\w-]+', 'password=***'),
        (r'secret["\']?\s*[:=]\s*["\']?[\w-]+', 'secret=***'),
        (r'token["\']?\s*[:=]\s*["\']?[\w.-]+', 'token=***'),
        (r'Bearer\s+[\w.-]+', 'Bearer ***'),
        (r'sk-[a-zA-Z0-9]+', 'sk-***'),
    ]

    @classmethod
    def sanitize(cls, content: str) -> str:
        """脱敏处理"""
        if not content:
            return content

        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        return content


class LLMLogger:
    """LLM 调用日志记录器"""

    def __init__(
        self,
        storage: LogStorage | None = None,
        config: LogConfig | None = None,
    ):
        self.storage = storage or get_log_storage()
        self.config = config or LogConfig()
        self._pending_calls: dict[str, LLMCallRecord] = {}

    def log_request(
        self,
        model: str,
        messages: list[dict[str, str]],
        system_prompt: str = "",
        user_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        caller: str = "",
        purpose: str = "",
        provider: str = "",
        extra_params: dict[str, Any] | None = None,
    ) -> str:
        """
        记录 LLM 请求

        Returns:
            call_id: 调用 ID，用于关联响应
        """
        if not self.config.enabled:
            return generate_id("llm")

        call_id = generate_id("llm")
        trace_id = get_trace_id() or generate_id("trace")
        session_id = get_session_id()

        # 转换消息格式
        msg_list = []
        if self.config.log_messages:
            for m in messages:
                content = m.get("content", "")
                if self.config.sanitize_sensitive:
                    content = LogSanitizer.sanitize(content)
                if len(content) > self.config.max_content_length:
                    content = content[:self.config.max_content_length] + "...[truncated]"
                msg_list.append(Message(
                    role=m.get("role", "user"),
                    content=content,
                ))

        # 处理 prompts
        sys_prompt = system_prompt
        usr_prompt = user_prompt
        if self.config.sanitize_sensitive:
            sys_prompt = LogSanitizer.sanitize(sys_prompt)
            usr_prompt = LogSanitizer.sanitize(usr_prompt)

        # 转换工具定义
        tool_defs = []
        if tools:
            for t in tools:
                tool_defs.append(ToolDefinition(
                    name=t.get("name", t.get("function", {}).get("name", "")),
                    description=t.get("description", t.get("function", {}).get("description", "")),
                    parameters=t.get("parameters", t.get("function", {}).get("parameters", {})),
                ))

        request = LLMCallRequest(
            call_id=call_id,
            trace_id=trace_id,
            session_id=session_id,
            timestamp=datetime.now(),
            model=model,
            provider=provider,
            messages=msg_list,
            system_prompt=sys_prompt if self.config.log_prompts else "",
            user_prompt=usr_prompt if self.config.log_prompts else "",
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tool_defs,
            caller=caller,
            purpose=purpose,
            extra_params=extra_params or {},
        )

        record = LLMCallRecord(request=request)
        self._pending_calls[call_id] = record

        # 控制台输出（使用 DEBUG 级别，避免重复写入数据库）
        # 完整的结构化日志由 storage.save_llm_call 记录
        if self.config.console_output:
            logger.debug(
                f"[LLM Request] call_id={call_id} model={model} "
                f"messages={len(messages)} tools={len(tools or [])} "
                f"caller={caller} purpose={purpose}"
            )

        return call_id

    def log_response(
        self,
        call_id: str,
        content: str = "",
        tool_calls: list[dict[str, Any]] | None = None,
        finish_reason: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        duration_ms: float = 0,
        first_token_ms: float = 0,
        success: bool = True,
        error_message: str = "",
        error_type: str = "",
        retry_count: int = 0,
        provider_request_id: str = "",
    ) -> None:
        """记录 LLM 响应"""
        if not self.config.enabled:
            return

        record = self._pending_calls.pop(call_id, None)
        if not record:
            logger.warning(f"No pending request found for call_id={call_id}")
            return

        # 处理内容
        resp_content = content
        if self.config.sanitize_sensitive:
            resp_content = LogSanitizer.sanitize(resp_content)
        if not self.config.log_content:
            resp_content = f"[content hidden, length={len(content)}]"
        elif len(resp_content) > self.config.max_content_length:
            resp_content = resp_content[:self.config.max_content_length] + "...[truncated]"

        response = LLMCallResponse(
            call_id=call_id,
            timestamp=datetime.now(),
            content=resp_content,
            tool_calls=tool_calls or [],
            finish_reason=finish_reason,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens or (prompt_tokens + completion_tokens),
            ),
            duration_ms=duration_ms,
            first_token_ms=first_token_ms,
            status=CallStatus.SUCCESS if success else CallStatus.FAILED,
            error_message=error_message,
            error_type=error_type,
            retry_count=retry_count,
            provider_request_id=provider_request_id,
        )

        record.response = response

        # 保存到存储
        try:
            self.storage.save_llm_call(record)
        except Exception as e:
            logger.error(f"Failed to save LLM call record: {e}")

        # 控制台输出（使用 DEBUG 级别，避免重复写入数据库）
        # 完整的结构化日志由 storage.save_llm_call 记录
        if self.config.console_output:
            status_str = "SUCCESS" if success else f"FAILED: {error_message}"
            logger.debug(
                f"[LLM Response] call_id={call_id} status={status_str} "
                f"tokens={total_tokens} duration={duration_ms:.0f}ms "
                f"finish_reason={finish_reason}"
            )

    def log_error(
        self,
        call_id: str,
        error: Exception,
        duration_ms: float = 0,
        retry_count: int = 0,
    ) -> None:
        """记录 LLM 调用错误"""
        self.log_response(
            call_id=call_id,
            success=False,
            error_message=str(error),
            error_type=type(error).__name__,
            duration_ms=duration_ms,
            retry_count=retry_count,
        )

    def get_call(self, call_id: str) -> LLMCallRecord | None:
        """获取调用记录"""
        return self.storage.get_llm_call(call_id)

    def query_calls(
        self,
        trace_id: str | None = None,
        session_id: str | None = None,
        model: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: CallStatus | None = None,
        limit: int = 100,
    ) -> list[LLMCallRecord]:
        """查询调用记录"""
        return self.storage.query_llm_calls(
            trace_id=trace_id,
            session_id=session_id,
            model=model,
            start_time=start_time,
            end_time=end_time,
            status=status,
            limit=limit,
        )

    def get_stats(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """获取统计信息"""
        return self.storage.get_stats(start_time=start_time, end_time=end_time)


# 全局日志实例
_llm_logger: LLMLogger | None = None


def get_llm_logger() -> LLMLogger:
    """获取全局 LLM 日志实例"""
    global _llm_logger
    if _llm_logger is None:
        _llm_logger = LLMLogger()
    return _llm_logger


def configure_llm_logger(
    storage: LogStorage | None = None,
    config: LogConfig | None = None,
) -> LLMLogger:
    """配置全局 LLM 日志实例"""
    global _llm_logger
    _llm_logger = LLMLogger(storage=storage, config=config)
    return _llm_logger


# 类型变量
T = TypeVar("T")


def logged_llm_call(
    model: str = "",
    caller: str = "",
    purpose: str = "",
    provider: str = "",
):
    """
    LLM 调用日志装饰器

    用于装饰异步 LLM 调用函数，自动记录请求和响应。

    Args:
        model: 模型名称（如果函数参数中没有）
        caller: 调用方标识
        purpose: 调用目的
        provider: 提供商

    Example:
        @logged_llm_call(caller="field_filler", purpose="fill_style")
        async def call_openai(messages, model="gpt-4", **kwargs):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            llm_logger = get_llm_logger()

            # 提取参数
            actual_model = kwargs.get("model", model)
            messages = kwargs.get("messages", [])
            if args and isinstance(args[0], list):
                messages = args[0]

            # 记录请求
            call_id = llm_logger.log_request(
                model=actual_model,
                messages=messages,
                system_prompt=kwargs.get("system_prompt", ""),
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 4096),
                tools=kwargs.get("tools"),
                caller=caller or func.__module__,
                purpose=purpose or func.__name__,
                provider=provider,
            )

            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # 提取响应信息
                duration_ms = (time.time() - start_time) * 1000

                # 尝试从结果中提取信息
                content = ""
                tool_calls = []
                usage = {}
                finish_reason = ""
                provider_request_id = ""

                if hasattr(result, "choices") and result.choices:
                    choice = result.choices[0]
                    if hasattr(choice, "message"):
                        content = getattr(choice.message, "content", "") or ""
                        tool_calls = getattr(choice.message, "tool_calls", []) or []
                    finish_reason = getattr(choice, "finish_reason", "")

                if hasattr(result, "usage"):
                    usage = {
                        "prompt_tokens": getattr(result.usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(result.usage, "completion_tokens", 0),
                        "total_tokens": getattr(result.usage, "total_tokens", 0),
                    }

                if hasattr(result, "id"):
                    provider_request_id = result.id

                # 处理 tool_calls
                tc_list = []
                if tool_calls:
                    for tc in tool_calls:
                        if hasattr(tc, "function"):
                            tc_list.append({
                                "id": getattr(tc, "id", ""),
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                }
                            })
                        elif isinstance(tc, dict):
                            tc_list.append(tc)

                # 记录响应
                llm_logger.log_response(
                    call_id=call_id,
                    content=content,
                    tool_calls=tc_list,
                    finish_reason=finish_reason,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    duration_ms=duration_ms,
                    success=True,
                    provider_request_id=provider_request_id,
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                llm_logger.log_error(
                    call_id=call_id,
                    error=e,
                    duration_ms=duration_ms,
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            llm_logger = get_llm_logger()

            actual_model = kwargs.get("model", model)
            messages = kwargs.get("messages", [])
            if args and isinstance(args[0], list):
                messages = args[0]

            call_id = llm_logger.log_request(
                model=actual_model,
                messages=messages,
                system_prompt=kwargs.get("system_prompt", ""),
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 4096),
                tools=kwargs.get("tools"),
                caller=caller or func.__module__,
                purpose=purpose or func.__name__,
                provider=provider,
            )

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # 简单处理同步结果
                content = ""
                if isinstance(result, dict):
                    content = result.get("content", "")
                elif hasattr(result, "content"):
                    content = result.content or ""

                llm_logger.log_response(
                    call_id=call_id,
                    content=content,
                    duration_ms=duration_ms,
                    success=True,
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                llm_logger.log_error(call_id=call_id, error=e, duration_ms=duration_ms)
                raise

        # 根据函数类型返回对应的包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class LLMCallContext:
    """
    LLM 调用上下文管理器

    用于手动管理 LLM 调用的日志记录。

    Example:
        async with LLMCallContext(
            model="gpt-4",
            messages=messages,
            caller="my_service",
        ) as ctx:
            response = await client.chat(messages)
            ctx.set_response(response)
    """

    def __init__(
        self,
        model: str,
        messages: list[dict[str, str]],
        caller: str = "",
        purpose: str = "",
        provider: str = "",
        **kwargs,
    ):
        self.model = model
        self.messages = messages
        self.caller = caller
        self.purpose = purpose
        self.provider = provider
        self.kwargs = kwargs
        self.call_id: str | None = None
        self.start_time: float = 0
        self._llm_logger = get_llm_logger()

    def __enter__(self):
        self.call_id = self._llm_logger.log_request(
            model=self.model,
            messages=self.messages,
            caller=self.caller,
            purpose=self.purpose,
            provider=self.provider,
            **self.kwargs,
        )
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is not None:
            self._llm_logger.log_error(
                call_id=self.call_id,
                error=exc_val,
                duration_ms=duration_ms,
            )
        return False

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)

    def set_response(
        self,
        content: str = "",
        tool_calls: list[dict[str, Any]] | None = None,
        finish_reason: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        provider_request_id: str = "",
    ):
        """设置响应信息"""
        duration_ms = (time.time() - self.start_time) * 1000
        self._llm_logger.log_response(
            call_id=self.call_id,
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            success=True,
            provider_request_id=provider_request_id,
        )

    def set_error(self, error: Exception):
        """设置错误信息"""
        duration_ms = (time.time() - self.start_time) * 1000
        self._llm_logger.log_error(
            call_id=self.call_id,
            error=error,
            duration_ms=duration_ms,
        )
