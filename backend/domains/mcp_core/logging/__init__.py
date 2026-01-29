"""
结构化日志模块

基于 structlog 提供统一的日志配置，支持:
- 控制台输出
- 异步写入 PostgreSQL
"""

from .config import (
    LogConfig,
    LogFormat,
    bind_request_context,
    clear_request_context,
    configure_logging,
    get_log_store,
    get_logger,
    init_log_store,
    setup_task_logger,
    shutdown_log_store,
)
from .store import LogEntry, LogQueryResult, LogStore, LogTopic

__all__ = [
    # 配置
    "configure_logging",
    "get_logger",
    "LogConfig",
    "LogFormat",
    # 任务日志
    "setup_task_logger",
    # 上下文
    "bind_request_context",
    "clear_request_context",
    # 存储
    "LogStore",
    "LogEntry",
    "LogTopic",
    "LogQueryResult",
    "get_log_store",
    "init_log_store",
    "shutdown_log_store",
]
