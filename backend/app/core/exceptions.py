"""Exception handling utilities for FastAPI routes.

统一异常处理，集成 domains.core 的 ApplicationError 体系。

提供:
- 异常到 HTTP 响应的自动转换
- FastAPI exception_handler 注册
- 装饰器模式的异常处理
"""

import logging
from functools import wraps
from typing import Callable, TypeVar, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.schemas.common import ApiResponse
from domains.core import (
    ErrorCategory,
    ApplicationError,
    NotFoundError,
    ValidationError,
    ConflictError,
    BusinessError,
    ExternalServiceError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# 向后兼容的 ServiceError（已废弃，推荐使用 ApplicationError）
# ============================================================================

class ServiceError(ApplicationError):
    """
    服务层错误（已废弃）

    推荐使用 mcp_core.exceptions 中的具体异常类型:
    - NotFoundError: 资源不存在
    - ValidationError: 参数验证错误
    - BusinessError: 业务逻辑错误
    """

    def __init__(self, message: str, status_code: int = 400):
        # 映射 HTTP 状态码到错误分类
        category_map = {
            400: ErrorCategory.VALIDATION,
            404: ErrorCategory.NOT_FOUND,
            409: ErrorCategory.CONFLICT,
            403: ErrorCategory.PERMISSION,
            422: ErrorCategory.BUSINESS,
            502: ErrorCategory.EXTERNAL,
            500: ErrorCategory.INTERNAL,
        }
        category = category_map.get(status_code, ErrorCategory.INTERNAL)

        super().__init__(
            code="SERVICE_ERROR",
            message=message,
            category=category,
        )
        self._status_code = status_code

    @property
    def status_code(self) -> int:
        return self._status_code


# ============================================================================
# FastAPI 异常处理器
# ============================================================================

def register_exception_handlers(app: FastAPI) -> None:
    """
    注册 FastAPI 异常处理器

    将 ApplicationError 及其子类自动转换为 HTTP 响应。

    使用示例:
        app = FastAPI()
        register_exception_handlers(app)
    """

    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request,
        exc: ApplicationError
    ) -> JSONResponse:
        """处理 ApplicationError 及其子类"""
        logger.warning(
            f"Application error: [{exc.code}] {exc.message}",
            extra={"details": exc.details}
        )

        return JSONResponse(
            status_code=exc.http_status_code,
            content={
                "success": False,
                "error": exc.message,
                "code": exc.code,
                "details": exc.details,
            }
        )

    @app.exception_handler(ServiceError)
    async def service_error_handler(
        request: Request,
        exc: ServiceError
    ) -> JSONResponse:
        """处理 ServiceError（向后兼容）"""
        logger.warning(f"Service error: {exc.message}")

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.message,
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """全局异常处理器 - 捕获所有未处理的异常"""
        # 记录完整的异常堆栈
        logger.exception(
            f"Unhandled exception: {type(exc).__name__}: {exc}",
            extra={
                "path": request.url.path,
                "method": request.method,
            }
        )

        # 返回通用错误响应
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Internal server error: {type(exc).__name__}",
                "detail": str(exc),
            }
        )


# ============================================================================
# 装饰器模式异常处理
# ============================================================================

def handle_service_error(operation_name: str):
    """
    API 端点异常处理装饰器

    自动捕获异常并转换为适当的响应:
    - ApplicationError: 使用其 HTTP 状态码
    - HTTPException: 直接抛出
    - 其他异常: 返回 ApiResponse(success=False)

    Args:
        operation_name: 操作名称（用于日志）

    Usage:
        @router.post("/endpoint")
        @handle_service_error("Create factor")
        async def create_factor(request: Request) -> ApiResponse:
            # ... endpoint logic
            return ApiResponse(success=True, data=result)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTP exceptions (404, 403, etc.)
                raise
            except ApplicationError as e:
                logger.error(f"{operation_name} failed: [{e.code}] {e.message}")
                raise HTTPException(
                    status_code=e.http_status_code,
                    detail=e.message
                )
            except ServiceError as e:
                logger.error(f"{operation_name} failed: {e.message}")
                raise HTTPException(status_code=e.status_code, detail=e.message)
            except Exception as e:
                logger.error(f"{operation_name} failed: {e}", exc_info=True)
                return ApiResponse(success=False, error=str(e))

        return wrapper

    return decorator


def handle_errors(
    log_errors: bool = True,
    reraise_http: bool = True,
    default_status: int = 500,
):
    """
    通用异常处理装饰器

    提供更灵活的配置选项。

    Args:
        log_errors: 是否记录错误日志
        reraise_http: 是否重新抛出 HTTPException
        default_status: 未知异常的默认 HTTP 状态码

    Usage:
        @router.get("/resource")
        @handle_errors(log_errors=True)
        async def get_resource():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                if reraise_http:
                    raise
                return ApiResponse(success=False, error="HTTP error occurred")
            except ApplicationError as e:
                if log_errors:
                    logger.error(f"[{e.code}] {e.message}", extra={"details": e.details})
                raise HTTPException(
                    status_code=e.http_status_code,
                    detail=e.message
                )
            except Exception as e:
                if log_errors:
                    logger.exception(f"Unexpected error: {e}")
                raise HTTPException(
                    status_code=default_status,
                    detail=str(e)
                )

        return wrapper

    return decorator


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "ServiceError",
    "register_exception_handlers",
    "handle_service_error",
    "handle_errors",
]
