"""
Core - 通用应用基础设施

提供与具体协议无关的基础设施组件:
- 统一异常体系
- 服务生命周期管理
- 依赖注入

注意: MCP 协议相关的组件在 mcp_core 模块中。
"""

from .exceptions import (
    ErrorCategory,
    ApplicationError,
    NotFoundError,
    ValidationError,
    ConflictError,
    PermissionError,
    BusinessError,
    ExternalServiceError,
    ConfigurationError,
    # 因子相关
    FactorNotFoundError,
    FactorCodeError,
    FactorCalculationError,
    # 策略相关
    StrategyNotFoundError,
    BacktestError,
    # 数据相关
    DataNotFoundError,
    DataLoadError,
)

from .lifecycle import (
    ServiceRegistry,
    ServiceDefinition,
    get_service_registry,
    reset_service_registry,
    lifespan_manager,
    inject,
    register_core_services,
)

__all__ = [
    # Exceptions
    "ErrorCategory",
    "ApplicationError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "PermissionError",
    "BusinessError",
    "ExternalServiceError",
    "ConfigurationError",
    "FactorNotFoundError",
    "FactorCodeError",
    "FactorCalculationError",
    "StrategyNotFoundError",
    "BacktestError",
    "DataNotFoundError",
    "DataLoadError",
    # Lifecycle
    "ServiceRegistry",
    "ServiceDefinition",
    "get_service_registry",
    "reset_service_registry",
    "lifespan_manager",
    "inject",
    "register_core_services",
]
