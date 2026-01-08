"""
MCP Tool 基类

从 mcp_core 导入基类，并提供经验知识库专用的扩展。
"""

from domains.mcp_core import (
    DomainBaseTool,
    ToolResult,
)


class BaseTool(DomainBaseTool):
    """
    经验知识库 MCP 工具基类

    继承 DomainBaseTool，配置 experience_service 延迟加载。
    """

    # 配置服务延迟加载
    service_path = "domains.experience_hub.services.experience:get_experience_service"
    service_attr = "experience_service"


__all__ = ['BaseTool', 'ToolResult']
