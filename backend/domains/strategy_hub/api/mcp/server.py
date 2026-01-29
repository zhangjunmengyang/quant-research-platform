"""
MCP Server - 策略知识库 MCP 服务器

基于 mcp_core 实现的 MCP 服务器。
使用 Streamable HTTP 传输协议（MCP 2025-03-26 规范推荐）。
"""

import logging

from domains.mcp_core import (
    BaseMCPServer,
    MCPConfig,
    create_streamable_http_app,
    run_streamable_http_server,
)

from .resources.strategy_resources import StrategyResourceProvider
from .tools.analysis_tools import (
    CompareBacktestLiveTool,
    CompareEquityCurvesTool,
    CompareStrategyCoinsTool,
)
from .tools.strategy_tools import (
    GetStrategyStatsTool,
    GetStrategyTool,
    ListStrategiesTool,
    RunBacktestTool,
    SearchStrategiesTool,
)

logger = logging.getLogger(__name__)


class StrategyHubMCPServer(BaseMCPServer):
    """
    策略知识库 MCP 服务器

    继承 mcp_core.BaseMCPServer，注册策略相关的工具和资源。
    """

    def _setup(self) -> None:
        """设置服务器，注册工具和资源"""
        self._register_tools()
        self._register_resources()

    def _register_tools(self) -> None:
        """注册策略知识库工具"""
        # 查询类工具
        self.register_tool(ListStrategiesTool(), "query")
        self.register_tool(GetStrategyTool(), "query")
        self.register_tool(SearchStrategiesTool(), "query")
        self.register_tool(GetStrategyStatsTool(), "query")

        # 回测工具
        self.register_tool(RunBacktestTool(), "mutation")

        # 分析类工具 (参数搜索/分析已移至 factor-hub)
        self.register_tool(CompareBacktestLiveTool(), "query")
        self.register_tool(CompareStrategyCoinsTool(), "query")
        self.register_tool(CompareEquityCurvesTool(), "query")

        logger.info(f"注册了 {len(self.tool_registry)} 个策略知识库工具")

    def _register_resources(self) -> None:
        """注册策略知识库资源"""
        self.set_resource_provider(StrategyResourceProvider())
        logger.info("注册了策略资源提供者")


def create_strategy_hub_config(
    host: str = "0.0.0.0",
    port: int = 6791,
    log_level: str = "INFO",
    auth_enabled: bool = False,
    api_key: str | None = None,
) -> MCPConfig:
    """
    创建策略知识库 MCP 配置

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
        server_name="strategy-hub",
        server_version="1.0.0",
        enable_tools=True,
        enable_resources=True,
        enable_prompts=False,
    )


def create_mcp_server(config: MCPConfig | None = None):
    """
    创建 MCP FastAPI 应用 (Streamable HTTP)

    Args:
        config: MCP 配置

    Returns:
        FastAPI 应用实例
    """
    if config is None:
        config = create_strategy_hub_config()

    server = StrategyHubMCPServer(config)
    return create_streamable_http_app(server)


def run_server(
    host: str = "0.0.0.0",
    port: int = 6791,
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
    config = create_strategy_hub_config(
        host=host,
        port=port,
        log_level=log_level,
    )

    # 创建服务器并运行 (使用 Streamable HTTP)
    server = StrategyHubMCPServer(config)
    run_streamable_http_server(server, host=host, port=port, log_level=log_level, reload=reload)


if __name__ == "__main__":
    run_server()
