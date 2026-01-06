"""
MCP Tool 基类

从 mcp_core 导入基类，并提供笔记知识库专用的扩展。
"""

from domains.mcp_core import (
    DomainBaseTool,
    ToolResult,
)


class BaseTool(DomainBaseTool):
    """
    笔记知识库 MCP 工具基类

    继承 DomainBaseTool，配置 note_service 延迟加载。
    """

    # 配置服务延迟加载
    service_path = "domains.note_hub.services.note_service:get_note_service"
    service_attr = "note_service"


__all__ = ['BaseTool', 'ToolResult']
