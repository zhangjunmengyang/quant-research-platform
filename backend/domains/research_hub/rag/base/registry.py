"""
组件注册表

实现组件的注册、发现和工厂模式。
支持:
- 装饰器注册
- 配置驱动的组件创建
- 组件生命周期管理
"""

from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar
import logging

from .component import BaseComponent, ComponentConfig

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseComponent)


class ComponentRegistry(Generic[T]):
    """
    组件注册表

    用于管理同一类型的多个组件实现，支持:
    - 装饰器注册: @registry.register("name")
    - 配置创建: registry.create("name", config)
    - 实例缓存: 可选的单例模式

    示例:
        # 创建注册表
        parser_registry = ComponentRegistry[BaseParser]("parser")

        # 注册组件
        @parser_registry.register("mineru")
        class MinerUParser(BaseParser):
            ...

        # 创建组件
        parser = parser_registry.create("mineru", {"model": "MinerU2.5"})
    """

    def __init__(
        self,
        name: str,
        base_class: Optional[Type[T]] = None,
        allow_override: bool = False,
    ):
        """
        Args:
            name: 注册表名称，用于日志和错误信息
            base_class: 可选的基类检查
            allow_override: 是否允许覆盖已注册的组件
        """
        self.name = name
        self.base_class = base_class
        self.allow_override = allow_override
        self._registry: Dict[str, Type[T]] = {}
        self._instances: Dict[str, T] = {}
        self._factory_funcs: Dict[str, Callable[..., T]] = {}

    def register(
        self,
        name: str,
        *,
        aliases: Optional[List[str]] = None,
    ) -> Callable[[Type[T]], Type[T]]:
        """
        装饰器: 注册组件类

        Args:
            name: 组件名称
            aliases: 可选的别名列表

        示例:
            @parser_registry.register("mineru", aliases=["mineru2.5"])
            class MinerUParser(BaseParser):
                ...
        """

        def decorator(cls: Type[T]) -> Type[T]:
            self._do_register(name, cls)
            if aliases:
                for alias in aliases:
                    self._do_register(alias, cls)
            return cls

        return decorator

    def register_factory(
        self,
        name: str,
        factory: Callable[..., T],
    ) -> None:
        """
        注册工厂函数

        用于需要复杂初始化逻辑的组件。

        Args:
            name: 组件名称
            factory: 工厂函数，接收配置参数，返回组件实例
        """
        if name in self._registry or name in self._factory_funcs:
            if not self.allow_override:
                raise ValueError(
                    f"Component '{name}' already registered in {self.name} registry"
                )
            logger.warning(f"Overriding component '{name}' in {self.name} registry")

        self._factory_funcs[name] = factory
        logger.debug(f"Registered factory '{name}' in {self.name} registry")

    def _do_register(self, name: str, cls: Type[T]) -> None:
        """执行注册"""
        if name in self._registry:
            if not self.allow_override:
                raise ValueError(
                    f"Component '{name}' already registered in {self.name} registry"
                )
            logger.warning(f"Overriding component '{name}' in {self.name} registry")

        if self.base_class and not issubclass(cls, self.base_class):
            raise TypeError(
                f"Component '{name}' must be subclass of {self.base_class.__name__}"
            )

        self._registry[name] = cls
        logger.debug(f"Registered component '{name}' in {self.name} registry")

    def get(self, name: str) -> Type[T]:
        """
        获取组件类

        Args:
            name: 组件名称

        Returns:
            组件类

        Raises:
            KeyError: 组件不存在
        """
        if name not in self._registry:
            available = ", ".join(self.list_available())
            raise KeyError(
                f"Component '{name}' not found in {self.name} registry. "
                f"Available: [{available}]"
            )
        return self._registry[name]

    def create(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        *,
        use_cache: bool = False,
        cache_key: Optional[str] = None,
    ) -> T:
        """
        创建组件实例

        Args:
            name: 组件名称
            config: 配置参数
            use_cache: 是否使用缓存（单例模式）
            cache_key: 自定义缓存键

        Returns:
            组件实例
        """
        config = config or {}
        key = cache_key or name

        # 检查缓存
        if use_cache and key in self._instances:
            return self._instances[key]

        # 使用工厂函数或类创建
        if name in self._factory_funcs:
            instance = self._factory_funcs[name](**config)
        else:
            cls = self.get(name)
            instance = cls(**config)

        # 缓存实例
        if use_cache:
            self._instances[key] = instance

        return instance

    async def create_async(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        *,
        auto_setup: bool = True,
    ) -> T:
        """
        异步创建并初始化组件

        Args:
            name: 组件名称
            config: 配置参数
            auto_setup: 是否自动调用 setup()

        Returns:
            已初始化的组件实例
        """
        instance = self.create(name, config)
        if auto_setup:
            await instance.setup()
        return instance

    def list_available(self) -> List[str]:
        """列出所有可用的组件名称"""
        names = set(self._registry.keys())
        names.update(self._factory_funcs.keys())
        return sorted(names)

    def is_registered(self, name: str) -> bool:
        """检查组件是否已注册"""
        return name in self._registry or name in self._factory_funcs

    def clear_cache(self) -> None:
        """清除实例缓存"""
        self._instances.clear()

    def unregister(self, name: str) -> None:
        """取消注册组件"""
        self._registry.pop(name, None)
        self._factory_funcs.pop(name, None)
        self._instances.pop(name, None)

    def __contains__(self, name: str) -> bool:
        return self.is_registered(name)

    def __len__(self) -> int:
        return len(self._registry) + len(self._factory_funcs)


