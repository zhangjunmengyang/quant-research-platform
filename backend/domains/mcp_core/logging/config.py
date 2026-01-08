"""
结构化日志配置

提供统一的日志格式和配置，支持:
- 控制台输出（开发环境）
- JSON 格式输出（生产环境）
- 异步写入 PostgreSQL（日志查询）
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

import structlog

if TYPE_CHECKING:
    from .store import LogStore, LogEntry


class LogFormat(str, Enum):
    """日志格式"""
    JSON = "json"
    CONSOLE = "console"


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"
    format: LogFormat = LogFormat.JSON
    add_timestamp: bool = True
    add_logger_name: bool = True
    service_name: str = "quant-api"
    extra_tags: dict = field(default_factory=dict)
    # PostgreSQL 日志存储
    enable_db_logging: bool = True
    db_log_topic: str = "system"  # 默认日志主题

    @classmethod
    def from_env(cls, service_name: str = "quant-api") -> "LogConfig":
        """从环境变量创建配置"""
        level = os.getenv("LOG_LEVEL", "INFO").upper()
        format_str = os.getenv("LOG_FORMAT", "json").lower()
        enable_db = os.getenv("LOG_TO_DB", "true").lower() == "true"

        return cls(
            level=level,
            format=LogFormat.JSON if format_str == "json" else LogFormat.CONSOLE,
            service_name=service_name,
            enable_db_logging=enable_db,
        )


# 全局配置引用
_current_config: Optional[LogConfig] = None
_log_store: Optional["LogStore"] = None
_event_loop: Optional[asyncio.AbstractEventLoop] = None


class PostgreSQLHandler(logging.Handler):
    """
    异步写入 PostgreSQL 的日志 Handler

    将日志异步写入数据库，不阻塞主线程
    """

    def __init__(
        self,
        service_name: str,
        default_topic: str = "system",
    ):
        super().__init__()
        self.service_name = service_name
        self.default_topic = default_topic
        self._pending_logs: list[dict] = []

    def emit(self, record: logging.LogRecord):
        """处理日志记录"""
        try:
            # 解析 structlog 格式的消息
            msg = self.format(record)
            log_data = self._parse_log_message(record, msg)

            # 尝试异步写入
            self._write_async(log_data)

        except Exception:
            self.handleError(record)

    def _parse_log_message(self, record: logging.LogRecord, formatted_msg: str) -> dict:
        """解析日志消息，提取结构化字段"""
        # 尝试解析 JSON 格式
        data = {}
        message = record.getMessage()

        try:
            parsed = json.loads(formatted_msg)
            if isinstance(parsed, dict):
                # 提取核心字段
                message = parsed.pop("event", message)
                data = {k: v for k, v in parsed.items()
                       if k not in ("timestamp", "level", "logger")}

                # 如果 message 本身是 JSON 字符串，尝试解析并合并
                if isinstance(message, str) and message.startswith("{"):
                    try:
                        inner = json.loads(message)
                        if isinstance(inner, dict):
                            # 合并内层字段到 data
                            data.update(inner)
                            # 使用内层的 event 作为 message
                            message = inner.pop("event", message)
                    except (json.JSONDecodeError, TypeError):
                        pass
        except (json.JSONDecodeError, TypeError):
            pass

        # 确定日志主题（基于 logger 名称）
        topic = data.pop("_topic", self.default_topic)
        logger_name = (record.name or "").lower()

        # MCP 相关 logger -> mcp 主题
        if "mcp_logger" in logger_name:
            topic = "mcp"
        # MCP 服务的 streamable_http 日志 -> mcp 主题
        elif "streamable_http" in logger_name:
            # 如果包含 MCP 请求相关字段，归类为 mcp
            if "tool_name" in data or "method" in data or "server_name" in data:
                topic = "mcp"
            else:
                topic = "system"
        # LLM 相关 logger -> llm 主题
        elif "llm_logger" in logger_name:
            topic = "llm"
        # storage logger 根据内容判断
        elif "observability.storage" in logger_name:
            if "tool_name" in data or "mcp_server" in data or "method" in data:
                topic = "mcp"
            elif "model" in data or "tokens" in data:
                topic = "llm"
            else:
                topic = "system"
        # 其他 -> system 主题（默认）
        else:
            topic = "system"

        return {
            "timestamp": datetime.fromtimestamp(record.created),
            "topic": topic,
            "level": record.levelname.lower(),
            "service": self.service_name,
            "logger_name": record.name or "",
            "trace_id": data.pop("trace_id", data.pop("request_id", "")),
            "message": message,
            "data": data,
        }

    def _write_async(self, log_data: dict):
        """异步写入日志"""
        global _log_store, _event_loop

        if _log_store is None:
            return

        try:
            from .store import LogEntry

            entry = LogEntry(
                timestamp=log_data["timestamp"],
                topic=log_data["topic"],
                level=log_data["level"],
                service=log_data["service"],
                logger_name=log_data["logger_name"],
                trace_id=log_data["trace_id"],
                message=log_data["message"],
                data=log_data["data"],
            )

            # 尝试在事件循环中执行
            if _event_loop and _event_loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    _log_store.write(entry),
                    _event_loop
                )
            else:
                # 如果没有运行的事件循环，缓存日志
                self._pending_logs.append(log_data)

        except Exception:
            pass  # 日志写入失败不应影响主程序


def configure_logging(config: Optional[LogConfig] = None, service_name: str = "quant-api"):
    """
    配置结构化日志

    Args:
        config: 日志配置，None 则从环境变量读取
        service_name: 服务名称
    """
    global _current_config

    if config is None:
        config = LogConfig.from_env(service_name=service_name)

    _current_config = config

    # 设置日志级别
    log_level = getattr(logging, config.level, logging.INFO)

    # 构建处理器链
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if config.add_timestamp:
        processors.insert(0, structlog.processors.TimeStamper(fmt="iso"))

    # 使用 stdlib.BoundLogger 时，不在 structlog 配置中添加最终渲染器
    # 渲染工作由标准库 logging 的 ProcessorFormatter 完成
    # 这里添加 ProcessorFormatter.wrap_for_formatter 来准备事件字典
    processors.append(structlog.stdlib.ProcessorFormatter.wrap_for_formatter)

    # 配置 structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 配置标准库日志使用 structlog 处理器
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if config.add_timestamp:
        shared_processors.insert(0, structlog.processors.TimeStamper(fmt="iso"))

    if config.format == LogFormat.JSON:
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(ensure_ascii=False),
            foreign_pre_chain=shared_processors,
        )
    else:
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(
                colors=sys.stdout.isatty(),
                exception_formatter=structlog.dev.plain_traceback,
            ),
            foreign_pre_chain=shared_processors,
        )

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(log_level)

    # PostgreSQL Handler（如果启用）
    if config.enable_db_logging:
        pg_handler = PostgreSQLHandler(
            service_name=config.service_name,
            default_topic=config.db_log_topic,
        )
        pg_handler.setLevel(log_level)
        # JSON 格式化器用于解析
        pg_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(ensure_ascii=False),
            foreign_pre_chain=shared_processors,
        ))
        root_logger.addHandler(pg_handler)

    # 设置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


async def init_log_store():
    """
    初始化日志存储（在应用启动时调用）

    需要在 FastAPI 的 lifespan 中调用
    """
    global _log_store, _event_loop

    try:
        from .store import LogStore

        _event_loop = asyncio.get_running_loop()
        _log_store = LogStore()
        await _log_store.start()
        logging.info("PostgreSQL log store initialized")
    except Exception as e:
        logging.warning(f"Failed to initialize log store: {e}")


async def shutdown_log_store():
    """
    关闭日志存储（在应用关闭时调用）
    """
    global _log_store

    if _log_store:
        await _log_store.stop()
        _log_store = None


def get_log_store() -> Optional["LogStore"]:
    """获取日志存储实例"""
    return _log_store


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    获取结构化日志器

    Args:
        name: 日志器名称

    Returns:
        structlog BoundLogger

    使用示例:
        logger = get_logger(__name__)
        logger.info("factor_analyzed", factor_id="Rsi", ic_mean=0.03)

        # 指定日志主题
        logger.info("tool_called", _topic="mcp_calls", tool_name="analyze_factor")
    """
    return structlog.get_logger(name)


# 便捷函数：添加请求上下文
def bind_request_context(request_id: str, user_id: Optional[str] = None):
    """
    绑定请求上下文到日志

    Args:
        request_id: 请求 ID
        user_id: 用户 ID（可选）
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    if user_id:
        structlog.contextvars.bind_contextvars(user_id=user_id)


def clear_request_context():
    """清除请求上下文"""
    structlog.contextvars.clear_contextvars()
