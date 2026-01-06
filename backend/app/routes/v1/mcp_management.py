"""MCP management routes.

提供 MCP 服务器管理功能:
- 查看所有 MCP 服务器状态
- 启动/停止/重启 MCP 服务器
- 查看工具和资源列表
- 执行工具调用
- 获取服务器统计信息
"""

import asyncio
import logging
import subprocess
import signal
import os
import sys
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.schemas.common import ApiResponse
from app.schemas.mcp import (
    MCPServerStatus,
    MCPServerInfo,
    MCPServerHealth,
    MCPServerStats,
    MCPToolInfo,
    MCPResourceInfo,
    MCPToolCallRequest,
    MCPToolCallResult,
    MCPServerAction,
    MCPServerActionRequest,
    MCPServerActionResult,
    MCPDashboardStats,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# MCP 服务器配置（按显示顺序排列：数据 -> 因子 -> 策略 -> 笔记）
MCP_SERVERS = {
    "data-hub": {
        "name": "data-hub",
        "display_name": "数据中心",
        "description": "K线数据加载和因子计算服务",
        "host": "localhost",
        "port": 6790,
        "module": "domains.data_hub.api.mcp.server",
    },
    "factor-hub": {
        "name": "factor-hub",
        "display_name": "因子知识库",
        "description": "因子管理、分析和查询服务",
        "host": "localhost",
        "port": 6789,
        "module": "domains.factor_hub.api.mcp.server",
    },
    "strategy-hub": {
        "name": "strategy-hub",
        "display_name": "策略知识库",
        "description": "策略管理和回测服务",
        "host": "localhost",
        "port": 6791,
        "module": "domains.strategy_hub.api.mcp.server",
    },
    "note-hub": {
        "name": "note-hub",
        "display_name": "经验笔记",
        "description": "研究笔记和经验记录服务",
        "host": "localhost",
        "port": 6792,
        "module": "domains.note_hub.api.mcp.server",
    },
}

# 进程管理器（存储启动的进程）
_server_processes: Dict[str, subprocess.Popen] = {}


async def _check_server_health(name: str, host: str, port: int) -> Optional[MCPServerHealth]:
    """检查 MCP 服务器健康状态

    优化：先用 socket 快速检查端口是否在用，避免不必要的 HTTP 超时等待
    """
    # 快速检查：如果端口没在用，直接返回 None（服务器未运行）
    if not _is_port_in_use(port):
        return None

    try:
        # 端口在用，尝试 HTTP 健康检查
        # 降低超时时间：端口已确认在用，连接应该很快
        timeout = httpx.Timeout(connect=1.0, read=3.0, write=1.0, pool=1.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"http://{host}:{port}/health")
            if response.status_code == 200:
                data = response.json()
                return MCPServerHealth(
                    status=data.get("status", "unknown"),
                    uptime_seconds=data.get("uptime_seconds", 0),
                    server_name=data.get("server_name", name),
                    version=data.get("version", ""),
                )
    except httpx.ConnectError as e:
        logger.debug(f"Health check connect failed for {name}: {e}")
    except httpx.TimeoutException as e:
        # 超时说明进程可能卡死，记录警告
        logger.warning(f"Health check timeout for {name}: server may be unresponsive")
    except Exception as e:
        logger.debug(f"Health check failed for {name}: {e}")
    return None


def _is_port_in_use(port: int) -> bool:
    """检查端口是否被占用

    使用 socket 连接测试，比 netstat/lsof 快很多
    """
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setblocking(False)  # 非阻塞模式
            result = s.connect_ex(("127.0.0.1", port))
            # 0 = 连接成功，端口在用
            # 10035 (WSAEWOULDBLOCK) = Windows 非阻塞连接中
            # 115 (EINPROGRESS) = Linux 非阻塞连接中
            if result == 0:
                return True
            # 连接中的状态也表示端口可能在用，用 select 等待一小段时间
            if result in (10035, 115, 36):  # WSAEWOULDBLOCK, EINPROGRESS, EINPROGRESS(macOS)
                import select
                _, writable, _ = select.select([], [s], [], 0.05)  # 50ms
                if writable:
                    # 检查是否真的连接成功
                    err = s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                    return err == 0
            return False
    except Exception:
        return False


async def _is_port_in_use_async(port: int) -> bool:
    """异步检查端口是否被占用"""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _is_port_in_use, port)


