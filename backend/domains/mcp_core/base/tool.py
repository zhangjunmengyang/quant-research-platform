"""
MCP Tool 基类和工具注册器

提供可扩展的工具定义框架，支持:
- 类继承模式定义工具
- 装饰器模式注册工具
- 工具分类管理
- 参数验证
- 执行模式调度（Fast/Compute/Heavy）
"""

import asyncio
import functools
import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# 工具执行超时配置（秒）
DEFAULT_TOOL_TIMEOUT = 60.0  # 非回测工具默认超时
COMPUTE_TOOL_TIMEOUT = 300.0  # 回测等计算密集型工具超时


class ExecutionMode(str, Enum):
    """
    工具执行模式

    用于标注工具的执行路径:
    - FAST: 直接 async 执行，适用于 I/O 密集型、轻量查询（< 100ms）
    - COMPUTE: 适用于 CPU 密集型任务，由 BacktestRunner 等专用执行器管理
    """

    FAST = "fast"
    COMPUTE = "compute"


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.success:
            return {"success": True, "data": self.data}
        return {"success": False, "error": self.error}

    @classmethod
    def ok(cls, data: Any = None) -> 'ToolResult':
        """创建成功结果"""
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> 'ToolResult':
        """创建失败结果"""
        return cls(success=False, error=error)


