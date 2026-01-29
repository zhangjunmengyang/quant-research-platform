"""
数据库抽象层

提供 PostgreSQL 数据库连接、会话管理和查询构建。
"""

from .connection import (
    DatabaseConfig,
    create_engine_from_config,
    get_async_engine,
    get_database_config,
    get_sync_engine,
)
from .query_builder import (
    QueryBuilder,
    create_query_builder,
)
from .session import (
    AsyncSessionDep,
    SessionDep,
    get_async_session,
    get_session,
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
