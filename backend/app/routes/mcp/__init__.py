"""MCP proxy routes."""

from fastapi import APIRouter
from .proxy import router as mcp_router

__all__ = ["mcp_router"]