@dataclass
class ToolDefinition:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: dict[str, Any]
    category: str = "default"

    def to_mcp_format(self) -> dict[str, Any]:
        """转换为 MCP 协议格式"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class BaseTool(ABC):
    """
    MCP 工具基类

    所有工具必须继承此类并实现必要的抽象方法。
    支持依赖注入、生命周期管理和执行模式调度。

    使用方式:
        class MyTool(BaseTool):
            # 执行模式：FAST（默认）、COMPUTE
            execution_mode = ExecutionMode.FAST

            @property
            def name(self) -> str:
                return "my_tool"

            @property
            def description(self) -> str:
                return "我的工具"

            @property
            def input_schema(self) -> Dict[str, Any]:
                return {
                    "type": "object",
                    "properties": {
                        "param": {"type": "string"}
                    },
                    "required": ["param"]
                }

            async def execute(self, param: str) -> ToolResult:
                return ToolResult.ok({"result": param})

    执行模式说明:
        - FAST: 直接 async 执行，适用于 I/O 密集型、轻量查询（< 100ms）
          例如：list_factors, get_factor, list_symbols
        - COMPUTE: 适用于 CPU 密集型任务，由专用执行器管理
          例如：analyze_factor, calculate_factor, run_backtest
    """

    # 工具分类，子类可覆盖
    category: str = "default"

    # 执行模式，子类可覆盖
    execution_mode: ExecutionMode = ExecutionMode.FAST

    # 执行超时时间（秒），None 使用默认值
    execution_timeout: float | None = None

    # 是否需要认证，子类可覆盖
    require_auth: bool = False

    # 所需权限范围，子类可覆盖
    required_scopes: list[str] = []

    def __init__(self, **services):
        """
        初始化工具

        Args:
            **services: 依赖注入的服务实例
        """
        self._services = services

    def get_service(self, name: str) -> Any:
        """获取注入的服务"""
        return self._services.get(name)

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识）"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（供 LLM 理解用途）"""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """
        输入参数的 JSON Schema

        Returns:
            符合 JSON Schema 规范的字典
        """
        pass

    @abstractmethod
    async def execute(self, **params) -> ToolResult:
        """
        执行工具

        Args:
            **params: 工具参数

        Returns:
            ToolResult 执行结果
        """
        pass

    def get_definition(self) -> ToolDefinition:
        """获取工具定义"""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
            category=self.category,
        )

    def coerce_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        根据 schema 类型定义转换参数类型

        MCP 客户端（如 Claude）有时会将数字以字符串形式传入，
        此方法根据 input_schema 的类型定义自动转换参数类型。

        Args:
            params: 原始输入参数

        Returns:
            类型转换后的参数字典
        """
        schema = self.input_schema
        properties = schema.get("properties", {})
        coerced = params.copy()

        for field_name, value in params.items():
            if field_name not in properties or value is None:
                continue

            prop_schema = properties[field_name]
            expected_type = prop_schema.get("type")

            try:
                if expected_type == "integer" and isinstance(value, str):
                    coerced[field_name] = int(value)
                elif expected_type == "number" and isinstance(value, str):
                    coerced[field_name] = float(value)
                elif expected_type == "boolean" and isinstance(value, str):
                    coerced[field_name] = value.lower() in ("true", "1", "yes")
            except (ValueError, TypeError):
                # 转换失败，保留原值，让后续验证报错
                pass

        return coerced

    def validate_params(self, params: dict[str, Any]) -> str | None:
        """
        验证参数

        Args:
            params: 输入参数

        Returns:
            错误信息，None 表示验证通过
        """
        schema = self.input_schema
        required = schema.get("required", [])

        for field_name in required:
            if field_name not in params:
                return f"缺少必填参数: {field_name}"

        # 基本类型验证
        properties = schema.get("properties", {})
        for field_name, value in params.items():
            if field_name in properties:
                prop_schema = properties[field_name]
                expected_type = prop_schema.get("type")

                if expected_type == "string" and not isinstance(value, str):
                    return f"参数 {field_name} 应为字符串"
                elif expected_type == "integer" and not isinstance(value, int):
                    return f"参数 {field_name} 应为整数"
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    return f"参数 {field_name} 应为数字"
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return f"参数 {field_name} 应为布尔值"
                elif expected_type == "array" and not isinstance(value, list):
                    return f"参数 {field_name} 应为数组"
                elif expected_type == "object" and not isinstance(value, dict):
                    return f"参数 {field_name} 应为对象"

        return None


class ToolRegistry:
    """
    工具注册器

    管理所有可用的 MCP 工具，支持动态注册和分类管理。
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._categories: dict[str, list[str]] = {}
        self._services: dict[str, Any] = {}

    def set_service(self, name: str, service: Any) -> None:
        """设置服务实例，用于依赖注入"""
        self._services[name] = service

    def register(self, tool: BaseTool, category: str | None = None) -> None:
        """
        注册工具实例

        Args:
            tool: 工具实例
            category: 工具分类，默认使用工具的 category 属性
        """
        name = tool.name
        category = category or tool.category

        if name in self._tools:
            logger.warning(f"工具 {name} 已存在，将被覆盖")

        self._tools[name] = tool

        if category not in self._categories:
            self._categories[category] = []
        if name not in self._categories[category]:
            self._categories[category].append(name)

        logger.debug(f"注册工具: {name} (分类: {category})")

    def register_class(
        self,
        tool_class: type[BaseTool],
        category: str | None = None,
        **kwargs
    ) -> BaseTool:
        """
        注册工具类（自动实例化）

        Args:
            tool_class: 工具类
            category: 工具分类
            **kwargs: 传递给工具构造函数的参数

        Returns:
            工具实例
        """
        # 合并服务实例
        services = {**self._services, **kwargs}
        tool = tool_class(**services)
        self.register(tool, category)
        return tool

    def unregister(self, name: str) -> bool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            是否成功注销
        """
        if name not in self._tools:
            return False

        del self._tools[name]

        for category, tools in self._categories.items():
            if name in tools:
                tools.remove(name)

        logger.debug(f"注销工具: {name}")
        return True

    def get(self, name: str) -> BaseTool | None:
        """获取工具"""
        return self._tools.get(name)

    def get_all(self) -> dict[str, BaseTool]:
        """获取所有工具"""
        return self._tools.copy()

    def get_by_category(self, category: str) -> list[BaseTool]:
        """获取指定分类的工具"""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def get_definitions(self) -> list[ToolDefinition]:
        """获取所有工具定义"""
        return [tool.get_definition() for tool in self._tools.values()]

    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """获取 MCP 格式的工具列表"""
        return [defn.to_mcp_format() for defn in self.get_definitions()]

    async def execute(self, name: str, params: dict[str, Any]) -> ToolResult:
        """
        执行工具（带超时控制、日志记录和执行模式调度）

        根据工具的 execution_mode 属性自动选择执行路径:
        - FAST: 直接 async 执行，默认 60s 超时
        - COMPUTE: 由专用执行器管理（如 BacktestRunner），默认 300s 超时

        Args:
            name: 工具名称
            params: 工具参数

        Returns:
            执行结果
        """
        tool = self.get(name)
        if tool is None:
            return ToolResult.fail(f"工具不存在: {name}")

        # 类型转换（兼容 MCP 客户端传入的字符串类型数字）
        coerced_params = tool.coerce_params(params)

        # 参数验证
        error = tool.validate_params(coerced_params)
        if error:
            return ToolResult.fail(error)

        params = coerced_params

        # 确定超时时间
        execution_mode = getattr(tool, "execution_mode", ExecutionMode.FAST)
        if tool.execution_timeout is not None:
            timeout = tool.execution_timeout
        elif execution_mode == ExecutionMode.COMPUTE:
            timeout = COMPUTE_TOOL_TIMEOUT
        else:
            timeout = DEFAULT_TOOL_TIMEOUT

        try:
            # 带超时的执行
            result = await asyncio.wait_for(
                tool.execute(**params),
                timeout=timeout
            )
            return result
        except TimeoutError:
            logger.error(f"工具 {name} 执行超时（{timeout}秒）")
            return ToolResult.fail(f"执行超时: 工具 {name} 超过 {timeout} 秒未响应")
        except Exception as e:
            logger.exception(f"工具 {name} 执行失败")
            return ToolResult.fail(f"执行失败: {str(e)}")

    @property
    def categories(self) -> list[str]:
        """获取所有分类"""
        return list(self._categories.keys())

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# 全局工具注册器实例管理
_registries: dict[str, ToolRegistry] = {}


def get_tool_registry(namespace: str = "default") -> ToolRegistry:
    """
    获取工具注册器

    Args:
        namespace: 命名空间，用于隔离不同模块的工具

    Returns:
        ToolRegistry 实例
    """
    if namespace not in _registries:
        _registries[namespace] = ToolRegistry()
    return _registries[namespace]


def register_tool(
    category: str = "default",
    namespace: str = "default",
):
    """
    工具注册装饰器

    Usage:
        @register_tool("query")
        class MyTool(BaseTool):
            ...

        @register_tool("mutation", namespace="factor_kb")
        class UpdateTool(BaseTool):
            ...
    """
    def decorator(cls: type[BaseTool]):
        # 设置类的 category 属性
        cls.category = category

        # 延迟注册，在首次获取 registry 时注册
        @functools.wraps(cls, updated=[])
        class WrappedClass(cls):
            _registered = False
            _category = category
            _namespace = namespace

            @classmethod
            def ensure_registered(cls):
                if not cls._registered:
                    registry = get_tool_registry(cls._namespace)
                    registry.register_class(cls.__bases__[0], cls._category)
                    cls._registered = True

        return WrappedClass

    return decorator


def auto_schema(func: Callable) -> dict[str, Any]:
    """
    从函数签名自动生成 JSON Schema

    Args:
        func: 函数

    Returns:
        JSON Schema 字典
    """
    sig = inspect.signature(func)
    properties = {}
    required = []

    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue

        prop = {}

        # 获取类型注解
        if param.annotation != inspect.Parameter.empty:
            py_type = param.annotation
            if py_type in type_mapping:
                prop["type"] = type_mapping[py_type]

        # 获取默认值
        if param.default == inspect.Parameter.empty:
            required.append(name)
        else:
            prop["default"] = param.default

        properties[name] = prop

    schema = {
        "type": "object",
        "properties": properties,
    }

    if required:
        schema["required"] = required

    return schema


class DomainBaseTool(BaseTool):
    """
    领域工具基类 - 提供延迟服务注入功能

    允许子类声明需要的服务，在首次访问时延迟加载。
    这样可以避免循环导入，同时保持类型安全。

    使用方式（单服务）:
        class FactorBaseTool(DomainBaseTool):
            service_path = "domains.factor_hub.services.factor_service:get_factor_service"
            service_attr = "factor_service"

            async def execute(self, **params) -> ToolResult:
                factors = self.factor_service.list_factors()
                return ToolResult.ok(factors)

    使用方式（多服务）:
        class DataBaseTool(DomainBaseTool):
            # 多服务配置：属性名 -> "module:getter" 或 "module:ClassName"
            service_configs = {
                "data_loader": "domains.data_hub:DataLoader",
                "factor_calculator": "domains.data_hub:FactorCalculator",
            }

            async def execute(self, **params) -> ToolResult:
                df = self.data_loader.load_kline("BTCUSDT")
                return ToolResult.ok(df)
    """

    # 单服务配置（向后兼容）
    service_path: str | None = None
    service_attr: str = "service"

    # 多服务配置：{属性名: "module:getter_or_class"}
    service_configs: dict[str, str] = {}

    def __init__(self, **services):
        super().__init__(**services)
        self._lazy_services: dict[str, Any] = {}
        self._service_loaded: dict[str, bool] = {}

    def _load_service(self, attr_name: str, path: str) -> Any:
        """加载单个服务"""
        if attr_name in self._lazy_services:
            return self._lazy_services[attr_name]

        parts = path.split(":")
        if len(parts) != 2:
            raise ValueError(
                f"服务路径格式错误，应为 'module:getter_or_class'，实际为 '{path}'"
            )

        module_path, target_name = parts

        try:
            import importlib
            module = importlib.import_module(module_path)
            target = getattr(module, target_name)

            # 如果是类，实例化；如果是函数，调用
            if isinstance(target, type):
                instance = target()
            else:
                instance = target()

            self._lazy_services[attr_name] = instance
            self._service_loaded[attr_name] = True
            return instance
        except ImportError as e:
            logger.error(f"无法导入服务模块 {module_path}: {e}")
            raise
        except AttributeError as e:
            logger.error(f"服务模块 {module_path} 中没有 {target_name}: {e}")
            raise

    def __getattr__(self, name: str) -> Any:
        """拦截服务属性访问，实现延迟加载"""
        # 检查多服务配置
        if name in self.service_configs:
            return self._load_service(name, self.service_configs[name])

        # 检查单服务配置
        if name == self.service_attr and self.service_path:
            return self._load_service(name, self.service_path)

        raise AttributeError(f"'{type(self).__name__}' 没有属性 '{name}'")
