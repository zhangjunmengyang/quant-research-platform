"""FastAPI application entry point."""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.routes.v1.router import api_router
from app.core.config import settings
from app.core.events import create_start_handler, create_stop_handler
from app.core.exceptions import register_exception_handlers

# 配置结构化日志
from domains.mcp_core.logging import configure_logging, get_logger, bind_request_context, clear_request_context

configure_logging(service_name="api")
logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """HTTP 请求日志中间件"""

    # 不记录日志的路径前缀
    SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next) -> Response:
        # 跳过不需要记录的路径
        if any(request.url.path.startswith(p) for p in self.SKIP_PATHS):
            return await call_next(request)

        # 生成请求 ID
        request_id = str(uuid.uuid4())[:8]
        bind_request_context(request_id)

        # 记录请求开始
        start_time = time.time()
        method = request.method
        path = request.url.path
        query = str(request.query_params) if request.query_params else ""
        client_ip = request.client.host if request.client else ""
        user_agent = request.headers.get("user-agent", "")[:100]

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # 记录响应
            logger.info(
                "http_request",
                request_id=request_id,
                method=method,
                path=path,
                query=query,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                client_ip=client_ip,
                user_agent=user_agent,
            )

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "http_request_error",
                request_id=request_id,
                method=method,
                path=path,
                query=query,
                duration_ms=round(duration_ms, 2),
                client_ip=client_ip,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        finally:
            clear_request_context()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await create_start_handler()()
    yield
    # Shutdown
    await create_stop_handler()()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="量化因子管理平台 REST API",
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware (在 CORS 之后添加，先执行)
    app.add_middleware(RequestLoggingMiddleware)

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Register exception handlers
    register_exception_handlers(app)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": settings.VERSION}

    return app


app = create_application()
