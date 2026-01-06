"""
数据层异常定义

定义数据层相关的自定义异常类。
"""


class DataHubError(Exception):
    """数据层基础异常"""

    def __init__(self, message: str = "数据层错误"):
        self.message = message
        super().__init__(self.message)


class DataNotFoundError(DataHubError):
    """数据未找到异常"""

    def __init__(self, message: str = "数据未找到"):
        super().__init__(message)


class FactorNotFoundError(DataHubError):
    """因子未找到异常"""

    def __init__(self, factor_name: str):
        self.factor_name = factor_name
        super().__init__(f"因子未找到: {factor_name}")


class ConfigError(DataHubError):
    """配置错误异常"""

    def __init__(self, message: str = "配置错误"):
        super().__init__(message)


class CalculationError(DataHubError):
    """计算错误异常"""

    def __init__(self, message: str = "计算错误"):
        super().__init__(message)
