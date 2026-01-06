"""
MCP Server - 因子知识库 MCP 服务器

基于 mcp_core 实现的 MCP 服务器。
"""

import logging
from typing import Optional

from domains.mcp_core import (
    BaseMCPServer,
    MCPConfig,
    create_mcp_app,
)
from domains.mcp_core.server.server import run_server as mcp_run_server

from .tools.query_tools import (
    ListFactorsTool,
    GetFactorTool,
    GetStatsTool,
    GetStylesTool,
    SearchByCodeTool,
)
from .tools.mutation_tools import (
    CreateFactorTool,
    UpdateFactorTool,
    DeleteFactorTool,
)
from .tools.analysis_tools import (
    # 单因子分析工具
    AnalyzeFactorTool,
    GetFactorICTool,
    CompareFactorsTool,
    SuggestSimilarFactorsTool,
    # 多因子分析工具
    GetFactorCorrelationTool,
    DetectCollinearityTool,
    MultiFactorAnalyzeTool,
    # 分组分析工具
    AnalyzeFactorGroupsTool,
)
from .resources.factor_resources import FactorResourceProvider

logger = logging.getLogger(__name__)


class FactorHubMCPServer(BaseMCPServer):
    """
    因子知识库 MCP 服务器

    继承 mcp_core.BaseMCPServer，注册因子相关的工具和资源。
    """

    def _setup(self) -> None:
        """设置服务器，注册工具和资源"""
        self._register_tools()
        self._register_resources()

    def _register_tools(self) -> None:
        """注册因子知识库工具"""
        # 查询类工具
        self.register_tool(ListFactorsTool(), "query")
        self.register_tool(GetFactorTool(), "query")
        self.register_tool(GetStatsTool(), "query")
        self.register_tool(GetStylesTool(), "query")
        self.register_tool(SearchByCodeTool(), "query")

        # 修改类工具（CRUD）
        self.register_tool(CreateFactorTool(), "mutation")
        self.register_tool(UpdateFactorTool(), "mutation")
        self.register_tool(DeleteFactorTool(), "mutation")

        # 单因子分析工具
        self.register_tool(AnalyzeFactorTool(), "analysis")
        self.register_tool(GetFactorICTool(), "analysis")
        self.register_tool(CompareFactorsTool(), "analysis")
        self.register_tool(SuggestSimilarFactorsTool(), "analysis")

        # 多因子分析工具
        self.register_tool(GetFactorCorrelationTool(), "analysis")
        self.register_tool(DetectCollinearityTool(), "analysis")
        self.register_tool(MultiFactorAnalyzeTool(), "analysis")

        # 分组分析工具
        self.register_tool(AnalyzeFactorGroupsTool(), "analysis")

        logger.info(f"注册了 {len(self.tool_registry)} 个因子知识库工具")

    def _register_resources(self) -> None:
        """注册因子知识库资源"""
        self.set_resource_provider(FactorResourceProvider())
        logger.info("注册了因子资源提供者")


def create_factor_hub_config(
    host: str = "0.0.0.0",
    port: int = 6789,
    log_level: str = "INFO",
    auth_enabled: bool = False,
    api_key: Optional[str] = None,
) -> MCPConfig:
    """
    创建因子知识库 MCP 配置

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
        server_name="factor-hub",
        server_version="1.0.0",
        enable_tools=True,
        enable_resources=True,
        enable_prompts=False,
    )


def create_mcp_server(config: Optional[MCPConfig] = None):
    """
    创建 MCP FastAPI 应用

    Args:
        config: MCP 配置

    Returns:
        FastAPI 应用实例
    """
    if config is None:
        config = create_factor_hub_config()

    server = FactorHubMCPServer(config)
    return create_mcp_app(server, config)


def run_server(
    host: str = "0.0.0.0",
    port: int = 6789,
    log_level: str = "info",
    reload: bool = False,
):
    """
    运行 MCP 服务器

    Args:
        host: 监听地址
        port: 监听端口
        log_level: 日志级别
        reload: 是否启用热重载
    """
    # 创建配置
    config = create_factor_hub_config(
        host=host,
        port=port,
        log_level=log_level,
    )

    # 创建服务器并运行（日志配置由 mcp_run_server 处理）
    server = FactorHubMCPServer(config)
    mcp_run_server(server, host=host, port=port, log_level=log_level, reload=reload)


if __name__ == "__main__":
    run_server()
