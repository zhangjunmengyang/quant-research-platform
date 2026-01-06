"""
数据库抽象层

提供 PostgreSQL 数据库连接、会话管理和查询构建。
"""

from .connection import (
    DatabaseConfig,
    get_database_config,
    create_engine_from_config,
    get_async_engine,
    get_sync_engine,
)
from .session import (
    get_session,
    get_async_session,
    SessionDep,
    AsyncSessionDep,
)
from .query_builder import (
    QueryBuilder,
    create_query_builder,
)

__all__ = [
    "DatabaseConfig",
    "get_database_config",
    "create_engine_from_config",
    "get_async_engine",
    "get_sync_engine",
    "get_session",
    "get_async_session",
    "SessionDep",
    "AsyncSessionDep",
    "QueryBuilder",
    "create_query_builder",
]
