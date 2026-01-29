"""
Core - 通用应用基础设施

提供与具体协议无关的基础设施组件:
- 统一异常体系
- 服务生命周期管理
- 依赖注入

注意: MCP 协议相关的组件在 mcp_core 模块中。
"""

from .exceptions import (
    ApplicationError,
    BacktestError,
    BusinessError,
    ConfigurationError,
    ConflictError,
    DataLoadError,
    # 数据相关
    DataNotFoundError,
    ErrorCategory,
    ExternalServiceError,
    FactorCalculationError,
    FactorCodeError,
    # 因子相关
    FactorNotFoundError,
    NotFoundError,
    PermissionError,
    # 策略相关
    StrategyNotFoundError,
    ValidationError,
)
from .lifecycle import (
    ServiceDefinition,
    ServiceRegistry,
    get_service_registry,
    inject,
    lifespan_manager,
    register_core_services,
    reset_service_registry,
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
