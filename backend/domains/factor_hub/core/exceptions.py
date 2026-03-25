"""
自定义异常类

定义因子知识库的异常类型。
"""


class FactorKBError(Exception):
    """因子知识库基础异常"""
    pass


class FactorNotFoundError(FactorKBError):
    """因子不存在异常"""

    def __init__(self, filename: str):
        self.filename = filename
        super().__init__(f"因子不存在: {filename}")


class FactorExistsError(FactorKBError):
    """因子已存在异常"""

    def __init__(self, filename: str):
        self.filename = filename
        super().__init__(f"因子已存在: {filename}")


class ValidationError(FactorKBError):
    """数据验证异常"""

    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message)


class ConfigError(FactorKBError):
    """配置错误异常"""
    pass


class PromptError(FactorKBError):
    """Prompt 处理异常"""
    pass


class LLMError(FactorKBError):
    """LLM 调用异常"""

    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(message)
