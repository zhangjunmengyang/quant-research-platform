"""
MCP Server - 数据模块 MCP 服务器

基于 mcp_core 实现的 MCP 服务器。
使用 Streamable HTTP 传输协议（MCP 2025-03-26 规范推荐）。
"""

import logging
from typing import Optional, Dict, Any

from domains.mcp_core import (
    BaseMCPServer,
    MCPConfig,
    create_mcp_app,
    create_streamable_http_app,
    run_streamable_http_server,
)
from domains.mcp_core.server.server import run_server as mcp_run_server

from .tools.data_tools import (
    ListSymbolsTool,
    GetKlineTool,
    GetSymbolInfoTool,
)
from .tools.factor_tools import (
    ListFactorsTool,
    CalculateFactorTool,
    GetFactorRankingTool,
)
from .tools.market_tools import (
    GetMarketOverviewTool,
)
from .resources.data_resources import DataResourceProvider

logger = logging.getLogger(__name__)


class DataHubMCPServer(BaseMCPServer):
    """
    数据模块 MCP 服务器

    继承 mcp_core.BaseMCPServer，注册数据相关的工具和资源。
    """

    def _setup(self) -> None:
        """设置服务器，注册工具和资源"""
        self._register_tools()
        self._register_resources()

    def _register_tools(self) -> None:
        """注册数据模块工具"""
        # 数据查询工具
        self.register_tool(ListSymbolsTool(), "data")
        self.register_tool(GetKlineTool(), "data")
        self.register_tool(GetSymbolInfoTool(), "data")

        # 因子计算工具
        self.register_tool(ListFactorsTool(), "factor")
        self.register_tool(CalculateFactorTool(), "factor")
        self.register_tool(GetFactorRankingTool(), "factor")

        # 市场分析工具
        self.register_tool(GetMarketOverviewTool(), "market")

        logger.info(f"注册了 {len(self.tool_registry)} 个数据模块工具")

    def _register_resources(self) -> None:
        """注册数据模块资源"""
        self.set_resource_provider(DataResourceProvider())
        logger.info("注册了数据资源提供者")

    def _get_extended_health_status(self) -> Optional[Dict[str, Any]]:
        """
        添加数据缓存状态到健康检查

        Returns:
            包含缓存状态信息的字典
        """
        try:
            from domains.engine.services.data_loader import get_data_loader
            loader = get_data_loader()
            cache_status = loader.get_cache_status()
            return {
                "cache": {
                    "spot_loaded": cache_status.spot_loaded,
                    "swap_loaded": cache_status.swap_loaded,
                    "spot_symbols": cache_status.spot_symbols,
                    "swap_symbols": cache_status.swap_symbols,
                    "spot_memory_mb": round(cache_status.spot_memory_mb, 2),
                    "swap_memory_mb": round(cache_status.swap_memory_mb, 2),
                    "total_memory_mb": round(cache_status.total_memory_mb, 2),
                    "spot_age_seconds": round(cache_status.spot_age_seconds, 1) if cache_status.spot_age_seconds else None,
                    "swap_age_seconds": round(cache_status.swap_age_seconds, 1) if cache_status.swap_age_seconds else None,
                }
            }
        except Exception as e:
            logger.warning(f"获取缓存状态失败: {e}")
            return {"cache": {"error": str(e)}}


def create_data_hub_config(
    host: str = "0.0.0.0",
    port: int = 6790,
    log_level: str = "INFO",
    auth_enabled: bool = False,
    api_key: Optional[str] = None,
) -> MCPConfig:
    """
    创建数据模块 MCP 配置

    Args:
        host: 监听地址
        port: 监听端口
        log_level: 日志级别
        auth_enabled: 是否启用认证
        api_key: API Key

    Returns:
        MCPConfig 实例
    """
    return MCPConfig(
        host=host,
        port=port,
        log_level=log_level,
        auth_enabled=auth_enabled,
        api_key=api_key,
        server_name="data-hub",
        server_version="1.0.0",
        enable_tools=True,
        enable_resources=True,
        enable_prompts=False,
    )


def create_mcp_server(config: Optional[MCPConfig] = None):
    """
    创建 MCP FastAPI 应用 (Streamable HTTP)

    Args:
        config: MCP 配置

    Returns:
        FastAPI 应用实例
    """
    if config is None:
        config = create_data_hub_config()

    server = DataHubMCPServer(config)
    return create_streamable_http_app(server)


def run_server(
    host: str = "0.0.0.0",
    port: int = 6790,
    log_level: str = "info",
    reload: bool = False,
):
    """
    运行 MCP 服务器 (Streamable HTTP)

    Args:
        host: 监听地址
        port: 监听端口
        log_level: 日志级别
        reload: 是否启用热重载
    """
    # 创建配置
    config = create_data_hub_config(
        host=host,
        port=port,
        log_level=log_level,
    )

    # 创建服务器并运行 (使用 Streamable HTTP)
    server = DataHubMCPServer(config)
    run_streamable_http_server(server, host=host, port=port, log_level=log_level, reload=reload)


# 保持向后兼容的别名
MCPServer = DataHubMCPServer


if __name__ == "__main__":
    run_server()
