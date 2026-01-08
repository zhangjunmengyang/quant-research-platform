"""API v1 router - aggregates all route modules."""

from fastapi import APIRouter

from app.routes.v1 import factors, data, strategies, backtest, ws, pipeline, tasks, analysis, mcp_management, notes, logs, research, experiences
from app.routes.mcp import mcp_router

api_router = APIRouter()

# Include REST API route modules
api_router.include_router(factors.router, prefix="/factors", tags=["factors"])
api_router.include_router(data.router, prefix="/data", tags=["data"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(mcp_management.router, prefix="/mcp-management", tags=["mcp-management"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(experiences.router, prefix="/experiences", tags=["experiences"])

# Include MCP proxy routes
api_router.include_router(mcp_router, prefix="/mcp", tags=["mcp"])
