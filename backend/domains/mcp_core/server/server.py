"""
MCP 服务器基类

提供可扩展的 MCP 服务器框架，基于 FastAPI 实现。
支持:
- 结构化日志
- 统一错误处理
"""

import json
import time
import logging
from typing import Any, Dict, List, Optional, Type
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    MCP_PROTOCOL_VERSION,
)
from ..base.tool import ToolRegistry, BaseTool
from ..base.resource import BaseResourceProvider
from ..base.prompt import BasePromptProvider, EmptyPromptProvider
from ..middleware.error_handler import (
    MCPError,
    ErrorHandler,
    MethodNotFoundError,
    ToolNotFoundError,
    ToolExecutionError,
)
from ..config import MCPConfig

# 延迟导入可观测性模块（避免循环导入）
_logger = None
_mcp_logger = None


def get_server_logger():
    """获取服务器 logger"""
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


class BaseMCPServer:
    """
    MCP 服务器基类

    提供 MCP 协议的核心处理逻辑，子类可扩展工具、资源和 Prompt。

    使用方式:
        class MyMCPServer(BaseMCPServer):
            def __init__(self, config=None):
                super().__init__(config)
                self._register_tools()
                self._register_resources()

            def _register_tools(self):
                self.tool_registry.register(MyTool())

            def _create_resource_provider(self):
                return MyResourceProvider()
    """

    def __init__(
        self,
        config: Optional[MCPConfig] = None,
    ):
        """
        初始化服务器

        Args:
            config: MCP 配置
        """
        self.config = config or MCPConfig()
        self.tool_registry = ToolRegistry()
        self.resource_provider: Optional[BaseResourceProvider] = None
        self.prompt_provider: BasePromptProvider = EmptyPromptProvider()

        # 错误处理
        self.error_handler = ErrorHandler(log_stack_traces=True)

        # 服务器状态
        self._start_time = datetime.now()
        self._ready = False

        # 子类可在构造后调用 _setup() 完成初始化
        self._setup()
        self._ready = True

    def _setup(self) -> None:
        """
        初始化设置

        子类应覆盖此方法来注册工具、资源等。
        """
        pass

    def register_tool(self, tool: BaseTool, category: Optional[str] = None) -> None:
        """注册工具"""
        self.tool_registry.register(tool, category)

    def register_tool_class(self, tool_class: Type[BaseTool], category: Optional[str] = None, **kwargs) -> None:
        """注册工具类"""
        self.tool_registry.register_class(tool_class, category, **kwargs)

    def set_resource_provider(self, provider: BaseResourceProvider) -> None:
        """设置资源提供者"""
        self.resource_provider = provider

    def set_prompt_provider(self, provider: BasePromptProvider) -> None:
        """设置 Prompt 提供者"""
        self.prompt_provider = provider

    def get_health_status(self) -> Dict[str, Any]:
        """
        获取健康状态

        子类可覆盖 _get_extended_health_status() 方法添加额外状态信息。
        """
        uptime = (datetime.now() - self._start_time).total_seconds()
        status = {
            "status": "healthy" if self._ready else "starting",
            "uptime_seconds": round(uptime, 2),
            "server_name": self.config.server_name,
            "version": self.config.server_version,
        }

        # 允许子类添加额外状态信息
        extended = self._get_extended_health_status()
        if extended:
            status.update(extended)

        return status

    def _get_extended_health_status(self) -> Optional[Dict[str, Any]]:
        """
        获取扩展健康状态信息

        子类可覆盖此方法来添加自定义的健康状态信息，如缓存状态、连接池状态等。

        Returns:
            扩展状态字典，或 None
        """
        return None

    def get_ready_status(self) -> Dict[str, Any]:
        """获取就绪状态"""
        checks = {
            "tools_registered": len(self.tool_registry) > 0,
            "resources_configured": self.resource_provider is not None,
        }
        all_ready = all(checks.values()) and self._ready
        return {
            "ready": all_ready,
            "checks": checks,
        }

    async def handle_request(
        self,
        request: JSONRPCRequest,
        client_ip: str = "",
        client_name: str = "",
        user_agent: str = "",
    ) -> JSONRPCResponse:
        """
        处理 JSON-RPC 请求

        Args:
            request: JSON-RPC 请求
            client_ip: 客户端 IP
            client_name: 客户端名称
            user_agent: User-Agent
        """
        start_time = time.perf_counter()

        # 获取 MCP 请求日志记录器
        mcp_logger = get_mcp_request_logger()
        mcp_request_id = None

        # 记录 MCP 请求开始
        if mcp_logger:
            mcp_request_id = mcp_logger.log_request(
                server_name=self.config.server_name,
                server_port=self.config.port,
                method=request.method,
                params=request.params or {},
                jsonrpc_id=request.id,
                client_ip=client_ip,
                client_name=client_name,
                user_agent=user_agent,
            )

        try:
            result = await self._dispatch(request)
            response = JSONRPCResponse.success(request.id, result)

            duration_ms = (time.perf_counter() - start_time) * 1000

            # 记录 MCP 请求完成（包含完整排查信息）
            if mcp_logger and mcp_request_id:
                response_str = json.dumps(response.to_dict(), ensure_ascii=False)
                mcp_logger.log_response(
                    request_id=mcp_request_id,
                    duration_ms=duration_ms,
                    success=True,
                    response_size=len(response_str),
                    response_summary=self._generate_response_summary(request.method, result),
                    response_data=self._extract_response_data(request.method, result),
                )

        except MCPError as e:
            response = JSONRPCResponse.make_error(request.id, e.to_dict())
            duration_ms = (time.perf_counter() - start_time) * 1000

            # 记录 MCP 请求失败
            if mcp_logger and mcp_request_id:
                mcp_logger.log_response(
                    request_id=mcp_request_id,
                    duration_ms=duration_ms,
                    success=False,
                    error_code=e.code if hasattr(e, 'code') else -1,
                    error_message=str(e),
                )

        except Exception as e:
            logger.exception(f"处理请求失败: {request.method}")
            mcp_error = self.error_handler.handle(e, {"method": request.method})
            response = JSONRPCResponse.make_error(request.id, mcp_error.to_dict())
            duration_ms = (time.perf_counter() - start_time) * 1000

            # 记录 MCP 请求失败
            if mcp_logger and mcp_request_id:
                mcp_logger.log_response(
                    request_id=mcp_request_id,
                    duration_ms=duration_ms,
                    success=False,
                    error_message=str(e),
                )

        return response

    def _generate_response_summary(self, method: str, result: Any) -> str:
        """生成响应摘要"""
        if result is None:
            return ""

        try:
            if method == "tools/list":
                tools = result.get("tools", [])
                return f"返回 {len(tools)} 个工具"
            elif method == "tools/call":
                content = result.get("content", [])
                is_error = result.get("isError", False)
                if is_error:
                    return "工具执行失败"
                return f"工具执行成功，返回 {len(content)} 个内容块"
            elif method == "resources/list":
                resources = result.get("resources", [])
                return f"返回 {len(resources)} 个资源"
            elif method == "resources/read":
                contents = result.get("contents", [])
                return f"返回 {len(contents)} 个资源内容"
            elif method == "prompts/list":
                prompts = result.get("prompts", [])
                return f"返回 {len(prompts)} 个 Prompt"
            elif method == "initialize":
                return "初始化完成"
            else:
                return ""
        except Exception:
            return ""

    def _extract_response_data(self, method: str, result: Any) -> Dict[str, Any]:
        """
        提取响应数据用于日志排查

        返回结构化的响应信息，便于问题排查。
        """
        if result is None:
            return {}

        try:
            if method == "tools/list":
                tools = result.get("tools", [])
                return {
                    "tool_count": len(tools),
                    "tool_names": [t.get("name", "") for t in tools[:20]],  # 最多记录20个
                }
            elif method == "tools/call":
                content = result.get("content", [])
                is_error = result.get("isError", False)

                # 提取工具返回的文本内容
                response_text = ""
                for item in content:
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        # 限制长度，避免日志过大
                        if len(text) > 2000:
                            response_text = text[:2000] + "...(truncated)"
                        else:
                            response_text = text
                        break

                return {
                    "is_error": is_error,
                    "content_count": len(content),
                    "response_text": response_text,
                }
            elif method == "resources/list":
                resources = result.get("resources", [])
                return {
                    "resource_count": len(resources),
                    "resource_uris": [r.get("uri", "") for r in resources[:20]],
                }
            elif method == "resources/read":
                contents = result.get("contents", [])
                return {
                    "content_count": len(contents),
                }
            elif method == "prompts/list":
                prompts = result.get("prompts", [])
                return {
                    "prompt_count": len(prompts),
                    "prompt_names": [p.get("name", "") for p in prompts[:20]],
                }
            elif method == "initialize":
                capabilities = result.get("capabilities", {})
                return {
                    "capabilities": list(capabilities.keys()),
                    "server_name": result.get("serverInfo", {}).get("name", ""),
                }
            else:
                return {}
        except Exception:
            return {}

    async def _dispatch(self, request: JSONRPCRequest) -> Any:
        """分发请求到对应的处理器"""
        method = request.method
        params = request.params or {}

        # MCP 核心方法
        if method == "initialize":
            return await self._handle_initialize(params)
        elif method == "initialized" or method == "notifications/initialized":
            return await self._handle_initialized(params)
        elif method == "ping":
            return {}

        # 工具相关
        elif method == "tools/list":
            return await self._handle_tools_list(params)
        elif method == "tools/call":
            return await self._handle_tools_call(params)

        # 资源相关
        elif method == "resources/list":
            return await self._handle_resources_list(params)
        elif method == "resources/read":
            return await self._handle_resources_read(params)

        # Prompt 相关
        elif method == "prompts/list":
            return await self._handle_prompts_list(params)
        elif method == "prompts/get":
            return await self._handle_prompts_get(params)

        else:
            raise MethodNotFoundError(method)

    async def _handle_initialize(self, params: dict) -> dict:
        """处理初始化请求"""
        client_info = params.get("clientInfo", {})
        logger.info(f"MCP 客户端连接: {client_info.get('name', 'unknown')}")

        # 构建服务器能力
        capabilities = {}

        if self.config.enable_tools and len(self.tool_registry) > 0:
            capabilities["tools"] = {}

        if self.config.enable_resources and self.resource_provider is not None:
            capabilities["resources"] = {}

        if self.config.enable_prompts and self.prompt_provider is not None:
            prompts = self.prompt_provider.list_prompts()
            if prompts:
                capabilities["prompts"] = {}

        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": capabilities,
            "serverInfo": {
                "name": self.config.server_name,
                "version": self.config.server_version,
            },
        }

    async def _handle_initialized(self, params: dict) -> dict:
        """处理初始化完成通知"""
        logger.info("MCP 连接初始化完成")
        return {}

    async def _handle_tools_list(self, params: dict) -> dict:
        """列出所有可用工具"""
        tools = self.tool_registry.get_mcp_tools()
        return {"tools": tools}

    async def _handle_tools_call(self, params: dict) -> dict:
        """调用工具"""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            raise ToolNotFoundError("未提供工具名称")

        # 获取工具
        tool = self.tool_registry.get(name)
        if tool is None:
            raise ToolNotFoundError(name)

        # 执行工具
        try:
            result = await self.tool_registry.execute(name, arguments)
        except Exception as e:
            raise ToolExecutionError(name, str(e), cause=e)

        # 转换为 MCP 格式
        if result.success:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result.data, ensure_ascii=False, indent=2),
                    }
                ],
            }
        else:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"error": result.error}, ensure_ascii=False),
                    }
                ],
                "isError": True,
            }

    async def _handle_resources_list(self, params: dict) -> dict:
        """列出所有可用资源"""
        if self.resource_provider is None:
            return {"resources": []}

        resources = self.resource_provider.list_resources()
        return {
            "resources": [r.to_mcp_format() for r in resources]
        }

    async def _handle_resources_read(self, params: dict) -> dict:
        """读取资源"""
        uri = params.get("uri")
        if not uri:
            raise ValueError("缺少资源 URI")

        if self.resource_provider is None:
            raise ValueError("资源提供者未配置")

        content = await self.resource_provider.read_resource(uri)
        if content is None:
            raise ValueError(f"资源不存在: {uri}")

        return {
            "contents": [content.to_mcp_format()]
        }

    async def _handle_prompts_list(self, params: dict) -> dict:
        """列出所有可用 Prompt"""
        prompts = self.prompt_provider.list_prompts()
        return {
            "prompts": [p.to_mcp_format() for p in prompts]
        }

    async def _handle_prompts_get(self, params: dict) -> dict:
        """获取 Prompt"""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            raise ValueError("缺少 Prompt 名称")

        result = await self.prompt_provider.get_prompt(name, arguments)
        if result is None:
            raise ValueError(f"Prompt 不存在: {name}")

        return result.to_mcp_format()


