"""
工具调用日志记录器

提供 MCP 工具调用的日志记录能力，包括：
- 工具请求/响应记录
- 执行时间统计
- 错误追踪
- 结果摘要
"""

import json
import logging
import time
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any, TypeVar

from .llm_logger import get_trace_id
from .models import (
    CallStatus,
    ToolCallRecord,
    ToolCallRequest,
    ToolCallResponse,
    generate_id,
)
from .storage import LogStorage, get_log_storage

logger = logging.getLogger(__name__)


def summarize_result(result: Any, max_length: int = 500) -> str:
    """
    生成结果摘要

    Args:
        result: 工具执行结果
        max_length: 最大长度

    Returns:
        结果摘要字符串
    """
    if result is None:
        return "None"

    if isinstance(result, str):
        if len(result) <= max_length:
            return result
        return result[:max_length] + "...[truncated]"

    if isinstance(result, (int, float, bool)):
        return str(result)

    if isinstance(result, (list, tuple)):
        if len(result) == 0:
            return "[]"
        return f"[{len(result)} items]"

    if isinstance(result, dict):
        if len(result) == 0:
            return "{}"
        keys = list(result.keys())[:5]
        if len(result) > 5:
            return f"{{keys: {keys}... ({len(result)} total)}}"
        return f"{{keys: {keys}}}"

    # 尝试 JSON 序列化
    try:
        json_str = json.dumps(result, ensure_ascii=False, default=str)
        if len(json_str) <= max_length:
            return json_str
        return json_str[:max_length] + "...[truncated]"
    except (TypeError, ValueError):
        return f"<{type(result).__name__}>"


def get_result_type(result: Any) -> str:
    """获取结果类型"""
    if result is None:
        return "null"
    if isinstance(result, str):
        return "string"
    if isinstance(result, bool):
        return "boolean"
    if isinstance(result, int):
        return "integer"
    if isinstance(result, float):
        return "number"
    if isinstance(result, list):
        return "array"
    if isinstance(result, dict):
        return "object"
    return type(result).__name__


