"""
MCP 配置管理

提供配置加载、环境变量支持和 YAML 配置文件支持。
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# ============================================
# 项目路径管理
# ============================================

def get_project_root() -> Path:
    """
    获取项目根目录

    通过查找 .git 目录来确定项目根目录（比 pyproject.toml 更可靠，因为子目录也可能有 pyproject.toml）。
    """
    # 从当前文件向上查找
    current = Path(__file__).resolve()

    # 向上最多查找 10 层，优先找 .git
    for _ in range(10):
        current = current.parent
        if (current / ".git").exists():
            return current

    # 回退：从当前文件向上 5 层
    # backend/domains/mcp_core/config.py -> backend -> QuantResearchMCP
    return Path(__file__).resolve().parent.parent.parent.parent.parent


def get_data_dir() -> Path:
    """
    获取数据目录（项目根目录/data）

    自动创建目录（如果不存在）。
    """
    data_dir = get_project_root() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@dataclass
class MCPConfig:
    """
    MCP 服务配置

    支持从环境变量和 YAML 文件加载配置。
    """

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 6789

    # 认证配置
    auth_enabled: bool = False
    api_key: Optional[str] = None

    # 日志配置
    log_level: str = "INFO"

    # 服务信息
    server_name: str = "mcp-server"
    server_version: str = "1.0.0"

    # 能力配置
    enable_tools: bool = True
    enable_resources: bool = True
    enable_prompts: bool = False

    # 工具分类
    enabled_tool_categories: List[str] = field(
        default_factory=lambda: ["query", "mutation"]
    )

    # 缓存配置
    resource_cache_ttl: int = 0  # 0 表示不缓存

    @classmethod
    def from_env(cls, prefix: str = "MCP") -> 'MCPConfig':
        """
        从环境变量加载配置

        Args:
            prefix: 环境变量前缀

        Returns:
            MCPConfig 实例
        """
        def get_env(key: str, default: Any = None) -> Any:
            return os.environ.get(f"{prefix}_{key}", default)

        def get_bool(key: str, default: bool = False) -> bool:
            value = get_env(key)
            if value is None:
                return default
            return value.lower() in ("true", "1", "yes")

        def get_int(key: str, default: int) -> int:
            value = get_env(key)
            if value is None:
                return default
            try:
                return int(value)
            except ValueError:
                return default

        def get_list(key: str, default: List[str]) -> List[str]:
            value = get_env(key)
            if value is None:
                return default
            return [s.strip() for s in value.split(",") if s.strip()]

        return cls(
            host=get_env("HOST", "0.0.0.0"),
            port=get_int("PORT", 6789),
            auth_enabled=get_bool("AUTH_ENABLED", False),
            api_key=get_env("API_KEY"),
            log_level=get_env("LOG_LEVEL", "INFO"),
            server_name=get_env("SERVER_NAME", "mcp-server"),
            server_version=get_env("SERVER_VERSION", "1.0.0"),
            enable_tools=get_bool("ENABLE_TOOLS", True),
            enable_resources=get_bool("ENABLE_RESOURCES", True),
            enable_prompts=get_bool("ENABLE_PROMPTS", False),
            enabled_tool_categories=get_list("TOOL_CATEGORIES", ["query", "mutation"]),
            resource_cache_ttl=get_int("RESOURCE_CACHE_TTL", 0),
        )

    @classmethod
    def from_yaml(cls, path: str) -> 'MCPConfig':
        """
        从 YAML 文件加载配置

        Args:
            path: YAML 文件路径

        Returns:
            MCPConfig 实例
        """
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML 未安装，无法加载 YAML 配置")
            return cls()

        config_path = Path(path)
        if not config_path.exists():
            logger.warning(f"配置文件不存在: {path}")
            return cls()

        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}

            server = data.get("server", {})
            auth = data.get("auth", {})
            capabilities = data.get("capabilities", {})

            return cls(
                host=server.get("host", "0.0.0.0"),
                port=server.get("port", 6789),
                auth_enabled=auth.get("enabled", False),
                api_key=auth.get("api_key"),
                log_level=server.get("log_level", "INFO"),
                server_name=server.get("name", "mcp-server"),
                server_version=server.get("version", "1.0.0"),
                enable_tools=capabilities.get("tools", True),
                enable_resources=capabilities.get("resources", True),
                enable_prompts=capabilities.get("prompts", False),
                enabled_tool_categories=capabilities.get("tool_categories", ["query", "mutation"]),
                resource_cache_ttl=server.get("resource_cache_ttl", 0),
            )

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return cls()

    @classmethod
    def load(cls, yaml_path: Optional[str] = None, env_prefix: str = "MCP") -> 'MCPConfig':
        """
        加载配置

        优先级: 环境变量 > YAML 文件 > 默认值

        Args:
            yaml_path: YAML 配置文件路径
            env_prefix: 环境变量前缀

        Returns:
            MCPConfig 实例
        """
        # 尝试从 YAML 加载基础配置
        if yaml_path:
            config = cls.from_yaml(yaml_path)
        else:
            config = cls()

        # 环境变量覆盖
        env_config = cls.from_env(env_prefix)

        # 只覆盖在环境变量中明确设置的值
        for key in ["host", "port", "auth_enabled", "api_key", "log_level",
                    "server_name", "server_version"]:
            env_value = os.environ.get(f"{env_prefix}_{key.upper()}")
            if env_value is not None:
                setattr(config, key, getattr(env_config, key))

        return config

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "host": self.host,
            "port": self.port,
            "auth_enabled": self.auth_enabled,
            "log_level": self.log_level,
            "server_name": self.server_name,
            "server_version": self.server_version,
            "enable_tools": self.enable_tools,
            "enable_resources": self.enable_resources,
            "enable_prompts": self.enable_prompts,
            "enabled_tool_categories": self.enabled_tool_categories,
            "resource_cache_ttl": self.resource_cache_ttl,
        }

    def copy(self, **updates) -> 'MCPConfig':
        """创建配置副本，可覆盖部分值"""
        data = self.to_dict()
        data.update(updates)
        return MCPConfig(**data)


# 默认配置实例管理
_configs: Dict[str, MCPConfig] = {}


def get_config(namespace: str = "default") -> MCPConfig:
    """
    获取配置实例

    Args:
        namespace: 配置命名空间

    Returns:
        MCPConfig 实例
    """
    if namespace not in _configs:
        _configs[namespace] = MCPConfig.from_env()
    return _configs[namespace]


def set_config(config: MCPConfig, namespace: str = "default") -> None:
    """
    设置配置实例

    Args:
        config: MCPConfig 实例
        namespace: 配置命名空间
    """
    _configs[namespace] = config


def reset_config(namespace: Optional[str] = None) -> None:
    """
    重置配置

    Args:
        namespace: 配置命名空间，None 表示重置所有
    """
    if namespace:
        _configs.pop(namespace, None)
    else:
        _configs.clear()