def create_mcp_app(
    server: BaseMCPServer,
) -> FastAPI:
    """
    创建 MCP FastAPI 应用

    Args:
        server: MCP 服务器实例

    Returns:
        FastAPI 应用实例
    """
    from contextlib import asynccontextmanager

    config = server.config

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用生命周期管理"""
        # Startup: 初始化日志存储
        try:
            from ..logging import init_log_store, shutdown_log_store
            await init_log_store()
            logger.info(f"MCP Server {config.server_name} log store initialized")
        except Exception as e:
            logger.warning(f"Log store init skipped: {e}")

        yield

        # Shutdown: 关闭日志存储
        try:
            from ..logging import shutdown_log_store
            await shutdown_log_store()
            logger.info(f"MCP Server {config.server_name} log store shutdown")
        except Exception as e:
            logger.warning(f"Log store shutdown error: {e}")

    app = FastAPI(
        title=f"{config.server_name} MCP Server",
        description="Model Context Protocol 服务",
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
            "protocol_version": MCP_PROTOCOL_VERSION,
            "endpoints": {
                "mcp": "/mcp",
                "health": "/health",
                "ready": "/ready",
            },
        }

    @app.get("/health")
    async def health():
        """
        健康检查端点

        用于负载均衡器和容器编排系统检查服务存活状态。
        """
        return server.get_health_status()

    @app.get("/ready")
    async def ready():
        """
        就绪检查端点

        用于 Kubernetes 等系统检查服务是否准备好接收流量。
        """
        status = server.get_ready_status()
        if not status["ready"]:
            return JSONResponse(content=status, status_code=503)
        return status

    @app.get("/stats")
    async def stats():
        """服务统计信息"""
        return {
            "health": server.get_health_status(),
            "ready": server.get_ready_status(),
            "tools_count": len(server.tool_registry),
        }

    @app.post("/mcp")
    async def mcp_endpoint(request: Request):
        """MCP JSON-RPC 端点"""
        # 提取客户端信息用于日志记录
        client_ip = request.client.host if request.client else ""
        user_agent = request.headers.get("user-agent", "")
        # 尝试从自定义头获取客户端名称
        client_name = request.headers.get("x-client-name", "")

        # 解析请求
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(
                content=JSONRPCResponse.make_error(
                    None,
                    JSONRPCError.parse_error()
                ).to_dict(),
                status_code=400,
            )

        # 处理批量请求
        if isinstance(body, list):
            responses = []
            for item in body:
                req = JSONRPCRequest.from_dict(item)
                resp = await server.handle_request(
                    req,
                    client_ip=client_ip,
                    client_name=client_name,
                    user_agent=user_agent,
                )
                responses.append(resp.to_dict())
            return JSONResponse(content=responses)

        # 处理单个请求
        req = JSONRPCRequest.from_dict(body)
        resp = await server.handle_request(
            req,
            client_ip=client_ip,
            client_name=client_name,
            user_agent=user_agent,
        )
        return JSONResponse(content=resp.to_dict())

    @app.get("/mcp")
    async def mcp_sse(request: Request):
        """MCP SSE 端点（用于服务器推送）"""
        async def event_generator():
            yield f"data: {json.dumps({'type': 'connected'}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )

    # ============================================
    # SSE 任务进度推送端点
    # ============================================

    @app.get("/mcp/sse/tasks")
    async def list_sse_tasks():
        """列出所有正在运行的任务"""
        from .sse import get_task_manager

        manager = get_task_manager()
        tasks = manager.list_tasks()
        return {
            "count": len(tasks),
            "tasks": [t.to_dict() for t in tasks],
        }

    @app.get("/mcp/sse/tasks/{task_id}")
    async def get_task_status(task_id: str):
        """获取任务状态"""
        from .sse import get_task_manager

        manager = get_task_manager()
        task = manager.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        return task.to_dict()

    @app.get("/mcp/sse/tasks/{task_id}/stream")
    async def stream_task_progress(task_id: str, request: Request):
        """
        SSE 端点：订阅任务进度流

        客户端可以通过此端点实时接收任务进度更新。

        使用方式:
            const eventSource = new EventSource('/mcp/sse/tasks/{task_id}/stream');
            eventSource.addEventListener('progress', (e) => {
                const data = JSON.parse(e.data);
                console.log(data.progress, data.message);
            });

        事件类型:
            - progress: 进度更新
            - error: 错误事件
        """
        from .sse import get_task_manager

        manager = get_task_manager()

        async def event_generator():
            async for event in manager.subscribe(task_id):
                # 检查客户端是否断开
                if await request.is_disconnected():
                    break
                yield event

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
            },
        )

    return app


def run_server(
    server: BaseMCPServer,
    host: Optional[str] = None,
    port: Optional[int] = None,
    log_level: str = "info",
    reload: bool = False,
    use_structlog: bool = True,
):
    """
    运行 MCP 服务器

    Args:
        server: MCP 服务器实例
        host: 监听地址，默认使用配置值
        port: 监听端口，默认使用配置值
        log_level: 日志级别
        reload: 是否启用热重载
        use_structlog: 是否使用 structlog
    """
    config = server.config
    host = host or config.host
    port = port or config.port

    # 配置日志
    import os
    log_format_env = os.getenv("LOG_FORMAT", "json").lower()
    use_json = log_format_env == "json"

    # 从服务器配置中获取服务名称
    service_name = f"mcp-{config.name}" if hasattr(config, "name") else "mcp"

    if use_structlog:
        try:
            from ..logging import configure_logging, LogConfig, LogFormat
            log_config = LogConfig(
                level=log_level.upper(),
                format=LogFormat.JSON if use_json else LogFormat.CONSOLE,
                service_name=service_name,
            )
            configure_logging(log_config, service_name=service_name)
        except ImportError:
            logging.basicConfig(
                level=getattr(logging, log_level.upper()),
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
    else:
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    logger.info(f"启动 MCP 服务器: http://{host}:{port}")
    logger.info(f"MCP 端点: http://{host}:{port}/mcp")
    logger.info(f"健康检查: http://{host}:{port}/health")
    logger.info(f"就绪检查: http://{host}:{port}/ready")

    # 创建应用
    app = create_mcp_app(server)

    # 运行服务器
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        reload=reload,
    )
