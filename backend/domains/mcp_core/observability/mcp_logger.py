"""
MCP 请求日志记录器

提供对外部 MCP 请求的完整日志记录功能。
"""

import logging
import threading
import time
from datetime import datetime
from typing import Any

from .models import CallStatus, MCPRequestRecord, generate_id
from .storage import LogStorage, get_log_storage

logger = logging.getLogger(__name__)


class MCPRequestLogger:
    """
    MCP 请求日志记录器

    记录外部对 MCP 服务器的所有请求，包括:
    - 请求时间、客户端信息
    - 请求方法和参数
    - 响应状态和耗时
    - 错误信息

    使用示例:
        mcp_logger = get_mcp_logger()

        # 记录请求开始
        request_id = mcp_logger.log_request(
            server_name="factor-hub",
            server_port=6789,
            method="tools/call",
            params={"name": "list_factors"},
            client_ip="127.0.0.1",
            client_name="Claude Code",
        )

        # 记录请求完成
        mcp_logger.log_response(
            request_id=request_id,
            duration_ms=150.5,
            success=True,
            response_size=1024,
            response_summary="返回 50 个因子",
        )
    """

    def __init__(self, storage: LogStorage | None = None):
        """
        初始化

        Args:
            storage: 日志存储实例
        """
        self._storage = storage
        self._pending: dict[str, MCPRequestRecord] = {}
        self._lock = threading.Lock()

    @property
    def storage(self) -> LogStorage:
        """延迟获取存储实例"""
        if self._storage is None:
            self._storage = get_log_storage()
        return self._storage

    def log_request(
        self,
        server_name: str,
        server_port: int,
        method: str,
        params: dict[str, Any] | None = None,
        jsonrpc_id: Any | None = None,
        client_ip: str = "",
        client_name: str = "",
        user_agent: str = "",
        trace_id: str = "",
        session_id: str = "",
    ) -> str:
        """
        记录请求开始

        Args:
            server_name: 服务器名称
            server_port: 服务器端口
            method: JSON-RPC 方法
            params: 请求参数
            jsonrpc_id: JSON-RPC 请求 ID
            client_ip: 客户端 IP
            client_name: 客户端名称
            user_agent: User-Agent
            trace_id: 追踪 ID
            session_id: 会话 ID

        Returns:
            请求 ID
        """
        request_id = generate_id("mcp")
        params = params or {}

        # 提取工具名、入参和资源 URI
        tool_name = ""
        tool_arguments = {}
        resource_uri = ""
        if method == "tools/call":
            tool_name = params.get("name", "")
            tool_arguments = params.get("arguments", {})
        elif method == "resources/read":
            resource_uri = params.get("uri", "")

        record = MCPRequestRecord(
            request_id=request_id,
            timestamp=datetime.now(),
            server_name=server_name,
            server_port=server_port,
            client_ip=client_ip,
            client_name=client_name,
            user_agent=user_agent,
            method=method,
            jsonrpc_id=jsonrpc_id,
            params=params,
            tool_name=tool_name,
            tool_arguments=tool_arguments,
            resource_uri=resource_uri,
            status=CallStatus.PENDING,
            trace_id=trace_id,
            session_id=session_id,
        )

        with self._lock:
            self._pending[request_id] = record

        logger.debug(
            f"MCP 请求开始: [{request_id}] {server_name}:{server_port} "
            f"{method} tool={tool_name or '-'}"
        )

        return request_id

    def log_response(
        self,
        request_id: str,
        duration_ms: float,
        success: bool,
        response_size: int = 0,
        response_summary: str = "",
        response_data: dict[str, Any] | None = None,
        error_code: int | None = None,
        error_message: str = "",
    ) -> None:
        """
        记录请求完成

        Args:
            request_id: 请求 ID
            duration_ms: 耗时 (毫秒)
            success: 是否成功
            response_size: 响应大小 (字节)
            response_summary: 响应摘要
            response_data: 结构化响应数据（用于排查）
            error_code: 错误码
            error_message: 错误信息
        """
        with self._lock:
            record = self._pending.pop(request_id, None)

        if record is None:
            logger.warning(f"未找到待处理的请求记录: {request_id}")
            return

        # 更新响应信息
        record.response_timestamp = datetime.now()
        record.duration_ms = duration_ms
        record.status = CallStatus.SUCCESS if success else CallStatus.FAILED
        record.response_size = response_size
        record.response_summary = response_summary
        record.response_data = response_data or {}
        record.error_code = error_code
        record.error_message = error_message

        # 保存到存储
        try:
            self.storage.save_mcp_request(record)
        except Exception as e:
            logger.error(f"保存 MCP 请求日志失败: {e}")

        # 日志输出
        status_str = "成功" if success else f"失败: {error_message}"
        logger.info(
            f"MCP 请求完成: [{request_id}] {record.server_name} "
            f"{record.method} - {status_str} ({duration_ms:.1f}ms)"
        )

    def log_error(
        self,
        request_id: str,
        error: Exception,
        duration_ms: float,
        error_code: int = -1,
    ) -> None:
        """
        记录请求错误

        Args:
            request_id: 请求 ID
            error: 异常对象
            duration_ms: 耗时 (毫秒)
            error_code: 错误码
        """
        self.log_response(
            request_id=request_id,
            duration_ms=duration_ms,
            success=False,
            error_code=error_code,
            error_message=str(error),
        )

    def query(
        self,
        server_name: str | None = None,
        method: str | None = None,
        tool_name: str | None = None,
        client_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: CallStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MCPRequestRecord]:
        """查询 MCP 请求记录"""
        return self.storage.query_mcp_requests(
            server_name=server_name,
            method=method,
            tool_name=tool_name,
            client_name=client_name,
            start_time=start_time,
            end_time=end_time,
            status=status,
            limit=limit,
            offset=offset,
        )

    def get(self, request_id: str) -> MCPRequestRecord | None:
        """获取单个请求记录"""
        return self.storage.get_mcp_request(request_id)


