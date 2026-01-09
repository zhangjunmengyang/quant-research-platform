"""
MCP Tool 基类

从 mcp_core 导入基类，并提供研报知识库专用的扩展。
"""

from domains.mcp_core import (
    DomainBaseTool,
    ToolResult,
)


class BaseTool(DomainBaseTool):
    """
    研报知识库 MCP 工具基类

    继承 DomainBaseTool，配置多服务延迟加载。

    可用服务:
    - report_service: 研报管理服务
    - retrieval_service: 语义检索服务
    """

    # 多服务配置：属性名 -> "module:getter"
    service_configs = {
        "report_service": "domains.research_hub.services:get_report_service",
        "retrieval_service": "domains.research_hub.services:get_retrieval_service",
    }


__all__ = ['BaseTool', 'ToolResult']
