"""
graph-hub MCP 服务器

统一的知识图谱管理服务，提供关联管理、图查询和标签管理功能。
端口: 6795
"""
import logging

from domains.mcp_core import (
    BaseMCPServer,
    MCPConfig,
    run_streamable_http_server,
)

logger = logging.getLogger(__name__)


class GraphHubMCPServer(BaseMCPServer):
    """图谱管理 MCP 服务器"""

    def _setup(self) -> None:
        """注册工具"""
        self._register_tools()

    def _register_tools(self) -> None:
        """注册所有工具"""
        # 关联管理
        from .tools.link_tools import CreateLinkTool, DeleteLinkTool
        self.register_tool(CreateLinkTool(), "mutation")
        self.register_tool(DeleteLinkTool(), "mutation")

        # 查询工具
        from .tools.query_tools import (
            GetEdgesTool,
            TraceLineageTool,
            FindPathTool,
        )
        self.register_tool(GetEdgesTool(), "query")
        self.register_tool(TraceLineageTool(), "query")
        self.register_tool(FindPathTool(), "query")

        # 标签管理
        from .tools.tag_tools import (
            AddTagTool,
            RemoveTagTool,
            GetEntityTagsTool,
            GetEntitiesByTagTool,
            ListAllTagsTool,
        )
        self.register_tool(AddTagTool(), "mutation")
        self.register_tool(RemoveTagTool(), "mutation")
        self.register_tool(GetEntityTagsTool(), "query")
        self.register_tool(GetEntitiesByTagTool(), "query")
        self.register_tool(ListAllTagsTool(), "query")

        logger.info(f"graph-hub: 注册了 {len(self.tool_registry)} 个工具")


def create_graph_hub_config(
    host: str = "0.0.0.0",
    port: int = 6795,
    log_level: str = "INFO",
) -> MCPConfig:
    """创建 graph-hub 配置"""
    return MCPConfig(
        host=host,
        port=port,
        log_level=log_level,
        server_name="graph-hub",
        server_version="1.0.0",
        enable_tools=True,
        enable_resources=False,
        enable_prompts=False,
    )


def run_server(
    host: str = "0.0.0.0",
    port: int = 6795,
    log_level: str = "info",
    reload: bool = False,
):
    """运行服务器"""
    config = create_graph_hub_config(host=host, port=port, log_level=log_level)
    server = GraphHubMCPServer(config)
    run_streamable_http_server(server, host=host, port=port, log_level=log_level, reload=reload)


if __name__ == "__main__":
    run_server()
