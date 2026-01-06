"""
异步工具函数

提供在异步上下文中安全执行同步代码的工具。
"""

import asyncio
from functools import wraps
from typing import TypeVar, Callable, Any, Coroutine

T = TypeVar("T")


async def run_sync(func: Callable[..., T], *args, **kwargs) -> T:
    """
    在线程池中执行同步函数，避免阻塞 event loop。

    用于包装使用 psycopg2（同步驱动）的数据库操作。

    Args:
        func: 同步函数
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        函数执行结果

    Example:
        # 在 async 路由中安全调用同步服务方法
        result = await run_sync(service.query_factors, filter_condition={"verified": True})
    """
    return await asyncio.to_thread(func, *args, **kwargs)


def async_wrap(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    将同步函数包装为异步函数的装饰器。

    Args:
        func: 同步函数

    Returns:
        异步包装函数

    Example:
        @async_wrap
        def sync_function():
            return "result"

        # 现在可以 await 调用
        result = await sync_function()
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        return await asyncio.to_thread(func, *args, **kwargs)
    return wrapper


class AsyncServiceWrapper:
    """
    服务层异步包装器

    将同步服务的所有方法自动包装为异步版本。

    Example:
        sync_service = get_factor_service()
        async_service = AsyncServiceWrapper(sync_service)

        # 现在可以 await 调用
        result = await async_service.query_factors(...)
    """

    def __init__(self, service: Any):
        self._service = service

    def __getattr__(self, name: str) -> Callable[..., Coroutine[Any, Any, Any]]:
        attr = getattr(self._service, name)
        if callable(attr):
            async def async_method(*args, **kwargs):
                return await asyncio.to_thread(attr, *args, **kwargs)
            return async_method
        return attr
