"""
数据库连接管理

PostgreSQL 连接配置。
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str
    pool_size: int = 5
    max_overflow: int = 10
    pool_recycle: int = 3600
    echo: bool = False

    @classmethod
    def from_url(cls, url: str, **kwargs) -> "DatabaseConfig":
        """从 URL 创建配置"""
        if not url.startswith("postgresql"):
            raise ValueError(f"仅支持 PostgreSQL 数据库: {url}")
        return cls(url=url, **kwargs)

    @property
    def async_url(self) -> str:
        """获取异步连接 URL"""
        # postgresql://... -> postgresql+asyncpg://...
        return self.url.replace("postgresql://", "postgresql+asyncpg://", 1)


# 全局配置缓存
_config: Optional[DatabaseConfig] = None


def get_database_url() -> str:
    """获取数据库 URL"""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL 环境变量未设置。"
            "请设置 DATABASE_URL=postgresql://user:pass@host:port/dbname"
        )
    return url


def get_database_config() -> DatabaseConfig:
    """获取数据库配置"""
    global _config
    if _config is not None:
        return _config

    url = get_database_url()
    logger.info(f"使用数据库: {url.split('@')[-1] if '@' in url else url}")
    _config = DatabaseConfig.from_url(url)

    return _config


def create_engine_from_config(config: Optional[DatabaseConfig] = None) -> Engine:
    """
    根据配置创建 SQLAlchemy 引擎

    Args:
        config: 数据库配置，None 则使用默认配置

    Returns:
        SQLAlchemy Engine
    """
    if config is None:
        config = get_database_config()

    return create_engine(
        config.url,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_recycle=config.pool_recycle,
        echo=config.echo,
    )


def create_async_engine_from_config(config: Optional[DatabaseConfig] = None) -> AsyncEngine:
    """
    根据配置创建异步 SQLAlchemy 引擎

    Args:
        config: 数据库配置，None 则使用默认配置

    Returns:
        SQLAlchemy AsyncEngine
    """
    if config is None:
        config = get_database_config()

    return create_async_engine(
        config.async_url,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_recycle=config.pool_recycle,
        echo=config.echo,
    )


# 全局引擎缓存
_sync_engine: Optional[Engine] = None
_async_engine: Optional[AsyncEngine] = None


def get_sync_engine() -> Engine:
    """获取同步引擎（单例）"""
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine_from_config()
    return _sync_engine


def get_async_engine() -> AsyncEngine:
    """获取异步引擎（单例）"""
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine_from_config()
    return _async_engine


def reset_engines():
    """重置引擎（用于测试）"""
    global _sync_engine, _async_engine, _config
    if _sync_engine:
        _sync_engine.dispose()
        _sync_engine = None
    if _async_engine:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_async_engine.dispose())
            else:
                loop.run_until_complete(_async_engine.dispose())
        except RuntimeError:
            pass
        _async_engine = None
    _config = None
