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

    def _register_handlers(self):
        """注册 MCP 协议处理器"""

        @self.mcp_server.list_tools()
        async def list_tools() -> list[types.Tool]:
            """列出所有可用工具"""
            mcp_tools = self.base_server.tool_registry.get_mcp_tools()
            return [
                types.Tool(
                    name=t["name"],
                    description=t.get("description", ""),
                    inputSchema=t.get("inputSchema", {"type": "object", "properties": {}}),
                )
                for t in mcp_tools
            ]

        @self.mcp_server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """调用工具"""
            import json

            try:
                result = await self.base_server.tool_registry.execute(name, arguments)

                if result.success:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(result.data, ensure_ascii=False, indent=2),
                        )
                    ]
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps({"error": result.error}, ensure_ascii=False),
                        )
                    ]
            except Exception as e:
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
                resources = self.base_server.resource_provider.list_resources()
                return [
                    types.Resource(
                        uri=r.uri,
                        name=r.name,
                        description=r.description,
                        mimeType=r.mime_type,
                    )
                    for r in resources
                ]

            @self.mcp_server.read_resource()
            async def read_resource(uri: str) -> str:
                """读取资源"""
                content = await self.base_server.resource_provider.read_resource(uri)
                if content is None:
                    raise ValueError(f"资源不存在: {uri}")
                return content.text if hasattr(content, 'text') else str(content)

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
        logger.info(f"MCP Server {config.server_name} 启动中...")

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

            logger.info(f"MCP Server {config.server_name} 已启动")

            yield

            # 关闭
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            logger.info(f"MCP Server {config.server_name} 已关闭")

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