async def _get_server_stats(name: str, host: str, port: int) -> Optional[MCPServerStats]:
    """获取 MCP 服务器统计信息"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://{host}:{port}/stats")
            if response.status_code == 200:
                data = response.json()
                health_data = data.get("health", {})
                return MCPServerStats(
                    name=name,
                    health=MCPServerHealth(**health_data) if health_data else None,
                    ready=data.get("ready", {}).get("ready", False),
                    tools_count=data.get("tools_count", 0),
                    logging_stats=data.get("logging_stats"),
                    cache_stats=data.get("cache_stats"),
                    rate_limiter=data.get("rate_limiter"),
                )
    except Exception as e:
        logger.debug(f"Stats check failed for {name}: {e}")
    return None


async def _get_server_tools(name: str, host: str, port: int) -> List[MCPToolInfo]:
    """获取 MCP 服务器的工具列表"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"http://{host}:{port}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "1",
                    "method": "tools/list",
                    "params": {},
                },
            )
            if response.status_code == 200:
                data = response.json()
                result = data.get("result", {})
                tools = result.get("tools", [])
                return [
                    MCPToolInfo(
                        name=t.get("name", ""),
                        description=t.get("description", ""),
                        category=t.get("category"),
                        input_schema=t.get("inputSchema"),
                        server=name,
                    )
                    for t in tools
                ]
    except Exception as e:
        logger.debug(f"Tools list failed for {name}: {e}")
    return []


