"""
MCP Tool 基类和工具注册器

从 mcp_core 导入基类，并提供数据模块专用的扩展。
"""

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
    数据模块 MCP 工具基类

    继承 DomainBaseTool，配置多服务延迟加载。
    """

    # 多服务配置
    service_configs = {
        "data_loader": "domains.data_hub:DataLoader",
        "factor_calculator": "domains.data_hub:FactorCalculator",
    }

    @property
    def data_slicer(self):
        """DataSlicer 需要依赖注入，特殊处理"""
        if "data_slicer" not in self._lazy_services:
            from domains.data_hub import DataSlicer
            self._lazy_services["data_slicer"] = DataSlicer(
                self.data_loader, self.factor_calculator
            )
        return self._lazy_services["data_slicer"]


# 重新导出供其他模块使用
__all__ = [
    'BaseTool',
    'ToolResult',
    'ToolDefinition',
    'ToolRegistry',
    'get_tool_registry',
    'register_tool',
]
