"""Stock Hub MCP 服务器"""
import logging

from domains.mcp_core import BaseMCPServer
from domains.mcp_core.server.server import run_streamable_http_server
from domains.stock_hub.config import MCP_SERVER_PORT
from domains.stock_hub.tools.factor_query_tool import (
    ListStockFactorsTool,
    GetStockFactorTool,
    RefreshStockFactorsTool,
)
from domains.stock_hub.tools.backtest_tool import (
    RunBacktestTool,
    GetBacktestResultTool,
)
from domains.stock_hub.tools.analysis_tool import FactorICAnalysisTool

logger = logging.getLogger(__name__)


def create_stock_hub_config(host="0.0.0.0", port=None, log_level="info"):
    """创建 Stock Hub MCP 服务器配置"""
    return {
        "name": "stock-hub",
        "version": "1.0.0",
        "description": "A股千因子选股研究 MCP 服务",
        "host": host,
        "port": port or MCP_SERVER_PORT,
        "log_level": log_level,
    }


class StockHubMCPServer(BaseMCPServer):
    """A股选股研究 MCP 服务器"""

    def _setup(self) -> None:
        """注册工具"""
        self._register_tools()

    def _register_tools(self) -> None:
        """注册 Stock Hub 工具"""
        # 因子查询工具
        self.register_tool(ListStockFactorsTool(), "query")
        self.register_tool(GetStockFactorTool(), "query")
        self.register_tool(RefreshStockFactorsTool(), "management")

        # 回测工具
        self.register_tool(RunBacktestTool(), "backtest")
        self.register_tool(GetBacktestResultTool(), "backtest")

        # 分析工具
        self.register_tool(FactorICAnalysisTool(), "analysis")

        logger.info(f"注册了 {len(self.tool_registry)} 个 Stock Hub 工具")


def run_server(
    host: str = "0.0.0.0",
    port: int = None,
    log_level: str = "info",
    reload: bool = False,
):
    """运行 Stock Hub MCP 服务器"""
    port = port or MCP_SERVER_PORT
    config = create_stock_hub_config(host=host, port=port, log_level=log_level)
    server = StockHubMCPServer(config)
    run_streamable_http_server(server, host=host, port=port, log_level=log_level, reload=reload)


if __name__ == "__main__":
    run_server()
