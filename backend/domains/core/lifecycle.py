"""
服务生命周期管理

提供集中式的服务注册、获取和清理，替代分散的 lru_cache 单例模式。

优势:
1. 显式的生命周期控制（startup/shutdown）
2. 清晰的依赖关系（服务注册顺序）
3. 统一的错误处理和日志
4. 支持测试时的服务替换
5. 避免循环导入（延迟导入 + 工厂函数）

使用示例:
    # 注册服务
    registry = get_service_registry()
    registry.register("factor_store", lambda: FactorStore())
    registry.register("factor_service", lambda: FactorService(registry.get("factor_store")))

    # 获取服务
    factor_service = registry.get("factor_service")

    # 应用关闭时
    await registry.shutdown()
"""

import asyncio
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ServiceDefinition:
    """服务定义"""
    name: str
    factory: Callable[[], Any]
    instance: Any | None = None
    dependencies: list[str] = field(default_factory=list)
    cleanup: Callable[[Any], None] | None = None
    async_cleanup: Callable[[Any], Any] | None = None
    initialized: bool = False


class ServiceRegistry:
    """
    服务注册表

    集中管理所有服务的生命周期，提供:
    - 延迟初始化（首次访问时创建）
    - 依赖注入（按顺序创建依赖）
    - 统一关闭（逆序清理资源）
    - 测试支持（服务替换/重置）
    """

    def __init__(self):
        self._services: dict[str, ServiceDefinition] = {}
        self._init_order: list[str] = []
        self._shutdown_callbacks: list[Callable] = []

    def register(
        self,
        name: str,
        factory: Callable[[], T],
        dependencies: list[str] | None = None,
        cleanup: Callable[[T], None] | None = None,
        async_cleanup: Callable[[T], Any] | None = None,
    ) -> "ServiceRegistry":
        """
        注册服务

        Args:
            name: 服务名称（唯一标识）
            factory: 服务工厂函数（无参数，返回服务实例）
            dependencies: 依赖的其他服务名称
            cleanup: 同步清理函数（接收服务实例）
            async_cleanup: 异步清理函数（接收服务实例）

        Returns:
            self，支持链式调用
        """
        if name in self._services:
            logger.warning(f"服务 {name} 已注册，将被覆盖")

        self._services[name] = ServiceDefinition(
            name=name,
            factory=factory,
            dependencies=dependencies or [],
            cleanup=cleanup,
            async_cleanup=async_cleanup,
        )
        return self

    def register_class(
        self,
        name: str,
        cls: type[T],
        dependencies: list[str] | None = None,
        cleanup: Callable[[T], None] | None = None,
        async_cleanup: Callable[[T], Any] | None = None,
    ) -> "ServiceRegistry":
        """
        注册类（自动创建工厂函数）

        Args:
            name: 服务名称
            cls: 服务类
            dependencies: 依赖的其他服务名称
            cleanup: 清理函数
            async_cleanup: 异步清理函数
        """
        return self.register(
            name=name,
            factory=lambda: cls(),
            dependencies=dependencies,
            cleanup=cleanup,
            async_cleanup=async_cleanup,
        )

    def get(self, name: str) -> Any:
        """
        获取服务实例

        首次访问时创建实例，后续返回缓存的实例。
        会自动先初始化依赖的服务。

        Args:
            name: 服务名称

        Returns:
            服务实例

        Raises:
            KeyError: 服务未注册
        """
        if name not in self._services:
            raise KeyError(f"服务未注册: {name}")

        definition = self._services[name]

        # 已初始化，直接返回
        if definition.initialized and definition.instance is not None:
            return definition.instance

        # 先初始化依赖
        for dep_name in definition.dependencies:
            self.get(dep_name)

        # 创建实例
        try:
            definition.instance = definition.factory()
            definition.initialized = True
            self._init_order.append(name)
            logger.debug(f"服务 {name} 已初始化")
        except Exception as e:
            logger.error(f"服务 {name} 初始化失败: {e}")
            raise

        return definition.instance

    def get_optional(self, name: str) -> Any | None:
        """获取服务实例，不存在时返回 None"""
        try:
            return self.get(name)
        except KeyError:
            return None

    def set(self, name: str, instance: Any) -> None:
        """
        直接设置服务实例（用于测试或外部注入）

        Args:
            name: 服务名称
            instance: 服务实例
        """
        if name not in self._services:
            # 未注册则创建一个简单定义
            self._services[name] = ServiceDefinition(
                name=name,
                factory=lambda: instance,
            )

        self._services[name].instance = instance
        self._services[name].initialized = True

        if name not in self._init_order:
            self._init_order.append(name)

    def reset(self, name: str) -> None:
        """
        重置单个服务（清理并标记为未初始化）

        Args:
            name: 服务名称
        """
        if name not in self._services:
            return

        definition = self._services[name]
        if definition.initialized and definition.instance is not None:
            self._cleanup_service(definition)
            definition.instance = None
            definition.initialized = False

            if name in self._init_order:
                self._init_order.remove(name)

    def reset_all(self) -> None:
        """重置所有服务（同步清理）"""
        # 逆序清理
        for name in reversed(self._init_order.copy()):
            self.reset(name)
        self._init_order.clear()

    async def shutdown(self) -> None:
        """
        关闭所有服务（异步清理）

        按初始化的逆序关闭服务，确保依赖关系正确。
        """
        logger.info("开始关闭所有服务...")

        # 执行注册的 shutdown 回调
        for callback in self._shutdown_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.warning(f"Shutdown callback 执行失败: {e}")

        # 逆序关闭服务
        for name in reversed(self._init_order.copy()):
            definition = self._services.get(name)
            if definition and definition.initialized:
                await self._cleanup_service_async(definition)
                definition.instance = None
                definition.initialized = False
                logger.debug(f"服务 {name} 已关闭")

        self._init_order.clear()
        logger.info("所有服务已关闭")

    def on_shutdown(self, callback: Callable) -> None:
        """注册 shutdown 回调"""
        self._shutdown_callbacks.append(callback)

    def _cleanup_service(self, definition: ServiceDefinition) -> None:
        """同步清理服务"""
        if definition.instance is None:
            return

        # 优先使用自定义清理函数
        if definition.cleanup:
            try:
                definition.cleanup(definition.instance)
            except Exception as e:
                logger.warning(f"服务 {definition.name} 清理失败: {e}")
            return

        # 默认关闭逻辑
        if hasattr(definition.instance, "close"):
            try:
                definition.instance.close()
            except Exception as e:
                logger.warning(f"服务 {definition.name} close() 失败: {e}")

    async def _cleanup_service_async(self, definition: ServiceDefinition) -> None:
        """异步清理服务"""
        if definition.instance is None:
            return

        # 优先使用异步清理函数
        if definition.async_cleanup:
            try:
                result = definition.async_cleanup(definition.instance)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.warning(f"服务 {definition.name} 异步清理失败: {e}")
            return

        # 使用同步清理
        self._cleanup_service(definition)

    @property
    def registered_services(self) -> list[str]:
        """获取所有已注册的服务名称"""
        return list(self._services.keys())

    @property
    def initialized_services(self) -> list[str]:
        """获取所有已初始化的服务名称"""
        return self._init_order.copy()

    def __contains__(self, name: str) -> bool:
        return name in self._services


