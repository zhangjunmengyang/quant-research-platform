"""
Streamable HTTP 传输层

使用官方 MCP SDK 的 StreamableHTTPServerTransport 实现 Streamable HTTP 传输。
这是 MCP 2025-03-26 规范推荐的传输方式，替代已弃用的 SSE 传输。

用法:
    from mcp_core.server.streamable_http import create_streamable_http_app, run_streamable_http_server

    server = MyMCPServer(config)
    app = create_streamable_http_app(server)

    # 或直接运行
    run_streamable_http_server(server)
"""

import json
import time
import logging
import uuid
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from mcp.server import Server
from mcp.server.streamable_http import StreamableHTTPServerTransport
import mcp.types as types

from .server import BaseMCPServer
from ..config import MCPConfig

# 延迟导入日志模块（避免循环导入）
_logger = None
_mcp_logger = None


def get_server_logger():
    """获取服务器 logger (使用 structlog)"""
    global _logger
    if _logger is None:
        try:
            from ..logging import get_logger
            _logger = get_logger(__name__)
        except ImportError:
            _logger = logging.getLogger(__name__)
    return _logger


def get_mcp_request_logger():
    """获取 MCP 请求日志记录器"""
    global _mcp_logger
    if _mcp_logger is None:
        try:
            from ..observability.mcp_logger import get_mcp_logger
            _mcp_logger = get_mcp_logger()
        except ImportError:
            _mcp_logger = None
    return _mcp_logger


logger = logging.getLogger(__name__)


