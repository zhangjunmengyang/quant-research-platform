"""
统一错误处理中间件

提供:
- 统一的错误响应格式
- 异常分类和映射
- 错误日志记录
- 重试支持
"""

import logging
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """MCP 错误码"""
    # 标准 JSON-RPC 错误
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP 自定义错误 (-32000 到 -32099)
    TOOL_NOT_FOUND = -32001
    TOOL_EXECUTION_ERROR = -32002
    RESOURCE_NOT_FOUND = -32003
    RESOURCE_READ_ERROR = -32004
    PROMPT_NOT_FOUND = -32005
    AUTHENTICATION_ERROR = -32010
    RATE_LIMIT_ERROR = -32011
    VALIDATION_ERROR = -32020
    TIMEOUT_ERROR = -32030
    SERVICE_UNAVAILABLE = -32050


@dataclass
class MCPError(Exception):
    """
    MCP 错误基类

    所有 MCP 相关错误应继承此类。
    """
    code: ErrorCode
    message: str
    data: dict[str, Any] | None = None
    cause: Exception | None = None

    def __str__(self) -> str:
        return f"[{self.code.name}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """转换为 JSON-RPC 错误格式"""
        result = {
            "code": self.code.value,
            "message": self.message,
        }
        if self.data:
            result["data"] = self.data
        return result


# 预定义错误类型
class ParseError(MCPError):
    """解析错误"""
    def __init__(self, message: str = "Parse error", data: dict | None = None):
        super().__init__(ErrorCode.PARSE_ERROR, message, data)


class InvalidRequestError(MCPError):
    """无效请求"""
    def __init__(self, message: str = "Invalid request", data: dict | None = None):
        super().__init__(ErrorCode.INVALID_REQUEST, message, data)


class MethodNotFoundError(MCPError):
    """方法未找到"""
    def __init__(self, method: str, data: dict | None = None):
        super().__init__(
            ErrorCode.METHOD_NOT_FOUND,
            f"Method not found: {method}",
            data or {"method": method}
        )


class InvalidParamsError(MCPError):
    """参数无效"""
    def __init__(self, message: str = "Invalid params", data: dict | None = None):
        super().__init__(ErrorCode.INVALID_PARAMS, message, data)


class ToolNotFoundError(MCPError):
    """工具未找到"""
    def __init__(self, tool_name: str, data: dict | None = None):
        super().__init__(
            ErrorCode.TOOL_NOT_FOUND,
            f"Tool not found: {tool_name}",
            data or {"tool_name": tool_name}
        )


class ToolExecutionError(MCPError):
    """工具执行错误"""
    def __init__(
        self,
        tool_name: str,
        message: str,
        cause: Exception | None = None,
        data: dict | None = None
    ):
        error_data = data or {}
        error_data["tool_name"] = tool_name
        super().__init__(
            ErrorCode.TOOL_EXECUTION_ERROR,
            f"Tool execution failed: {message}",
            error_data,
            cause
        )


class ResourceNotFoundError(MCPError):
    """资源未找到"""
    def __init__(self, uri: str, data: dict | None = None):
        super().__init__(
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Resource not found: {uri}",
            data or {"uri": uri}
        )


class AuthenticationError(MCPError):
    """认证错误"""
    def __init__(self, message: str = "Authentication failed", data: dict | None = None):
        super().__init__(ErrorCode.AUTHENTICATION_ERROR, message, data)


class RateLimitError(MCPError):
    """速率限制错误"""
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        data: dict | None = None
    ):
        error_data = data or {}
        if retry_after:
            error_data["retry_after"] = retry_after
        super().__init__(ErrorCode.RATE_LIMIT_ERROR, message, error_data)


class ValidationError(MCPError):
    """验证错误"""
    def __init__(self, message: str, errors: list | None = None, data: dict | None = None):
        error_data = data or {}
        if errors:
            error_data["validation_errors"] = errors
        super().__init__(ErrorCode.VALIDATION_ERROR, message, error_data)


class TimeoutError(MCPError):
    """超时错误"""
    def __init__(self, message: str = "Request timeout", data: dict | None = None):
        super().__init__(ErrorCode.TIMEOUT_ERROR, message, data)


class ServiceUnavailableError(MCPError):
    """服务不可用"""
    def __init__(self, message: str = "Service unavailable", data: dict | None = None):
        super().__init__(ErrorCode.SERVICE_UNAVAILABLE, message, data)


# 异常映射表
_EXCEPTION_MAP: dict[type[Exception], type[MCPError]] = {}


def register_exception_handler(
    exc_type: type[Exception],
    mcp_error_type: type[MCPError]
) -> None:
    """注册异常到 MCP 错误的映射"""
    _EXCEPTION_MAP[exc_type] = mcp_error_type


def map_exception(exc: Exception) -> MCPError:
    """
    将异常映射为 MCP 错误

    Args:
        exc: 原始异常

    Returns:
        MCPError 实例
    """
    # 如果已经是 MCPError，直接返回
    if isinstance(exc, MCPError):
        return exc

    # 查找映射的错误类型
    for exc_type, error_type in _EXCEPTION_MAP.items():
        if isinstance(exc, exc_type):
            return error_type(str(exc), cause=exc)

    # 默认映射为内部错误
    return MCPError(
        code=ErrorCode.INTERNAL_ERROR,
        message=str(exc) or "Internal server error",
        data={"exception_type": type(exc).__name__},
        cause=exc
    )


class ErrorHandler:
    """
    统一错误处理器

    提供错误捕获、日志记录和响应格式化。
    """

    def __init__(
        self,
        log_stack_traces: bool = True,
        include_stack_in_response: bool = False,
    ):
        """
        初始化

        Args:
            log_stack_traces: 是否在日志中记录堆栈
            include_stack_in_response: 是否在响应中包含堆栈（仅开发环境）
        """
        self.log_stack_traces = log_stack_traces
        self.include_stack_in_response = include_stack_in_response

    def handle(self, exc: Exception, context: dict | None = None) -> MCPError:
        """
        处理异常

        Args:
            exc: 异常
            context: 上下文信息

        Returns:
            MCPError 实例
        """
        mcp_error = map_exception(exc)

        # 记录日志
        log_data = {
            "error_code": mcp_error.code.name,
            "error_message": mcp_error.message,
        }

        if context:
            log_data.update(context)

        if mcp_error.data:
            log_data["error_data"] = mcp_error.data

        if self.log_stack_traces and mcp_error.cause:
            log_data["stack_trace"] = traceback.format_exception(
                type(mcp_error.cause),
                mcp_error.cause,
                mcp_error.cause.__traceback__
            )

        # 根据错误类型选择日志级别
        if mcp_error.code.value >= -32600:
            # 客户端错误
            logger.warning("MCP 客户端错误", extra=log_data)
        else:
            # 服务器错误
            logger.error("MCP 服务器错误", extra=log_data, exc_info=mcp_error.cause)

        # 是否在响应中包含堆栈
        if self.include_stack_in_response and mcp_error.cause:
            if mcp_error.data is None:
                mcp_error.data = {}
            mcp_error.data["stack_trace"] = traceback.format_exception(
                type(mcp_error.cause),
                mcp_error.cause,
                mcp_error.cause.__traceback__
            )

        return mcp_error


def error_boundary(
    handler: ErrorHandler | None = None,
    reraise: bool = False,
    default_return: Any = None,
):
    """
    错误边界装饰器

    捕获函数中的异常并转换为 MCPError。

    Args:
        handler: 错误处理器
        reraise: 是否重新抛出 MCPError
        default_return: 出错时的默认返回值（仅当 reraise=False 时生效）
    """
    _handler = handler or ErrorHandler()

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except MCPError:
                if reraise:
                    raise
                return default_return
            except Exception as e:
                mcp_error = _handler.handle(e)
                if reraise:
                    raise mcp_error from e
                return default_return

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except MCPError:
                if reraise:
                    raise
                return default_return
            except Exception as e:
                mcp_error = _handler.handle(e)
                if reraise:
                    raise mcp_error from e
                return default_return

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# 注册常见异常映射
register_exception_handler(ValueError, InvalidParamsError)
register_exception_handler(TypeError, InvalidParamsError)
register_exception_handler(KeyError, InvalidParamsError)
register_exception_handler(FileNotFoundError, ResourceNotFoundError)
register_exception_handler(PermissionError, AuthenticationError)
