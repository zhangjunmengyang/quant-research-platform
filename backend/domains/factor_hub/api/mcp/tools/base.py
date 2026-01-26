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

    @staticmethod
    def normalize_filename(filename: str) -> str:
        """
        规范化因子文件名，移除可能的 .py 后缀。

        数据库中存储的 filename 不含 .py 后缀，此方法确保输入参数的一致性。
        """
        if filename.endswith(".py"):
            return filename[:-3]
        return filename


# 重新导出供其他模块使用
__all__ = [
    'BaseTool',
    'ToolResult',
    'ToolDefinition',
    'ToolRegistry',
    'get_tool_registry',
    'register_tool',
]
