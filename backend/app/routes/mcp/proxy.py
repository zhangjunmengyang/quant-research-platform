"""MCP proxy endpoints.

This module provides REST endpoints that proxy requests to the existing MCP servers,
allowing the React frontend to interact with MCP tools via standard HTTP.
"""

import logging
from functools import lru_cache
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.common import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class MCPRequest(BaseModel):
    """MCP tool call request."""

    method: str = "tools/call"
    params: Dict[str, Any]


class MCPResponse(BaseModel):
    """MCP response."""

    result: Any = None
    error: Any = None


@lru_cache(maxsize=1)
def _get_factor_hub_server():
    """Get cached FactorHub MCP server instance."""
    from domains.factor_hub.api.mcp.server import FactorHubMCPServer

    return FactorHubMCPServer()


@lru_cache(maxsize=1)
def _get_data_hub_server():
    """Get cached DataHub MCP server instance."""
    from domains.data_hub.api.mcp.server import DataHubMCPServer

    return DataHubMCPServer()


@lru_cache(maxsize=1)
def _get_strategy_hub_server():
    """Get cached StrategyHub MCP server instance."""
    from domains.strategy_hub.api.mcp.server import StrategyHubMCPServer

    return StrategyHubMCPServer()


async def _call_mcp_server(server, request_data: dict) -> dict:
    """Call MCP server and return response."""
    try:
        from domains.mcp_core.server.protocol import JSONRPCRequest

        # Create JSON-RPC request
        rpc_request = JSONRPCRequest(
            jsonrpc="2.0",
            id="1",
            method=request_data.get("method", "tools/call"),
            params=request_data.get("params", {}),
        )

        # Handle request
        response = await server.handle_request(rpc_request)

        return {
            "result": response.result if hasattr(response, "result") else None,
            "error": response.error if hasattr(response, "error") else None,
        }
    except Exception as e:
        logger.exception("MCP server call failed")
        return {"result": None, "error": str(e)}


@router.post("/factor-hub", response_model=ApiResponse[MCPResponse])
async def factor_hub_mcp(request: MCPRequest):
    """
    因子知识库 MCP 端点

    代理请求到 factor_hub MCP 服务器。
    """
    try:
        server = _get_factor_hub_server()
        response = await _call_mcp_server(server, request.model_dump())
        return ApiResponse(data=MCPResponse(**response))
    except Exception as e:
        logger.exception("Factor hub MCP request failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-hub", response_model=ApiResponse[MCPResponse])
async def data_hub_mcp(request: MCPRequest):
    """
    数据模块 MCP 端点

    代理请求到 data_hub MCP 服务器。
    """
    try:
        server = _get_data_hub_server()
        response = await _call_mcp_server(server, request.model_dump())
        return ApiResponse(data=MCPResponse(**response))
    except Exception as e:
        logger.exception("Data hub MCP request failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategy-hub", response_model=ApiResponse[MCPResponse])
async def strategy_hub_mcp(request: MCPRequest):
    """
    策略知识库 MCP 端点

    代理请求到 strategy_hub MCP 服务器。
    """
    try:
        server = _get_strategy_hub_server()
        response = await _call_mcp_server(server, request.model_dump())
        return ApiResponse(data=MCPResponse(**response))
    except Exception as e:
        logger.exception("Strategy hub MCP request failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools", response_model=ApiResponse[Dict[str, list]])
async def list_all_tools():
    """
    列出所有可用的 MCP 工具

    返回三个 Hub 的所有工具列表。
    """
    tools = {
        "factor_hub": [],
        "data_hub": [],
        "strategy_hub": [],
    }

    try:
        server = _get_factor_hub_server()
        tools["factor_hub"] = [
            {"name": t.name, "description": t.description}
            for t in server.tool_registry.get_all_tools()
        ]
    except Exception as e:
        logger.warning("Failed to get factor hub tools: %s", e)

    try:
        server = _get_data_hub_server()
        tools["data_hub"] = [
            {"name": t.name, "description": t.description}
            for t in server.tool_registry.get_all_tools()
        ]
    except Exception as e:
        logger.warning("Failed to get data hub tools: %s", e)

    try:
        server = _get_strategy_hub_server()
        tools["strategy_hub"] = [
            {"name": t.name, "description": t.description}
            for t in server.tool_registry.get_all_tools()
        ]
    except Exception as e:
        logger.warning("Failed to get strategy hub tools: %s", e)

    return ApiResponse(data=tools)
