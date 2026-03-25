"""Stock Hub MCP 工具基类"""
from domains.mcp_core import DomainBaseTool


class StockBaseTool(DomainBaseTool):
    """
    Stock Hub MCP 工具基类

    配置 stock_factor_service 延迟加载。
    """
    service_path = "domains.stock_hub.services.stock_factor_service:get_stock_factor_service"
    service_attr = "stock_factor_service"
