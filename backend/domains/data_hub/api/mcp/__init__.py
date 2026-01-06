"""
数据模块 MCP 服务

提供数据查询、因子计算等能力的 MCP 接口。
基于 mcp_core 统一基础设施实现。
"""

from .server import (
    DataHubMCPServer,
    MCPServer,  # 向后兼容
    create_mcp_server,
    run_server,
    create_data_hub_config,
)

__all__ = [
    "DataHubMCPServer",
    "MCPServer",
    "create_mcp_server",
    "run_server",
    "create_data_hub_config",
]