# 全局注册表集合
class ComponentRegistries:
    """
    全局组件注册表管理

    提供所有 RAG 组件类型的注册表访问。
    """

    def __init__(self):
        # 延迟导入避免循环依赖
        self._registries: Dict[str, ComponentRegistry] = {}

    def _ensure_registry(self, name: str) -> ComponentRegistry:
        """确保注册表存在"""
        if name not in self._registries:
            self._registries[name] = ComponentRegistry(name)
        return self._registries[name]

    @property
    def parser(self) -> ComponentRegistry:
        """解析器注册表"""
        return self._ensure_registry("parser")

    @property
    def chunker(self) -> ComponentRegistry:
        """切块器注册表"""
        return self._ensure_registry("chunker")

    @property
    def embedder(self) -> ComponentRegistry:
        """嵌入器注册表"""
        return self._ensure_registry("embedder")

    @property
    def vector_store(self) -> ComponentRegistry:
        """向量库注册表"""
        return self._ensure_registry("vector_store")

    @property
    def retriever(self) -> ComponentRegistry:
        """检索器注册表"""
        return self._ensure_registry("retriever")

    @property
    def reranker(self) -> ComponentRegistry:
        """重排器注册表"""
        return self._ensure_registry("reranker")

    @property
    def generator(self) -> ComponentRegistry:
        """生成器注册表"""
        return self._ensure_registry("generator")

    @property
    def pipeline(self) -> ComponentRegistry:
        """流水线注册表"""
        return self._ensure_registry("pipeline")

    # Agentic RAG 扩展
    @property
    def agent(self) -> ComponentRegistry:
        """Agent 注册表"""
        return self._ensure_registry("agent")

    @property
    def tool(self) -> ComponentRegistry:
        """工具注册表"""
        return self._ensure_registry("tool")

    @property
    def planner(self) -> ComponentRegistry:
        """规划器注册表"""
        return self._ensure_registry("planner")

    def get(self, name: str) -> ComponentRegistry:
        """获取指定名称的注册表"""
        return self._ensure_registry(name)

    def list_all(self) -> Dict[str, List[str]]:
        """列出所有注册表及其组件"""
        return {
            name: registry.list_available()
            for name, registry in self._registries.items()
        }


# 全局单例
component_registries = ComponentRegistries()
