"""Stock Hub MCP Tool 基类。"""

from domains.mcp_core import DomainBaseTool, ToolResult


class BaseTool(DomainBaseTool):
    """Stock Hub MCP 工具基类。"""

    service_path = "domains.stock_hub.services.stock_factor_service:get_stock_factor_service"
    service_attr = "factor_service"


__all__ = ["BaseTool", "ToolResult"]