# ==================== 全局注册表 ====================

_registry: ServiceRegistry | None = None


def get_service_registry() -> ServiceRegistry:
    """获取全局服务注册表"""
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry


def reset_service_registry() -> None:
    """重置全局服务注册表（用于测试）"""
    global _registry
    if _registry is not None:
        _registry.reset_all()
    _registry = ServiceRegistry()


# ==================== FastAPI 集成 ====================

@asynccontextmanager
async def lifespan_manager(app):
    """
    FastAPI lifespan 管理器

    使用示例:
        from fastapi import FastAPI
        from domains.core import lifespan_manager

        app = FastAPI(lifespan=lifespan_manager)
    """
    registry = get_service_registry()

    # Startup
    logger.info("应用启动中...")
    try:
        # 预热关键服务
        _warmup_services(registry)
        logger.info("应用启动完成")
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        raise

    yield

    # Shutdown
    await registry.shutdown()


def _warmup_services(registry: ServiceRegistry) -> None:
    """预热关键服务"""
    warmup_list = [
        "factor_store",
        "factor_service",
        "data_loader",
    ]

    for name in warmup_list:
        try:
            if name in registry:
                service = registry.get(name)
                logger.debug(f"预热服务 {name}: {type(service).__name__}")
        except Exception as e:
            logger.warning(f"预热服务 {name} 失败: {e}")