class ToolLogger:
    """工具调用日志记录器"""

    def __init__(
        self,
        storage: LogStorage | None = None,
        enabled: bool = True,
        log_arguments: bool = True,
        log_results: bool = True,
        max_result_length: int = 5000,
        console_output: bool = True,
    ):
        self.storage = storage or get_log_storage()
        self.enabled = enabled
        self.log_arguments = log_arguments
        self.log_results = log_results
        self.max_result_length = max_result_length
        self.console_output = console_output
        self._pending_calls: dict[str, ToolCallRecord] = {}

    def log_request(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        llm_call_id: str = "",
        tool_version: str = "",
    ) -> str:
        """
        记录工具调用请求

        Returns:
            call_id: 调用 ID
        """
        if not self.enabled:
            return generate_id("tool")

        call_id = generate_id("tool")
        trace_id = get_trace_id()

        # 处理参数
        args = {}
        if self.log_arguments:
            args = arguments.copy()
            # 限制大参数的长度
            for key, value in args.items():
                if isinstance(value, str) and len(value) > 10000:
                    args[key] = value[:10000] + "...[truncated]"

        request = ToolCallRequest(
            call_id=call_id,
            trace_id=trace_id,
            llm_call_id=llm_call_id,
            timestamp=datetime.now(),
            tool_name=tool_name,
            tool_version=tool_version,
            arguments=args,
        )

        record = ToolCallRecord(request=request)
        self._pending_calls[call_id] = record

        if self.console_output:
            args_summary = summarize_result(arguments, 200)
            logger.info(
                f"[Tool Request] call_id={call_id} tool={tool_name} "
                f"args={args_summary}"
            )

        return call_id

    def log_response(
        self,
        call_id: str,
        result: Any = None,
        duration_ms: float = 0,
        success: bool = True,
        error_message: str = "",
        error_type: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        """记录工具调用响应"""
        if not self.enabled:
            return

        record = self._pending_calls.pop(call_id, None)
        if not record:
            logger.warning(f"No pending request found for call_id={call_id}")
            return

        # 处理结果
        result_summary = summarize_result(result)
        result_type = get_result_type(result)

        # 存储结果（可能截断）
        stored_result = result
        if self.log_results:
            try:
                result_str = json.dumps(result, ensure_ascii=False, default=str)
                if len(result_str) > self.max_result_length:
                    stored_result = {
                        "_truncated": True,
                        "_type": result_type,
                        "_summary": result_summary,
                    }
            except (TypeError, ValueError):
                stored_result = {"_type": result_type, "_summary": result_summary}
        else:
            stored_result = {"_hidden": True, "_type": result_type}

        response = ToolCallResponse(
            call_id=call_id,
            timestamp=datetime.now(),
            result=stored_result,
            result_summary=result_summary,
            result_type=result_type,
            duration_ms=duration_ms,
            status=CallStatus.SUCCESS if success else CallStatus.FAILED,
            error_message=error_message,
            error_type=error_type,
            extra=extra or {},
        )

        record.response = response

        # 保存到存储
        try:
            self.storage.save_tool_call(record)
        except Exception as e:
            logger.error(f"Failed to save tool call record: {e}")

        if self.console_output:
            status_str = "SUCCESS" if success else f"FAILED: {error_message}"
            logger.info(
                f"[Tool Response] call_id={call_id} status={status_str} "
                f"duration={duration_ms:.0f}ms result_type={result_type}"
            )

    def log_error(
        self,
        call_id: str,
        error: Exception,
        duration_ms: float = 0,
    ) -> None:
        """记录工具调用错误"""
        self.log_response(
            call_id=call_id,
            success=False,
            error_message=str(error),
            error_type=type(error).__name__,
            duration_ms=duration_ms,
        )

    def get_call(self, call_id: str) -> ToolCallRecord | None:
        """获取调用记录"""
        return self.storage.get_tool_call(call_id)

    def query_calls(
        self,
        trace_id: str | None = None,
        llm_call_id: str | None = None,
        tool_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: CallStatus | None = None,
        limit: int = 100,
    ) -> list[ToolCallRecord]:
        """查询调用记录"""
        return self.storage.query_tool_calls(
            trace_id=trace_id,
            llm_call_id=llm_call_id,
            tool_name=tool_name,
            start_time=start_time,
            end_time=end_time,
            status=status,
            limit=limit,
        )


# 全局工具日志实例
_tool_logger: ToolLogger | None = None


def get_tool_logger() -> ToolLogger:
    """获取全局工具日志实例"""
    global _tool_logger
    if _tool_logger is None:
        _tool_logger = ToolLogger()
    return _tool_logger


def configure_tool_logger(
    storage: LogStorage | None = None,
    **kwargs,
) -> ToolLogger:
    """配置全局工具日志实例"""
    global _tool_logger
    _tool_logger = ToolLogger(storage=storage, **kwargs)
    return _tool_logger


# 类型变量
T = TypeVar("T")


def logged_tool(
    tool_name: str = "",
    tool_version: str = "",
    log_result: bool = True,
    extra_extractor: Callable[[Any], dict[str, Any]] | None = None,
):
    """
    工具调用日志装饰器

    Args:
        tool_name: 工具名称（默认使用函数名）
        tool_version: 工具版本
        log_result: 是否记录结果
        extra_extractor: 额外信息提取函数

    Example:
        @logged_tool(tool_name="list_factors")
        async def list_factors(style: str = None, limit: int = 100):
            ...
    """
    def decorator(func: Callable) -> Callable:
        actual_tool_name = tool_name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tool_logger = get_tool_logger()

            # 记录请求
            call_id = tool_logger.log_request(
                tool_name=actual_tool_name,
                arguments=kwargs,
                tool_version=tool_version,
            )

            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # 提取额外信息
                extra = {}
                if extra_extractor:
                    try:
                        extra = extra_extractor(result)
                    except Exception:
                        pass

                # 记录响应
                tool_logger.log_response(
                    call_id=call_id,
                    result=result if log_result else None,
                    duration_ms=duration_ms,
                    success=True,
                    extra=extra,
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                tool_logger.log_error(
                    call_id=call_id,
                    error=e,
                    duration_ms=duration_ms,
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tool_logger = get_tool_logger()

            call_id = tool_logger.log_request(
                tool_name=actual_tool_name,
                arguments=kwargs,
                tool_version=tool_version,
            )

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                extra = {}
                if extra_extractor:
                    try:
                        extra = extra_extractor(result)
                    except Exception:
                        pass

                tool_logger.log_response(
                    call_id=call_id,
                    result=result if log_result else None,
                    duration_ms=duration_ms,
                    success=True,
                    extra=extra,
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                tool_logger.log_error(call_id=call_id, error=e, duration_ms=duration_ms)
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class ToolCallContext:
    """
    工具调用上下文管理器

    Example:
        with ToolCallContext(tool_name="calculate_factor", arguments=args) as ctx:
            result = calculate(args)
            ctx.set_result(result)
    """

    def __init__(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        tool_version: str = "",
        llm_call_id: str = "",
    ):
        self.tool_name = tool_name
        self.arguments = arguments
        self.tool_version = tool_version
        self.llm_call_id = llm_call_id
        self.call_id: str | None = None
        self.start_time: float = 0
        self._tool_logger = get_tool_logger()
        self._result_set = False

    def __enter__(self):
        self.call_id = self._tool_logger.log_request(
            tool_name=self.tool_name,
            arguments=self.arguments,
            tool_version=self.tool_version,
            llm_call_id=self.llm_call_id,
        )
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is not None:
            self._tool_logger.log_error(
                call_id=self.call_id,
                error=exc_val,
                duration_ms=duration_ms,
            )
        elif not self._result_set:
            # 如果没有显式设置结果，记录一个成功但无结果的响应
            self._tool_logger.log_response(
                call_id=self.call_id,
                duration_ms=duration_ms,
                success=True,
            )
        return False

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)

    def set_result(
        self,
        result: Any,
        extra: dict[str, Any] | None = None,
    ):
        """设置执行结果"""
        duration_ms = (time.time() - self.start_time) * 1000
        self._tool_logger.log_response(
            call_id=self.call_id,
            result=result,
            duration_ms=duration_ms,
            success=True,
            extra=extra,
        )
        self._result_set = True

    def set_error(self, error: Exception):
        """设置错误"""
        duration_ms = (time.time() - self.start_time) * 1000
        self._tool_logger.log_error(
            call_id=self.call_id,
            error=error,
            duration_ms=duration_ms,
        )
        self._result_set = True
