"""
MCP 配置管理（基于 pydantic-settings）

提供:
- 类型安全的配置
- 环境变量自动绑定
- 配置校验
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    """服务器配置"""
    model_config = SettingsConfigDict(
        env_prefix="MCP_SERVER_",
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=6789, ge=1, le=65535, description="监听端口")
    name: str = Field(default="mcp-server", description="服务名称")
    version: str = Field(default="1.0.0", description="服务版本")
    workers: int = Field(default=1, ge=1, description="工作进程数")
    reload: bool = Field(default=False, description="是否启用热重载")


class LoggingSettings(BaseSettings):
    """日志配置"""
    model_config = SettingsConfigDict(
        env_prefix="MCP_LOG_",
        extra="ignore",
    )

    level: str = Field(default="INFO", description="日志级别")
    json_format: bool = Field(default=False, description="是否使用 JSON 格式")
    include_timestamp: bool = Field(default=True, description="是否包含时间戳")
    log_requests: bool = Field(default=True, description="是否记录请求日志")
    log_params: bool = Field(default=False, description="是否记录请求参数")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v):
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper


class MCPSettings(BaseSettings):
    """
    MCP 服务主配置

    统一管理所有子配置，支持从环境变量和 .env 文件加载。
    """
    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 子配置
    server: ServerSettings = Field(default_factory=ServerSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    # 环境标识
    environment: str = Field(default="development", description="运行环境")
    debug: bool = Field(default=False, description="是否调试模式")

    @property
    def is_production(self) -> bool:
        """是否生产环境"""
        return self.environment.lower() in ("production", "prod")

    @property
    def is_development(self) -> bool:
        """是否开发环境"""
        return self.environment.lower() in ("development", "dev")

    def to_legacy_config(self):
        """转换为旧版 MCPConfig（兼容性）"""
        from .config import MCPConfig
        return MCPConfig(
            host=self.server.host,
            port=self.server.port,
            log_level=self.logging.level,
            server_name=self.server.name,
            server_version=self.server.version,
        )


@lru_cache
def get_settings() -> MCPSettings:
    """
    获取配置单例

    使用 lru_cache 确保只加载一次配置。
    """
    return MCPSettings()


def get_server_settings() -> ServerSettings:
    """获取服务器配置"""
    return get_settings().server


def get_logging_settings() -> LoggingSettings:
    """获取日志配置"""
    return get_settings().logging


def reload_settings() -> MCPSettings:
    """
    重新加载配置

    清除缓存并重新加载配置。
    """
    get_settings.cache_clear()
    return get_settings()