class MCPServerAdapter:
    """
    适配器：将 BaseMCPServer 转换为官方 MCP SDK 的 Server

    这个适配器桥接了我们的 BaseMCPServer 实现和官方 MCP SDK，
    允许复用现有的工具、资源注册逻辑。
    """

    def __init__(self, base_server: BaseMCPServer):
        self.base_server = base_server
        self.config = base_server.config

        # 创建官方 MCP Server
        self.mcp_server = Server(self.config.server_name)

        # 注册处理器
        self._register_handlers()

    def _log_mcp_request(
        self,
        method: str,
        tool_name: str = "",
        tool_arguments: Optional[dict] = None,
        resource_uri: str = "",
        start_time: float = 0,
        success: bool = True,
        error_message: str = "",
        response_data: Optional[dict] = None,
    ):
        """记录 MCP 请求日志"""
        slog = get_server_logger()
        duration_ms = (time.time() - start_time) * 1000 if start_time else 0

        # 构造日志数据
        log_data = {
            "method": method,
            "status": "success" if success else "failed",
            "duration_ms": round(duration_ms, 2),
            "server_name": self.config.server_name,
            "server_port": self.config.port,
            "client_ip": "",  # Streamable HTTP 没有直接的 request 对象
            "tool_name": tool_name,
            "tool_arguments": json.dumps(tool_arguments, ensure_ascii=False) if tool_arguments else "",
            "resource_uri": resource_uri,
            "error_message": error_message,
        }

        # 添加响应摘要
        if response_data:
            log_data["response_data"] = json.dumps(response_data, ensure_ascii=False)[:2000]
            log_data["response_summary"] = self._make_response_summary(method, tool_name, response_data)

        # 使用 structlog 记录
        if success:
            slog.info("mcp_request", **log_data)
        else:
            slog.warning("mcp_request", **log_data)

    def _make_response_summary(self, method: str, tool_name: str, data: dict) -> str:
        """生成响应摘要"""
        if method == "tools/list":
            tool_count = data.get("tool_count", 0)
            return f"返回 {tool_count} 个工具"
        elif method == "tools/call":
            if "error" in data:
                return f"工具调用失败: {data['error'][:100]}"
            return f"工具 {tool_name} 执行成功"
        elif method == "resources/list":
            res_count = data.get("resource_count", 0)
            return f"返回 {res_count} 个资源"
        elif method == "resources/read":
            return f"读取资源成功"
        return "请求完成"

    def _register_handlers(self):
        """注册 MCP 协议处理器"""

        @self.mcp_server.list_tools()
        async def list_tools() -> list[types.Tool]:
            """列出所有可用工具"""
            start_time = time.time()
            mcp_tools = self.base_server.tool_registry.get_mcp_tools()
            result = [
                types.Tool(
                    name=t["name"],
                    description=t.get("description", ""),
                    inputSchema=t.get("inputSchema", {"type": "object", "properties": {}}),
                )
                for t in mcp_tools
            ]

            # 记录日志
            self._log_mcp_request(
                method="tools/list",
                start_time=start_time,
                success=True,
                response_data={"tool_count": len(result), "tool_names": [t["name"] for t in mcp_tools]},
            )

            return result

        @self.mcp_server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """调用工具"""
            start_time = time.time()

            try:
                result = await self.base_server.tool_registry.execute(name, arguments)

                if result.success:
                    # 记录成功日志
                    self._log_mcp_request(
                        method="tools/call",
                        tool_name=name,
                        tool_arguments=arguments,
                        start_time=start_time,
                        success=True,
                        response_data=result.data if isinstance(result.data, dict) else {"result": str(result.data)[:500]},
                    )
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(result.data, ensure_ascii=False, indent=2),
                        )
                    ]
                else:
                    # 记录失败日志
                    self._log_mcp_request(
                        method="tools/call",
                        tool_name=name,
                        tool_arguments=arguments,
                        start_time=start_time,
                        success=False,
                        error_message=result.error or "Unknown error",
                        response_data={"error": result.error},
                    )
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps({"error": result.error}, ensure_ascii=False),
                        )
                    ]
            except Exception as e:
                # 记录异常日志
                self._log_mcp_request(
                    method="tools/call",
                    tool_name=name,
                    tool_arguments=arguments,
                    start_time=start_time,
                    success=False,
                    error_message=str(e),
                    response_data={"error": str(e)},
                )
                logger.exception(f"工具调用失败: {name}")
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps({"error": str(e)}, ensure_ascii=False),
                    )
                ]

        # 注册资源处理器（如果有）
        if self.base_server.resource_provider is not None:

            @self.mcp_server.list_resources()
            async def list_resources() -> list[types.Resource]:
                """列出所有可用资源"""
                start_time = time.time()
                resources = self.base_server.resource_provider.list_resources()
                result = [
                    types.Resource(
                        uri=r.uri,
                        name=r.name,
                        description=r.description,
                        mimeType=r.mime_type,
                    )
                    for r in resources
                ]

                # 记录日志
                self._log_mcp_request(
                    method="resources/list",
                    start_time=start_time,
                    success=True,
                    response_data={"resource_count": len(result)},
                )

                return result

            @self.mcp_server.read_resource()
            async def read_resource(uri: str) -> str:
                """读取资源"""
                start_time = time.time()
                try:
                    content = await self.base_server.resource_provider.read_resource(uri)
                    if content is None:
                        raise ValueError(f"资源不存在: {uri}")

                    # 记录日志
                    self._log_mcp_request(
                        method="resources/read",
                        resource_uri=uri,
                        start_time=start_time,
                        success=True,
                        response_data={"uri": uri, "has_content": content is not None},
                    )

                    return content.text if hasattr(content, 'text') else str(content)
                except Exception as e:
                    self._log_mcp_request(
                        method="resources/read",
                        resource_uri=uri,
                        start_time=start_time,
                        success=False,
                        error_message=str(e),
                    )
                    raise

        # 注册 Prompt 处理器（如果有）
        prompts = self.base_server.prompt_provider.list_prompts()
        if prompts:

            @self.mcp_server.list_prompts()
            async def list_prompts() -> list[types.Prompt]:
                """列出所有可用 Prompt"""
                prompts = self.base_server.prompt_provider.list_prompts()
                return [
                    types.Prompt(
                        name=p.name,
                        description=p.description,
                        arguments=[
                            types.PromptArgument(
                                name=arg.name,
                                description=arg.description,
                                required=arg.required,
                            )
                            for arg in (p.arguments or [])
                        ],
                    )
                    for p in prompts
                ]

            @self.mcp_server.get_prompt()
            async def get_prompt(name: str, arguments: dict | None = None) -> types.GetPromptResult:
                """获取 Prompt"""
                result = await self.base_server.prompt_provider.get_prompt(name, arguments or {})
                if result is None:
                    raise ValueError(f"Prompt 不存在: {name}")
                return types.GetPromptResult(
                    description=result.description,
                    messages=[
                        types.PromptMessage(
                            role=m.role,
                            content=types.TextContent(type="text", text=m.content),
                        )
                        for m in result.messages
                    ],
                )