async def _get_server_resources(name: str, host: str, port: int) -> List[MCPResourceInfo]:
    """获取 MCP 服务器的资源列表"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"http://{host}:{port}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "1",
                    "method": "resources/list",
                    "params": {},
                },
            )
            if response.status_code == 200:
                data = response.json()
                result = data.get("result", {})
                resources = result.get("resources", [])
                return [
                    MCPResourceInfo(
                        uri=r.get("uri", ""),
                        name=r.get("name", ""),
                        description=r.get("description", ""),
                        mime_type=r.get("mimeType"),
                        server=name,
                    )
                    for r in resources
                ]
    except Exception as e:
        logger.debug(f"Resources list failed for {name}: {e}")
    return []


async def _call_server_tool(
    name: str, host: str, port: int, tool: str, arguments: Dict[str, Any]
) -> MCPToolCallResult:
    """调用 MCP 服务器工具"""
    import time
    start_time = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"http://{host}:{port}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "1",
                    "method": "tools/call",
                    "params": {
                        "name": tool,
                        "arguments": arguments,
                    },
                },
            )
            duration_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                if data.get("error"):
                    return MCPToolCallResult(
                        success=False,
                        error=str(data["error"]),
                        duration_ms=duration_ms,
                    )
                result = data.get("result", {})
                return MCPToolCallResult(
                    success=not result.get("isError", False),
                    content=result.get("content"),
                    error=result.get("error") if result.get("isError") else None,
                    duration_ms=duration_ms,
                )
            else:
                return MCPToolCallResult(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text}",
                    duration_ms=duration_ms,
                )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return MCPToolCallResult(
            success=False,
            error=str(e),
            duration_ms=duration_ms,
        )


def _start_server_process(name: str, config: dict) -> bool:
    """启动 MCP 服务器进程"""
    global _server_processes

    if name in _server_processes:
        proc = _server_processes[name]
        if proc.poll() is None:
            logger.warning(f"Server {name} is already running")
            return True

    try:
        # 获取 Python 解释器路径
        python_path = sys.executable

        # 构建启动命令
        module = config["module"]
        port = config["port"]

        # 计算路径
        # __file__ = backend/app/routes/v1/mcp_management.py
        # backend_dir = backend/
        # project_root = QuantResearchMCP/
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        project_root = os.path.dirname(backend_dir)

        # 使用 subprocess 启动
        env = os.environ.copy()
        # PYTHONPATH 需要同时包含项目根目录（config 模块）和 backend 目录（domains 模块）
        # Windows 使用分号，Unix 使用冒号
        path_sep = ";" if sys.platform == "win32" else ":"
        env["PYTHONPATH"] = f"{project_root}{path_sep}{backend_dir}"

        # Windows 上需要指定编码，否则会因为 GBK 编码导致 UnicodeDecodeError
        proc = subprocess.Popen(
            [python_path, "-m", module],
            env=env,
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",  # 遇到无法解码的字符时用替代字符
        )

        _server_processes[name] = proc
        logger.info(f"Started MCP server {name} on port {port}, pid={proc.pid}")
        return True

    except Exception as e:
        logger.exception(f"Failed to start MCP server {name}")
        return False


async def _wait_for_server_ready(
    name: str, host: str, port: int, max_wait_seconds: int = 15
) -> Optional[MCPServerHealth]:
    """
    等待服务器启动并返回健康状态。

    使用指数退避策略：初始等待 0.5 秒，逐步增加到最大 2 秒。
    总等待时间不超过 max_wait_seconds。

    Args:
        name: 服务器名称
        host: 服务器主机
        port: 服务器端口
        max_wait_seconds: 最大等待秒数

    Returns:
        健康状态（如果就绪），否则返回 None
    """
    import time

    start_time = time.monotonic()
    wait_time = 0.5  # 初始等待时间
    max_interval = 2.0  # 最大间隔

    while (time.monotonic() - start_time) < max_wait_seconds:
        health = await _check_server_health(name, host, port)
        if health:
            return health

        await asyncio.sleep(wait_time)
        # 指数退避：每次增加 50%，但不超过最大间隔
        wait_time = min(wait_time * 1.5, max_interval)

    return None


def _find_process_by_port(port: int) -> Optional[int]:
    """通过端口查找进程 PID

    注意：此函数仅在需要停止进程时调用，不在健康检查路径上使用
    """
    try:
        if sys.platform == "win32":
            # Windows: 使用 netstat 只查找特定端口，减少输出量
            # -a: 显示所有连接  -n: 数字格式  -o: 显示 PID  -p TCP: 只显示 TCP
            result = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace",
            )
            for line in result.stdout.split("\n"):
                # 精确匹配端口号，避免匹配到包含该数字的其他端口
                # 格式: TCP    0.0.0.0:6789    0.0.0.0:0    LISTENING    12345
                if f":{port} " in line or f":{port}\t" in line:
                    if "LISTENING" in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            return int(parts[-1])
        else:
            # Unix: 使用 lsof 查找占用端口的进程
            result = subprocess.run(
                ["lsof", "-t", "-i", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                # 可能有多个 PID，取第一个
                pids = result.stdout.strip().split("\n")
                return int(pids[0])
    except Exception as e:
        logger.debug(f"Failed to find process by port {port}: {e}")
    return None


def _stop_server_process(name: str) -> bool:
    """停止 MCP 服务器进程"""
    global _server_processes

    config = MCP_SERVERS.get(name)
    if not config:
        logger.warning(f"Server {name} not found in config")
        return False

    port = config["port"]
    stopped = False

    # 方法1: 如果在进程列表中，直接停止
    if name in _server_processes:
        proc = _server_processes[name]
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            del _server_processes[name]
            stopped = True
            logger.info(f"Stopped MCP server {name} from process list")
        except Exception as e:
            logger.exception(f"Failed to stop MCP server {name} from process list")

    # 方法2: 通过端口查找并停止进程
    pid = _find_process_by_port(port)
    if pid:
        try:
            import time
            if sys.platform == "win32":
                # Windows: 使用 taskkill 命令
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=10)
            else:
                # Unix: 使用信号
                os.kill(pid, signal.SIGTERM)
                # 等待进程结束
                for _ in range(10):
                    time.sleep(0.5)
                    try:
                        os.kill(pid, 0)  # 检查进程是否存在
                    except OSError:
                        break  # 进程已结束
                else:
                    # 超时，强制杀死
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except OSError:
                        pass
            stopped = True
            logger.info(f"Stopped MCP server {name} (pid={pid}) by port {port}")
        except OSError as e:
            if e.errno == 3:  # No such process
                stopped = True
            else:
                logger.exception(f"Failed to kill process {pid} for server {name}")
        except Exception as e:
            logger.exception(f"Failed to kill process {pid} for server {name}")

    if not stopped:
        # 没有找到进程，可能已经停止
        logger.info(f"Server {name} process not found, may already be stopped")
        return True

    return stopped


# ============================================
# API Endpoints
# ============================================

@router.get("/servers", response_model=ApiResponse[List[MCPServerInfo]])
async def list_servers():
    """
    获取所有 MCP 服务器状态

    返回所有配置的 MCP 服务器及其当前状态。
    """
    servers = []

    # 并发检查所有服务器
    async def check_server(name: str, config: dict) -> MCPServerInfo:
        health = await _check_server_health(name, config["host"], config["port"])
        port = config["port"]

        if health:
            # 获取工具和资源数量
            tools = await _get_server_tools(name, config["host"], config["port"])
            resources = await _get_server_resources(name, config["host"], config["port"])

            return MCPServerInfo(
                name=name,
                display_name=config["display_name"],
                description=config["description"],
                host=config["host"],
                port=config["port"],
                status=MCPServerStatus.RUNNING,
                uptime_seconds=health.uptime_seconds,
                version=health.version,
                tools_count=len(tools),
                resources_count=len(resources),
                last_health_check=datetime.now(),
            )
        else:
            # 健康检查失败，检查端口是否被占用
            port_in_use = _is_port_in_use(port)
            if port_in_use:
                # 端口被占用但健康检查失败，说明进程卡死
                return MCPServerInfo(
                    name=name,
                    display_name=config["display_name"],
                    description=config["description"],
                    host=config["host"],
                    port=config["port"],
                    status=MCPServerStatus.UNRESPONSIVE,
                    last_health_check=datetime.now(),
                    error_message="进程存在但不响应请求，可能已卡死",
                )
            else:
                return MCPServerInfo(
                    name=name,
                    display_name=config["display_name"],
                    description=config["description"],
                    host=config["host"],
                    port=config["port"],
                    status=MCPServerStatus.STOPPED,
                    last_health_check=datetime.now(),
                )

    tasks = [check_server(name, config) for name, config in MCP_SERVERS.items()]
    servers = await asyncio.gather(*tasks)

    return ApiResponse(data=list(servers))


@router.get("/servers/{name}", response_model=ApiResponse[MCPServerInfo])
async def get_server(name: str):
    """
    获取指定 MCP 服务器状态
    """
    if name not in MCP_SERVERS:
        raise HTTPException(status_code=404, detail=f"Server not found: {name}")

    config = MCP_SERVERS[name]
    port = config["port"]
    health = await _check_server_health(name, config["host"], port)

    if health:
        tools = await _get_server_tools(name, config["host"], port)
        resources = await _get_server_resources(name, config["host"], port)

        server_info = MCPServerInfo(
            name=name,
            display_name=config["display_name"],
            description=config["description"],
            host=config["host"],
            port=port,
            status=MCPServerStatus.RUNNING,
            uptime_seconds=health.uptime_seconds,
            version=health.version,
            tools_count=len(tools),
            resources_count=len(resources),
            last_health_check=datetime.now(),
        )
    else:
        # 健康检查失败，检查端口是否被占用
        port_in_use = _is_port_in_use(port)
        if port_in_use:
            server_info = MCPServerInfo(
                name=name,
                display_name=config["display_name"],
                description=config["description"],
                host=config["host"],
                port=port,
                status=MCPServerStatus.UNRESPONSIVE,
                last_health_check=datetime.now(),
                error_message="进程存在但不响应请求，可能已卡死",
            )
        else:
            server_info = MCPServerInfo(
                name=name,
                display_name=config["display_name"],
                description=config["description"],
                host=config["host"],
                port=port,
                status=MCPServerStatus.STOPPED,
                last_health_check=datetime.now(),
            )

    return ApiResponse(data=server_info)


@router.get("/servers/{name}/stats", response_model=ApiResponse[MCPServerStats])
async def get_server_stats(name: str):
    """
    获取 MCP 服务器详细统计信息
    """
    if name not in MCP_SERVERS:
        raise HTTPException(status_code=404, detail=f"Server not found: {name}")

    config = MCP_SERVERS[name]
    stats = await _get_server_stats(name, config["host"], config["port"])

    if stats is None:
        raise HTTPException(status_code=503, detail=f"Server {name} is not available")

    return ApiResponse(data=stats)


@router.post("/servers/{name}/action", response_model=ApiResponse[MCPServerActionResult])
async def server_action(name: str, request: MCPServerActionRequest, background_tasks: BackgroundTasks):
    """
    执行 MCP 服务器操作（启动/停止/重启）
    """
    if name not in MCP_SERVERS:
        raise HTTPException(status_code=404, detail=f"Server not found: {name}")

    config = MCP_SERVERS[name]
    action = request.action

    if action == MCPServerAction.START:
        # 先检查是否已经运行
        health = await _check_server_health(name, config["host"], config["port"])
        if health:
            return ApiResponse(
                data=MCPServerActionResult(
                    success=True,
                    message=f"Server {name} is already running",
                    server=name,
                    new_status=MCPServerStatus.RUNNING,
                )
            )

        # 检查端口是否被占用（可能是卡死的进程）
        port = config["port"]
        if _is_port_in_use(port):
            # 健康检查失败但端口被占用，说明进程卡死，需要先清理
            logger.warning(f"Port {port} is in use but health check failed, cleaning up zombie process")
            _stop_server_process(name)
            # 等待端口释放
            for _ in range(10):
                await asyncio.sleep(0.5)
                if not _is_port_in_use(port):
                    break
            else:
                return ApiResponse(
                    data=MCPServerActionResult(
                        success=False,
                        message=f"Failed to clean up zombie process on port {port}",
                        server=name,
                        new_status=MCPServerStatus.ERROR,
                    )
                )

        # 启动服务器
        success = _start_server_process(name, config)
        if success:
            # 使用指数退避等待服务器启动
            health = await _wait_for_server_ready(
                name, config["host"], config["port"], max_wait_seconds=15
            )

            if health:
                return ApiResponse(
                    data=MCPServerActionResult(
                        success=True,
                        message=f"Server {name} started successfully",
                        server=name,
                        new_status=MCPServerStatus.RUNNING,
                    )
                )
            else:
                return ApiResponse(
                    data=MCPServerActionResult(
                        success=False,
                        message=f"Server {name} started but health check failed (timeout after 15s)",
                        server=name,
                        new_status=MCPServerStatus.ERROR,
                    )
                )
        else:
            return ApiResponse(
                data=MCPServerActionResult(
                    success=False,
                    message=f"Failed to start server {name}",
                    server=name,
                    new_status=MCPServerStatus.ERROR,
                )
            )

    elif action == MCPServerAction.STOP:
        success = _stop_server_process(name)
        return ApiResponse(
            data=MCPServerActionResult(
                success=success,
                message=f"Server {name} stopped" if success else f"Failed to stop server {name}",
                server=name,
                new_status=MCPServerStatus.STOPPED if success else MCPServerStatus.ERROR,
            )
        )

    elif action == MCPServerAction.RESTART:
        _stop_server_process(name)
        await asyncio.sleep(1)
        success = _start_server_process(name, config)

        # 使用指数退避等待服务器启动
        health = await _wait_for_server_ready(
            name, config["host"], config["port"], max_wait_seconds=15
        )

        return ApiResponse(
            data=MCPServerActionResult(
                success=success and health is not None,
                message=f"Server {name} restarted" if (success and health) else f"Failed to restart server {name}",
                server=name,
                new_status=MCPServerStatus.RUNNING if health else MCPServerStatus.ERROR,
            )
        )

    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


@router.post("/servers/start-all", response_model=ApiResponse[List[MCPServerActionResult]])
async def start_all_servers():
    """
    启动所有已停止的 MCP 服务器

    并发启动所有未运行的服务器，返回每个服务器的启动结果。
    """
    results = []

    async def start_if_stopped(name: str, config: dict) -> MCPServerActionResult:
        port = config["port"]

        # 检查是否已经运行
        health = await _check_server_health(name, config["host"], port)
        if health:
            return MCPServerActionResult(
                success=True,
                message=f"Server {name} is already running",
                server=name,
                new_status=MCPServerStatus.RUNNING,
            )

        # 检查端口是否被占用（可能是卡死的进程）
        if _is_port_in_use(port):
            logger.warning(f"Port {port} is in use but health check failed, cleaning up zombie process")
            _stop_server_process(name)
            for _ in range(10):
                await asyncio.sleep(0.5)
                if not _is_port_in_use(port):
                    break
            else:
                return MCPServerActionResult(
                    success=False,
                    message=f"Failed to clean up zombie process on port {port}",
                    server=name,
                    new_status=MCPServerStatus.ERROR,
                )

        # 启动服务器
        success = _start_server_process(name, config)
        if not success:
            return MCPServerActionResult(
                success=False,
                message=f"Failed to start server {name}",
                server=name,
                new_status=MCPServerStatus.ERROR,
            )

        # 使用指数退避等待服务器启动
        health = await _wait_for_server_ready(
            name, config["host"], port, max_wait_seconds=15
        )

        if health:
            return MCPServerActionResult(
                success=True,
                message=f"Server {name} started successfully",
                server=name,
                new_status=MCPServerStatus.RUNNING,
            )

        return MCPServerActionResult(
            success=False,
            message=f"Server {name} started but health check failed (timeout after 15s)",
            server=name,
            new_status=MCPServerStatus.ERROR,
        )

    # 并发启动所有服务器
    tasks = [start_if_stopped(name, config) for name, config in MCP_SERVERS.items()]
    results = await asyncio.gather(*tasks)

    return ApiResponse(data=list(results))


@router.get("/tools", response_model=ApiResponse[List[MCPToolInfo]])
async def list_all_tools():
    """
    获取所有 MCP 服务器的工具列表
    """
    all_tools = []

    for name, config in MCP_SERVERS.items():
        tools = await _get_server_tools(name, config["host"], config["port"])
        all_tools.extend(tools)

    return ApiResponse(data=all_tools)


@router.get("/servers/{name}/tools", response_model=ApiResponse[List[MCPToolInfo]])
async def get_server_tools(name: str):
    """
    获取指定 MCP 服务器的工具列表
    """
    if name not in MCP_SERVERS:
        raise HTTPException(status_code=404, detail=f"Server not found: {name}")

    config = MCP_SERVERS[name]
    tools = await _get_server_tools(name, config["host"], config["port"])

    return ApiResponse(data=tools)


@router.get("/resources", response_model=ApiResponse[List[MCPResourceInfo]])
async def list_all_resources():
    """
    获取所有 MCP 服务器的资源列表
    """
    all_resources = []

    for name, config in MCP_SERVERS.items():
        resources = await _get_server_resources(name, config["host"], config["port"])
        all_resources.extend(resources)

    return ApiResponse(data=all_resources)


@router.get("/servers/{name}/resources", response_model=ApiResponse[List[MCPResourceInfo]])
async def get_server_resources(name: str):
    """
    获取指定 MCP 服务器的资源列表
    """
    if name not in MCP_SERVERS:
        raise HTTPException(status_code=404, detail=f"Server not found: {name}")

    config = MCP_SERVERS[name]
    resources = await _get_server_resources(name, config["host"], config["port"])

    return ApiResponse(data=resources)


@router.post("/tools/call", response_model=ApiResponse[MCPToolCallResult])
async def call_tool(request: MCPToolCallRequest):
    """
    调用 MCP 工具
    """
    if request.server not in MCP_SERVERS:
        raise HTTPException(status_code=404, detail=f"Server not found: {request.server}")

    config = MCP_SERVERS[request.server]
    result = await _call_server_tool(
        request.server,
        config["host"],
        config["port"],
        request.tool,
        request.arguments,
    )

    return ApiResponse(data=result)


@router.get("/dashboard", response_model=ApiResponse[MCPDashboardStats])
async def get_dashboard_stats():
    """
    获取 MCP 仪表盘统计信息

    优化：先并发检查所有端口，快速确定哪些服务器可能在运行
    """
    total_tools = 0
    total_resources = 0
    running_count = 0

    async def check_and_count(name: str, config: dict, port_in_use: bool):
        nonlocal total_tools, total_resources, running_count

        port = config["port"]

        # 如果端口没在用，直接返回 stopped 状态
        if not port_in_use:
            return MCPServerInfo(
                name=name,
                display_name=config["display_name"],
                description=config["description"],
                host=config["host"],
                port=port,
                status=MCPServerStatus.STOPPED,
                last_health_check=datetime.now(),
            )

        # 端口在用，检查健康状态
        health = await _check_server_health(name, config["host"], port)

        if health:
            running_count += 1
            tools = await _get_server_tools(name, config["host"], port)
            resources = await _get_server_resources(name, config["host"], port)
            total_tools += len(tools)
            total_resources += len(resources)

            return MCPServerInfo(
                name=name,
                display_name=config["display_name"],
                description=config["description"],
                host=config["host"],
                port=port,
                status=MCPServerStatus.RUNNING,
                uptime_seconds=health.uptime_seconds,
                version=health.version,
                tools_count=len(tools),
                resources_count=len(resources),
                last_health_check=datetime.now(),
            )
        else:
            # 端口在用但健康检查失败
            return MCPServerInfo(
                name=name,
                display_name=config["display_name"],
                description=config["description"],
                host=config["host"],
                port=port,
                status=MCPServerStatus.UNRESPONSIVE,
                last_health_check=datetime.now(),
                error_message="进程存在但不响应请求，可能已卡死",
            )

    # 第一步：并发检查所有端口状态（快速，<100ms）
    port_checks = await asyncio.gather(*[
        _is_port_in_use_async(config["port"]) for config in MCP_SERVERS.values()
    ])
    port_status = dict(zip(MCP_SERVERS.keys(), port_checks))

    # 第二步：并发获取每个服务器的详细信息
    tasks = [
        check_and_count(name, config, port_status[name])
        for name, config in MCP_SERVERS.items()
    ]
    servers = await asyncio.gather(*tasks)

    return ApiResponse(
        data=MCPDashboardStats(
            total_servers=len(MCP_SERVERS),
            running_servers=running_count,
            total_tools=total_tools,
            total_resources=total_resources,
            servers=list(servers),
        )
    )
