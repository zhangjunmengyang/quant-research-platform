"""
数据库会话管理

提供同步和异步会话的创建和管理。
"""

from typing import Generator, AsyncGenerator, Annotated
from contextlib import contextmanager, asynccontextmanager

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from fastapi import Depends

from .connection import get_sync_engine, get_async_engine


def get_session_factory() -> sessionmaker:
    """获取同步会话工厂"""
    return sessionmaker(
        bind=get_sync_engine(),
        autocommit=False,
        autoflush=False,
    )


def get_async_session_factory() -> async_sessionmaker:
    """获取异步会话工厂"""
    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    获取同步数据库会话

    使用方式:
        with get_session() as session:
            session.query(...)
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话

    使用方式:
        async with get_async_session() as session:
            await session.execute(...)
    """
    factory = get_async_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# FastAPI 依赖注入
def get_db_session() -> Generator[Session, None, None]:
    """FastAPI 同步会话依赖"""
    with get_session() as session:
        yield session


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 异步会话依赖"""
    async with get_async_session() as session:
        yield session


# 类型别名
SessionDep = Annotated[Session, Depends(get_db_session)]
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_db_session)]
