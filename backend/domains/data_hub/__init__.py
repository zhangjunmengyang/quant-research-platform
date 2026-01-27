"""
数据层模块 (Data Hub)

提供数据加载、因子计算和数据切片能力。
封装回测引擎的数据处理逻辑，提供简洁的 API。

主要组件:
- DataLoader: 数据加载服务
- FactorCalculator: 因子计算服务
- DataSlicer: 数据切片服务
- MCP Server: Model Context Protocol 服务
"""

from domains.mcp_core.paths import setup_factor_paths

setup_factor_paths()

from .core.config import DataHubConfig, get_data_hub_config
from .core.models import DataConfig, KlineData, FactorResult
from domains.core.exceptions import DataHubError, DataNotFoundError, FactorNotFoundError

from .services.data_loader import DataLoader
from .services.factor_calculator import FactorCalculator
from .services.data_slicer import DataSlicer

__all__ = [
    # Config
    "DataHubConfig",
    "get_data_hub_config",
    # Models
    "DataConfig",
    "KlineData",
    "FactorResult",
    # Exceptions
    "DataHubError",
    "DataNotFoundError",
    "FactorNotFoundError",
    # Services
    "DataLoader",
    "FactorCalculator",
    "DataSlicer",
]

__version__ = "2.0.0"


def run_mcp_server(host: str = "0.0.0.0", port: int = 6790, log_level: str = "info"):
    """
    启动 DataHub MCP 服务器

    Args:
        host: 监听地址
        port: 监听端口
        log_level: 日志级别
    """
    from .api.mcp import run_server
    run_server(host=host, port=port, log_level=log_level)
