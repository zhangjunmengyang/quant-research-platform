"""
MCP Service - 策略知识库的 Model Context Protocol 服务

提供标准化的 MCP 接口，允许 LLM 访问和操作策略知识库。
基于 mcp_core 统一基础设施实现。
"""

from .server import (
    StrategyHubMCPServer,
    create_mcp_server,
    run_server,
    create_strategy_hub_config,
)

__all__ = [
    'StrategyHubMCPServer',
    'create_mcp_server',
    'run_server',
    'create_strategy_hub_config',
]