def create_streamable_http_app(
    server: BaseMCPServer,
) -> FastAPI:
    """
    创建支持 Streamable HTTP 的 FastAPI 应用

    Args:
        server: MCP 服务器实例

    Returns:
        FastAPI 应用实例
    """
    config = server.config

    # 创建适配器
    adapter = MCPServerAdapter(server)

    # 创建 Streamable HTTP 传输
    # 不使用 session ID，允许无状态请求
    transport = StreamableHTTPServerTransport(
        mcp_session_id=None,  # 不强制 session
        is_json_response_enabled=True,  # 启用 JSON 响应模式，更简单
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用生命周期管理"""
        # 初始化日志存储
        try:
            from ..logging.config import configure_logging, init_log_store, shutdown_log_store
            configure_logging(service_name=f"mcp-{config.server_name}")
            await init_log_store()
            log_store_initialized = True
        except Exception as e:
            logger.warning(f"日志存储初始化失败: {e}")
            log_store_initialized = False

        slog = get_server_logger()
        slog.info(f"MCP Server {config.server_name} 启动中...")

        # 启动 MCP 连接
        async with transport.connect() as (read_stream, write_stream):
            # 在后台运行 MCP 服务器
            import asyncio

            async def run_mcp():
                await adapter.mcp_server.run(
                    read_stream,
                    write_stream,
                    adapter.mcp_server.create_initialization_options(),
                )

            task = asyncio.create_task(run_mcp())

            # 存储到 app.state 供路由使用
            app.state.mcp_transport = transport
            app.state.mcp_task = task

            slog.info(
                "mcp_server_started",
                server_name=config.server_name,
                port=config.port,
                log_store=log_store_initialized,
            )

            yield

            # 关闭
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            # 关闭日志存储
            if log_store_initialized:
                try:
                    await shutdown_log_store()
                except Exception as e:
                    logger.warning(f"日志存储关闭失败: {e}")

            slog.info(
                "mcp_server_stopped",
                server_name=config.server_name,
            )

    app = FastAPI(
        title=f"{config.server_name} MCP Server",
        description="Model Context Protocol 服务 (Streamable HTTP)",
        version=config.server_version,
        lifespan=lifespan,
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        """服务器信息"""
        return {
            "name": config.server_name,
            "version": config.server_version,
            "protocol": "MCP",
            "transport": "streamable-http",
            "endpoints": {
                "mcp": "/mcp",
                "health": "/health",
                "ready": "/ready",
            },
        }

    @app.get("/health")
    async def health():
        """健康检查端点"""
        return server.get_health_status()

    @app.get("/ready")
    async def ready():
        """就绪检查端点"""
        status = server.get_ready_status()
        if not status["ready"]:
            return JSONResponse(content=status, status_code=503)
        return status

    # 挂载 MCP Streamable HTTP 端点
    # StreamableHTTPServerTransport.handle_request 是一个 ASGI 应用
    app.mount("/mcp", app=transport.handle_request)

    return app


def run_streamable_http_server(
    server: BaseMCPServer,
    host: Optional[str] = None,
    port: Optional[int] = None,
    log_level: str = "info",
    reload: bool = False,
):
    """
    运行 Streamable HTTP MCP 服务器

    Args:
        server: MCP 服务器实例
        host: 监听地址，默认使用配置值
        port: 监听端口，默认使用配置值
        log_level: 日志级别
        reload: 是否启用热重载
    """
    import uvicorn

    config = server.config
    host = host or config.host
    port = port or config.port

    logger.info(f"启动 MCP 服务器 (Streamable HTTP): http://{host}:{port}")
    logger.info(f"MCP 端点: http://{host}:{port}/mcp")
    logger.info(f"健康检查: http://{host}:{port}/health")

    # 创建应用
    app = create_streamable_http_app(server)

    # 运行服务器
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        reload=reload,
    )
