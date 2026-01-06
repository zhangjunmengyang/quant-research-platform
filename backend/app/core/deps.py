"""Dependency injection for FastAPI routes.

使用 ServiceRegistry 统一管理服务生命周期，替代分散的 lru_cache 单例。

优势:
1. 显式的生命周期控制
2. 清晰的依赖关系
3. 统一的错误处理
4. 支持测试时的服务替换
"""

import asyncio
from typing import Annotated, Callable, TypeVar, Optional

from fastapi import Depends, HTTPException, Path

from domains.core import get_service_registry, register_core_services, NotFoundError

T = TypeVar("T")


# ============================================================================
# 初始化服务注册表
# ============================================================================

def _ensure_services_registered():
    """确保服务已注册（延迟初始化）"""
    registry = get_service_registry()
    if not registry.registered_services:
        register_core_services()
    return registry


# ============================================================================
# Service getters - 使用 ServiceRegistry
# ============================================================================

def get_factor_store():
    """Get FactorStore singleton instance."""
    registry = _ensure_services_registered()
    return registry.get("factor_store")


def get_factor_service():
    """Get FactorService singleton instance."""
    registry = _ensure_services_registered()
    return registry.get("factor_service")


def get_field_filler():
    """Get FieldFiller singleton instance."""
    registry = _ensure_services_registered()
    return registry.get("field_filler")


def get_data_loader():
    """Get DataLoader singleton instance."""
    registry = _ensure_services_registered()
    return registry.get("data_loader")


def get_factor_calculator():
    """Get FactorCalculator singleton instance."""
    registry = _ensure_services_registered()
    return registry.get("factor_calculator")


def get_data_slicer():
    """Get DataSlicer singleton instance."""
    registry = _ensure_services_registered()
    return registry.get("data_slicer")


def get_strategy_store():
    """Get StrategyStore singleton instance."""
    registry = _ensure_services_registered()
    return registry.get("strategy_store")


def get_strategy_service():
    """Get StrategyService singleton instance."""
    registry = _ensure_services_registered()
    return registry.get("strategy_service")


def get_backtest_runner():
    """Get BacktestRunner singleton instance."""
    registry = _ensure_services_registered()
    return registry.get("backtest_runner")


def get_note_service():
    """Get NoteService singleton instance."""
    registry = _ensure_services_registered()
    return registry.get("note_service")


# ============================================================================
# Resource existence validators
# ============================================================================

async def _get_or_404_async(
    getter: Callable,
    resource_id,
    resource_name: str,
) -> T:
    """
    异步版本：验证资源存在并返回，不存在则抛出 404。

    使用 asyncio.to_thread 包装同步数据库调用，避免阻塞 event loop。
    """
    resource = await asyncio.to_thread(getter, resource_id)
    if not resource:
        raise HTTPException(
            status_code=404, detail=f"{resource_name}不存在: {resource_id}"
        )
    return resource


async def get_factor_or_404(
    filename: Annotated[str, Path(description="因子文件名")],
    store=Depends(get_factor_store),
):
    """
    验证因子存在并返回因子对象。

    用作路由依赖注入，自动处理 404 错误。
    """
    resource = await asyncio.to_thread(
        lambda: store.get(filename, include_excluded=True)
    )
    if not resource:
        raise HTTPException(
            status_code=404, detail=f"因子不存在: {filename}"
        )
    return resource


async def get_strategy_or_404(
    strategy_id: Annotated[str, Path(description="策略ID")],
    store=Depends(get_strategy_store),
):
    """
    验证策略存在并返回策略对象。

    用作路由依赖注入，自动处理 404 错误。
    """
    return await _get_or_404_async(store.get, strategy_id, "策略")


async def get_note_or_404(
    note_id: Annotated[int, Path(description="笔记ID")],
    service=Depends(get_note_service),
):
    """
    验证笔记存在并返回笔记对象。

    用作路由依赖注入，自动处理 404 错误。
    """
    return await _get_or_404_async(service.get_note, note_id, "笔记")


# ============================================================================
# Type hints for FastAPI Depends
# ============================================================================

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domains.factor_hub.core.store import FactorStore
    from domains.factor_hub.services import FactorService
    from domains.data_hub.services import DataLoader, FactorCalculator, DataSlicer
    from domains.strategy_hub.services import StrategyStore, BacktestRunner
    from domains.note_hub.services import NoteService
