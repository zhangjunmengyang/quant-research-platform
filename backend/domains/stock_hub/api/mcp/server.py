"""Stock Hub MCP 服务器。

基于 mcp_core 实现，提供因子查询和分析 MCP 工具。
"""

import logging
import os

from domains.mcp_core import (
    BaseMCPServer,
    MCPConfig,
    create_streamable_http_app,
    run_streamable_http_server,
)

from .tools.stock_tools import StockFactorDetailTool, StockFactorListTool

logger = logging.getLogger(__name__)

DEFAULT_HOST = os.environ.get("STOCK_HUB_MCP_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("STOCK_HUB_MCP_PORT", "6795"))


class StockHubMCPServer(BaseMCPServer):
    """A股千因子分析 MCP 服务器。"""

    def _setup(self) -> None:
        self._register_tools()

    def _register_tools(self) -> None:
        self.register_tool(StockFactorListTool(), "query")
        self.register_tool(StockFactorDetailTool(), "query")
        logger.info(f"注册了 {len(self.tool_registry)} 个股票分析工具")


def create_stock_hub_config(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    log_level: str = "INFO",
    auth_enabled: bool = False,
    api_key: str | None = None,
) -> MCPConfig:
    return MCPConfig(
        host=host,
        port=port,
        log_level=log_level,
        auth_enabled=auth_enabled,
        api_key=api_key,
        server_name="stock-hub",
        server_version="1.0.0",
        enable_tools=True,
        enable_resources=False,
        enable_prompts=False,
    )


def create_mcp_server(config: MCPConfig | None = None):
    if config is None:
        config = create_stock_hub_config()
    server = StockHubMCPServer(config)
    return create_streamable_http_app(server)


def run_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    log_level: str = "info",
    reload: bool = False,
):
    config = create_stock_hub_config(
        host=host,
        port=port,
        log_level=log_level,
    )
    server = StockHubMCPServer(config)
    run_streamable_http_server(
        server, host=host, port=port, log_level=log_level, reload=reload
    )


if __name__ == "__main__":
    run_server()