# ==================== 依赖注入装饰器 ====================

def inject(service_name: str):
    """
    依赖注入装饰器

    用于 FastAPI 路由或普通函数，自动注入服务。

    使用示例:
        @router.get("/factors")
        @inject("factor_service")
        async def list_factors(factor_service: FactorService):
            return factor_service.list_factors()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if service_name not in kwargs:
                registry = get_service_registry()
                kwargs[service_name] = registry.get(service_name)
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if service_name not in kwargs:
                registry = get_service_registry()
                kwargs[service_name] = registry.get(service_name)
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


# ==================== 服务注册辅助函数 ====================

def register_core_services() -> ServiceRegistry:
    """
    注册核心服务

    在应用启动时调用，注册所有核心服务。
    使用延迟导入避免循环依赖。
    """
    registry = get_service_registry()

    # ============ Store 层 ============
    def _create_factor_store():
        from domains.factor_hub.core.store import FactorStore
        return FactorStore()

    def _create_strategy_store():
        from domains.strategy_hub.services import StrategyStore
        return StrategyStore()

    def _create_note_store():
        from domains.note_hub.core.store import get_note_store
        return get_note_store()

    registry.register(
        "factor_store",
        _create_factor_store,
        cleanup=lambda s: s.close() if hasattr(s, 'close') else None
    )

    registry.register(
        "strategy_store",
        _create_strategy_store,
        cleanup=lambda s: s.close() if hasattr(s, 'close') else None
    )

    registry.register(
        "note_store",
        _create_note_store,
        cleanup=lambda s: s.close() if hasattr(s, 'close') else None
    )

    # ============ Data 层 ============
    def _create_data_loader():
        from domains.data_hub.services import DataLoader
        return DataLoader()

    def _create_factor_calculator():
        from domains.data_hub.services import FactorCalculator
        return FactorCalculator()

    def _create_data_slicer():
        from domains.data_hub.services import DataSlicer
        loader = registry.get("data_loader")
        calculator = registry.get("factor_calculator")
        return DataSlicer(loader, calculator)

    registry.register("data_loader", _create_data_loader)
    registry.register("factor_calculator", _create_factor_calculator)
    registry.register(
        "data_slicer",
        _create_data_slicer,
        dependencies=["data_loader", "factor_calculator"]
    )

    # ============ Service 层 ============
    def _create_factor_service():
        from domains.factor_hub.services import FactorService
        store = registry.get("factor_store")
        return FactorService(store=store)

    def _create_field_filler():
        from domains.factor_hub.services import FieldFiller
        return FieldFiller()

    def _create_strategy_service():
        from domains.strategy_hub.services import get_strategy_service
        return get_strategy_service()

    def _create_backtest_runner():
        from domains.strategy_hub.services import BacktestRunner
        store = registry.get("strategy_store")
        return BacktestRunner(store)

    def _create_note_service():
        from domains.note_hub.services import NoteService
        store = registry.get("note_store")
        return NoteService(store)

    registry.register(
        "factor_service",
        _create_factor_service,
        dependencies=["factor_store"]
    )

    registry.register(
        "field_filler",
        _create_field_filler,
        dependencies=["factor_service"]
    )

    registry.register(
        "strategy_service",
        _create_strategy_service,
        dependencies=["strategy_store"]
    )

    registry.register(
        "backtest_runner",
        _create_backtest_runner,
        dependencies=["strategy_store"],
        cleanup=lambda r: r.shutdown(wait=False) if hasattr(r, 'shutdown') else None
    )

    registry.register(
        "note_service",
        _create_note_service,
        dependencies=["note_store"]
    )

    logger.info(f"已注册 {len(registry.registered_services)} 个服务")
    return registry


# ==================== 导出 ====================

__all__ = [
    "ServiceRegistry",
    "ServiceDefinition",
    "get_service_registry",
    "reset_service_registry",
    "lifespan_manager",
    "inject",
    "register_core_services",
]
