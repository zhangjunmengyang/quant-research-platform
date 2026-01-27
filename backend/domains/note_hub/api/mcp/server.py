"""
MCP Server - 笔记知识库 MCP 服务器

基于 mcp_core 实现的 MCP 服务器。
使用 Streamable HTTP 传输协议（MCP 2025-03-26 规范推荐）。

Note Hub 定位为"研究草稿/临时记录"层，MCP 工具支持：
- 基础 CRUD（create_note, update_note, get_note, list_notes, search_notes）
- 研究流程：通过 create_note 的 note_type 参数区分
  - observation: 观察 - 对数据或现象的客观记录
  - hypothesis: 假设 - 基于观察提出的待验证假说
  - verification: 检验 - 对假设的验证
- 实体关联：通过 link_note 建立与任意实体的关系（Edge 系统）
- 归档管理（archive_note, unarchive_note）
- 提炼为经验（promote_to_experience）
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

from .tools.note_tools import (
    # 基础 CRUD
    CreateNoteTool,
    UpdateNoteTool,
    SearchNotesTool,
    GetNoteTool,
    ListNotesTool,
    # 归档管理
    ArchiveNoteTool,
    UnarchiveNoteTool,
    # 提炼为经验
    PromoteToExperienceTool,
    # 知识边关联
    LinkNoteTool,
    GetNoteEdgesTool,
    TraceNoteLineageTool,
)

logger = logging.getLogger(__name__)


class NoteHubMCPServer(BaseMCPServer):
    """
    笔记知识库 MCP 服务器

    继承 mcp_core.BaseMCPServer，注册笔记相关的工具。
    """

    def _setup(self) -> None:
        """设置服务器，注册工具"""
        self._register_tools()

    def _register_tools(self) -> None:
        """注册笔记知识库工具"""
        # 基础查询工具
        self.register_tool(ListNotesTool(), "query")
        self.register_tool(GetNoteTool(), "query")
        self.register_tool(SearchNotesTool(), "query")

        # 基础创建和更新工具
        self.register_tool(CreateNoteTool(), "mutation")
        self.register_tool(UpdateNoteTool(), "mutation")

        # 归档管理工具
        self.register_tool(ArchiveNoteTool(), "mutation")
        self.register_tool(UnarchiveNoteTool(), "mutation")

        # 提炼为经验工具
        self.register_tool(PromoteToExperienceTool(), "mutation")

        # 知识边关联工具
        self.register_tool(LinkNoteTool(), "mutation")
        self.register_tool(GetNoteEdgesTool(), "query")
        self.register_tool(TraceNoteLineageTool(), "query")

        logger.info(f"注册了 {len(self.tool_registry)} 个笔记知识库工具")


def create_note_hub_config(
    host: str = "0.0.0.0",
    port: int = 6792,
    log_level: str = "INFO",
    auth_enabled: bool = False,
    api_key: Optional[str] = None,
) -> MCPConfig:
    """
    创建笔记知识库 MCP 配置

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
        server_name="note-hub",
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
        config = create_note_hub_config()

    server = NoteHubMCPServer(config)
    return create_streamable_http_app(server)


def run_server(
    host: str = "0.0.0.0",
    port: int = 6792,
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
    config = create_note_hub_config(
        host=host,
        port=port,
        log_level=log_level,
    )

    # 创建服务器并运行 (使用 Streamable HTTP)
    server = NoteHubMCPServer(config)
    run_streamable_http_server(server, host=host, port=port, log_level=log_level, reload=reload)


if __name__ == "__main__":
    run_server()