class MCPRequestContext:
    """
    MCP 请求上下文管理器

    使用示例:
        async with MCPRequestContext(
            logger=mcp_logger,
            server_name="factor-hub",
            server_port=6789,
            method="tools/call",
            params={"name": "list_factors"},
        ) as ctx:
            result = await process_request()
            ctx.set_response(
                success=True,
                response_size=len(result),
                response_summary="返回 50 个因子",
            )
    """

    def __init__(
        self,
        mcp_logger: MCPRequestLogger,
        server_name: str,
        server_port: int,
        method: str,
        params: dict[str, Any] | None = None,
        jsonrpc_id: Any | None = None,
        client_ip: str = "",
        client_name: str = "",
        user_agent: str = "",
    ):
        self.mcp_logger = mcp_logger
        self.server_name = server_name
        self.server_port = server_port
        self.method = method
        self.params = params
        self.jsonrpc_id = jsonrpc_id
        self.client_ip = client_ip
        self.client_name = client_name
        self.user_agent = user_agent

        self.request_id: str | None = None
        self.start_time: float = 0
        self._response_logged = False

        # 响应信息
        self._success = True
        self._response_size = 0
        self._response_summary = ""
        self._error_code: int | None = None
        self._error_message = ""

    def set_response(
        self,
        success: bool = True,
        response_size: int = 0,
        response_summary: str = "",
        error_code: int | None = None,
        error_message: str = "",
    ) -> None:
        """设置响应信息"""
        self._success = success
        self._response_size = response_size
        self._response_summary = response_summary
        self._error_code = error_code
        self._error_message = error_message

    async def __aenter__(self):
        self.start_time = time.perf_counter()
        self.request_id = self.mcp_logger.log_request(
            server_name=self.server_name,
            server_port=self.server_port,
            method=self.method,
            params=self.params,
            jsonrpc_id=self.jsonrpc_id,
            client_ip=self.client_ip,
            client_name=self.client_name,
            user_agent=self.user_agent,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._response_logged:
            return False

        duration_ms = (time.perf_counter() - self.start_time) * 1000

        if exc_val is not None:
            self.mcp_logger.log_error(
                request_id=self.request_id,
                error=exc_val,
                duration_ms=duration_ms,
            )
        else:
            self.mcp_logger.log_response(
                request_id=self.request_id,
                duration_ms=duration_ms,
                success=self._success,
                response_size=self._response_size,
                response_summary=self._response_summary,
                error_code=self._error_code,
                error_message=self._error_message,
            )

        self._response_logged = True
        return False

    def __enter__(self):
        self.start_time = time.perf_counter()
        self.request_id = self.mcp_logger.log_request(
            server_name=self.server_name,
            server_port=self.server_port,
            method=self.method,
            params=self.params,
            jsonrpc_id=self.jsonrpc_id,
            client_ip=self.client_ip,
            client_name=self.client_name,
            user_agent=self.user_agent,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._response_logged:
            return False

        duration_ms = (time.perf_counter() - self.start_time) * 1000

        if exc_val is not None:
            self.mcp_logger.log_error(
                request_id=self.request_id,
                error=exc_val,
                duration_ms=duration_ms,
            )
        else:
            self.mcp_logger.log_response(
                request_id=self.request_id,
                duration_ms=duration_ms,
                success=self._success,
                response_size=self._response_size,
                response_summary=self._response_summary,
                error_code=self._error_code,
                error_message=self._error_message,
            )

        self._response_logged = True
        return False


# 单例
_mcp_logger: MCPRequestLogger | None = None
_logger_lock = threading.Lock()


def get_mcp_logger() -> MCPRequestLogger:
    """获取 MCP 请求日志记录器单例"""
    global _mcp_logger
    if _mcp_logger is None:
        with _logger_lock:
            if _mcp_logger is None:
                _mcp_logger = MCPRequestLogger()
    return _mcp_logger


def configure_mcp_logger(storage: LogStorage) -> MCPRequestLogger:
    """配置 MCP 请求日志记录器"""
    global _mcp_logger
    with _logger_lock:
        _mcp_logger = MCPRequestLogger(storage=storage)
    return _mcp_logger
