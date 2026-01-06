"""
MCP Tool 基类和工具注册器

从 mcp_core 导入基类，并提供因子知识库专用的扩展。
"""

# 从 mcp_core 导入基类
from domains.mcp_core import (
    DomainBaseTool,
    ToolResult,
    ToolDefinition,
    ToolRegistry,
    get_tool_registry,
    register_tool,
)


class BaseTool(DomainBaseTool):
    """
    因子知识库 MCP 工具基类

    继承 DomainBaseTool，配置 factor_service 延迟加载。
    与 REST API 统一使用 Service 层，遵循分层架构规范。
    """

    # 配置服务延迟加载
    service_path = "domains.factor_hub.services.factor_service:get_factor_service"
    service_attr = "factor_service"


# 重新导出供其他模块使用
__all__ = [
    'BaseTool',
    'ToolResult',
    'ToolDefinition',
    'ToolRegistry',
    'get_tool_registry',
    'register_tool',
]
