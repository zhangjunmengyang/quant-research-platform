"""
统一异常体系

提供业务层和基础设施层的统一错误处理，包括:
- 业务异常基类 (ApplicationError)
- 常用业务异常类型
- HTTP 状态码映射
- 与 MCP 错误的转换
"""

from enum import Enum
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field


class ErrorCategory(str, Enum):
    """错误分类"""
    VALIDATION = "validation"      # 参数验证错误
    NOT_FOUND = "not_found"        # 资源不存在
    CONFLICT = "conflict"          # 资源冲突
    PERMISSION = "permission"      # 权限不足
    BUSINESS = "business"          # 业务逻辑错误
    EXTERNAL = "external"          # 外部服务错误
    INTERNAL = "internal"          # 内部错误


@dataclass
class ApplicationError(Exception):
    """
    应用层异常基类

    所有业务相关的异常都应继承此类。
    提供统一的错误结构，支持 HTTP 和 MCP 协议转换。

    使用示例:
        raise NotFoundError("因子", "RSI.py")
        raise ValidationError("参数无效", errors=[{"field": "name", "message": "不能为空"}])
        raise BusinessError("IC_CALCULATION_FAILED", "IC 计算失败: 数据不足")
    """
    code: str                                    # 错误码 (如 "NOT_FOUND", "VALIDATION_ERROR")
    message: str                                 # 用户可读的错误信息
    category: ErrorCategory = ErrorCategory.INTERNAL
    details: Optional[Dict[str, Any]] = None    # 附加详情
    cause: Optional[Exception] = None           # 原始异常

    def __post_init__(self):
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    @property
    def http_status_code(self) -> int:
        """映射到 HTTP 状态码"""
        mapping = {
            ErrorCategory.VALIDATION: 400,
            ErrorCategory.NOT_FOUND: 404,
            ErrorCategory.CONFLICT: 409,
            ErrorCategory.PERMISSION: 403,
            ErrorCategory.BUSINESS: 422,
            ErrorCategory.EXTERNAL: 502,
            ErrorCategory.INTERNAL: 500,
        }
        return mapping.get(self.category, 500)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于 API 响应）"""
        result = {
            "code": self.code,
            "message": self.message,
            "category": self.category.value,
        }
        if self.details:
            result["details"] = self.details
        return result

    def to_mcp_error(self) -> "MCPError":
        """转换为 MCP 错误格式"""
        from .middleware.error_handler import MCPError, ErrorCode

        # 映射到 MCP 错误码
        code_mapping = {
            ErrorCategory.VALIDATION: ErrorCode.VALIDATION_ERROR,
            ErrorCategory.NOT_FOUND: ErrorCode.RESOURCE_NOT_FOUND,
            ErrorCategory.PERMISSION: ErrorCode.AUTHENTICATION_ERROR,
            ErrorCategory.BUSINESS: ErrorCode.TOOL_EXECUTION_ERROR,
            ErrorCategory.EXTERNAL: ErrorCode.SERVICE_UNAVAILABLE,
            ErrorCategory.INTERNAL: ErrorCode.INTERNAL_ERROR,
        }
        mcp_code = code_mapping.get(self.category, ErrorCode.INTERNAL_ERROR)

        return MCPError(
            code=mcp_code,
            message=self.message,
            data=self.details,
            cause=self.cause
        )


# ==================== 常用业务异常 ====================

class NotFoundError(ApplicationError):
    """资源不存在"""
    def __init__(
        self,
        resource_type: str,
        resource_id: Any,
        details: Optional[Dict] = None
    ):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource_type}不存在: {resource_id}",
            category=ErrorCategory.NOT_FOUND,
            details=details or {"resource_type": resource_type, "resource_id": str(resource_id)}
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class ValidationError(ApplicationError):
    """参数验证错误"""
    def __init__(
        self,
        message: str,
        errors: Optional[List[Dict[str, Any]]] = None,
        field: Optional[str] = None
    ):
        details = {}
        if errors:
            details["validation_errors"] = errors
        if field:
            details["field"] = field

        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            category=ErrorCategory.VALIDATION,
            details=details or None
        )
        self.errors = errors
        self.field = field


class ConflictError(ApplicationError):
    """资源冲突（如重复创建）"""
    def __init__(
        self,
        resource_type: str,
        conflict_field: str,
        conflict_value: Any,
        message: Optional[str] = None
    ):
        super().__init__(
            code="CONFLICT",
            message=message or f"{resource_type}已存在: {conflict_field}={conflict_value}",
            category=ErrorCategory.CONFLICT,
            details={
                "resource_type": resource_type,
                "conflict_field": conflict_field,
                "conflict_value": str(conflict_value)
            }
        )


class PermissionError(ApplicationError):
    """权限不足"""
    def __init__(
        self,
        action: str,
        resource: Optional[str] = None,
        message: Optional[str] = None
    ):
        super().__init__(
            code="PERMISSION_DENIED",
            message=message or f"无权执行操作: {action}" + (f" on {resource}" if resource else ""),
            category=ErrorCategory.PERMISSION,
            details={"action": action, "resource": resource} if resource else {"action": action}
        )


class BusinessError(ApplicationError):
    """业务逻辑错误"""
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.BUSINESS,
            details=details,
            cause=cause
        )


class ExternalServiceError(ApplicationError):
    """外部服务错误"""
    def __init__(
        self,
        service_name: str,
        message: str,
        details: Optional[Dict] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            code="EXTERNAL_SERVICE_ERROR",
            message=f"{service_name}: {message}",
            category=ErrorCategory.EXTERNAL,
            details=details or {"service": service_name},
            cause=cause
        )


class ConfigurationError(ApplicationError):
    """配置错误"""
    def __init__(
        self,
        config_key: str,
        message: str,
        details: Optional[Dict] = None
    ):
        super().__init__(
            code="CONFIGURATION_ERROR",
            message=f"配置错误 [{config_key}]: {message}",
            category=ErrorCategory.INTERNAL,
            details=details or {"config_key": config_key}
        )


# ==================== 因子相关异常 ====================

class FactorNotFoundError(NotFoundError):
    """因子不存在"""
    def __init__(self, filename: str):
        super().__init__("因子", filename)
        self.filename = filename


class FactorExistsError(ConflictError):
    """因子已存在"""
    def __init__(self, filename: str):
        super().__init__("因子", "filename", filename)
        self.filename = filename


class FactorCodeError(BusinessError):
    """因子代码错误"""
    def __init__(self, filename: str, message: str, cause: Optional[Exception] = None):
        super().__init__(
            code="FACTOR_CODE_ERROR",
            message=f"因子 {filename} 代码错误: {message}",
            details={"filename": filename},
            cause=cause
        )


class FactorCalculationError(BusinessError):
    """因子计算错误"""
    def __init__(self, factor_name: str, message: str, cause: Optional[Exception] = None):
        super().__init__(
            code="FACTOR_CALCULATION_ERROR",
            message=f"因子 {factor_name} 计算失败: {message}",
            details={"factor_name": factor_name},
            cause=cause
        )


# ==================== 策略相关异常 ====================

class StrategyNotFoundError(NotFoundError):
    """策略不存在"""
    def __init__(self, strategy_id: str):
        super().__init__("策略", strategy_id)


class BacktestError(BusinessError):
    """回测错误"""
    def __init__(self, strategy_id: str, message: str, cause: Optional[Exception] = None):
        super().__init__(
            code="BACKTEST_ERROR",
            message=f"策略 {strategy_id} 回测失败: {message}",
            details={"strategy_id": strategy_id},
            cause=cause
        )


# ==================== 数据相关异常 ====================

class DataNotFoundError(NotFoundError):
    """数据不存在"""
    def __init__(self, data_type: str, identifier: str):
        super().__init__(data_type, identifier)


class DataLoadError(BusinessError):
    """数据加载错误"""
    def __init__(self, data_type: str, message: str, cause: Optional[Exception] = None):
        super().__init__(
            code="DATA_LOAD_ERROR",
            message=f"加载{data_type}失败: {message}",
            details={"data_type": data_type},
            cause=cause
        )


class CalculationError(BusinessError):
    """计算错误"""
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(
            code="CALCULATION_ERROR",
            message=message,
            cause=cause
        )


# ==================== 兼容别名 ====================

# 为保持向后兼容，提供别名
DataHubError = ApplicationError
FactorKBError = ApplicationError
ConfigError = ConfigurationError


# ==================== 导出 ====================

__all__ = [
    # 基类
    "ErrorCategory",
    "ApplicationError",
    # 通用异常
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "PermissionError",
    "BusinessError",
    "ExternalServiceError",
    "ConfigurationError",
    "CalculationError",
    # 因子异常
    "FactorNotFoundError",
    "FactorExistsError",
    "FactorCodeError",
    "FactorCalculationError",
    # 策略异常
    "StrategyNotFoundError",
    "BacktestError",
    # 数据异常
    "DataNotFoundError",
    "DataLoadError",
    # 兼容别名
    "DataHubError",
    "FactorKBError",
    "ConfigError",
]
