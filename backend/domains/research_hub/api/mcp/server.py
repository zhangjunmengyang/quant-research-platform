"""
MCP Server - 研报知识库 MCP 服务器

基于 mcp_core 实现的 MCP 服务器。
使用 Streamable HTTP 传输协议（MCP 2025-03-26 规范推荐）。
"""

import logging
from typing import Optional

from domains.mcp_core import (
    BaseMCPServer,
    MCPConfig,
    create_mcp_app,
    create_streamable_http_app,
    run_streamable_http_server,
)
from domains.mcp_core.server.server import run_server as mcp_run_server

from .tools.report_tools import (
    ListReportsTool,
    GetReportTool,
    GetReportStatusTool,
    GetReportChunksTool,
)
from .tools.search_tools import (
    SearchReportsTool,
    AskReportsTool,
    GetSimilarChunksTool,
)

logger = logging.getLogger(__name__)


class ResearchHubMCPServer(BaseMCPServer):
    """
    研报知识库 MCP 服务器

    继承 mcp_core.BaseMCPServer，注册研报相关的工具。

    提供功能:
    - 研报管理（列表、详情、状态）
    - 语义检索
    - RAG 问答
    """

    def _setup(self) -> None:
        """设置服务器，注册工具"""
        self._register_tools()

    def _register_tools(self) -> None:
        """注册研报知识库工具"""
        # 研报管理工具（查询类）
        self.register_tool(ListReportsTool(), "query")
        self.register_tool(GetReportTool(), "query")
        self.register_tool(GetReportStatusTool(), "query")
        self.register_tool(GetReportChunksTool(), "query")

        # 检索和问答工具（查询类）
        self.register_tool(SearchReportsTool(), "query")
        self.register_tool(AskReportsTool(), "query")
        self.register_tool(GetSimilarChunksTool(), "query")

        logger.info(f"注册了 {len(self.tool_registry)} 个研报知识库工具")


def create_research_hub_config(
    host: str = "0.0.0.0",
    port: int = 6793,
    log_level: str = "INFO",
    auth_enabled: bool = False,
    api_key: Optional[str] = None,
) -> MCPConfig:
    """
    创建研报知识库 MCP 配置

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
        server_name="research-hub",
        server_version="1.0.0",
        enable_tools=True,
        enable_resources=False,
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
        config = create_research_hub_config()

    server = ResearchHubMCPServer(config)
    return create_streamable_http_app(server)


def run_server(
    host: str = "0.0.0.0",
    port: int = 6793,
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
    config = create_research_hub_config(
        host=host,
        port=port,
        log_level=log_level,
    )

    # 创建服务器并运行 (使用 Streamable HTTP)
    server = ResearchHubMCPServer(config)
    run_streamable_http_server(server, host=host, port=port, log_level=log_level, reload=reload)


if __name__ == "__main__":
    run_server()
