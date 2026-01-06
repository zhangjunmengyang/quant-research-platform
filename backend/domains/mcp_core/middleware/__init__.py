"""
MCP 中间件模块

提供错误处理中间件。
"""

from .error_handler import (
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
    TimeoutError,
    ServiceUnavailableError,
    ErrorHandler,
    error_boundary,
    map_exception,
    register_exception_handler,
)

__all__ = [
    # Error handling
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
    "TimeoutError",
    "ServiceUnavailableError",
    "ErrorHandler",
    "error_boundary",
    "map_exception",
    "register_exception_handler",
]
