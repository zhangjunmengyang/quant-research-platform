"""WebSocket endpoints for real-time updates."""

import asyncio
import logging
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.deps import get_backtest_runner

router = APIRouter()
logger = logging.getLogger(__name__)

# 最大轮询次数（防止无限循环）
MAX_POLL_COUNT = 3600  # 1小时（每秒轮询一次）


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, connection_id: str, websocket: WebSocket):
        """Accept and register a new connection."""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info(f"WebSocket connected: {connection_id}")

    def disconnect(self, connection_id: str):
        """Remove a connection."""
        self.active_connections.pop(connection_id, None)
        logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_json(self, connection_id: str, data: dict):
        """Send JSON data to a specific connection."""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_json(data)
            except Exception as e:
                logger.error(f"Error sending to {connection_id}: {e}")
                self.disconnect(connection_id)

    async def broadcast(self, data: dict):
        """Send JSON data to all connections."""
        disconnected = []
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(data)
            except Exception:
                disconnected.append(connection_id)

        for connection_id in disconnected:
            self.disconnect(connection_id)


manager = ConnectionManager()


@router.websocket("/backtest/{task_id}")
async def backtest_progress(websocket: WebSocket, task_id: str):
    """
    回测进度 WebSocket

    连接后自动推送回测任务进度更新。
    """
    await manager.connect(f"backtest_{task_id}", websocket)

    try:
        runner = get_backtest_runner()
        poll_count = 0

        while poll_count < MAX_POLL_COUNT:
            # Get current status
            status = runner.get_status(task_id)

            if status:
                status_value = (
                    status.status.value
                    if hasattr(status.status, "value")
                    else status.status
                )

                await manager.send_json(
                    f"backtest_{task_id}",
                    {
                        "task_id": task_id,
                        "status": status_value,
                        "progress": status.progress,
                        "message": status.message,
                        "started_at": str(status.started_at)
                        if status.started_at
                        else None,
                        "completed_at": str(status.completed_at)
                        if status.completed_at
                        else None,
                    },
                )

                # Stop polling if task is finished
                if status_value in ("completed", "failed", "cancelled"):
                    # Send final result
                    result = runner.get_result(task_id)
                    if result:
                        await manager.send_json(
                            f"backtest_{task_id}",
                            {
                                "task_id": task_id,
                                "status": "result",
                                "result": {
                                    "strategy_id": result.strategy_id,
                                    "metrics": result.metrics,
                                    "error": result.error,
                                },
                            },
                        )
                    break
            else:
                await manager.send_json(
                    f"backtest_{task_id}",
                    {
                        "task_id": task_id,
                        "status": "not_found",
                        "error": f"Task {task_id} not found",
                    },
                )
                break

            # Poll every second
            await asyncio.sleep(1)
            poll_count += 1

        # 超过最大轮询次数，发送超时消息并关闭
        if poll_count >= MAX_POLL_COUNT:
            await manager.send_json(
                f"backtest_{task_id}",
                {
                    "task_id": task_id,
                    "status": "timeout",
                    "error": "Task polling timeout exceeded",
                },
            )
            logger.warning(f"WebSocket polling timeout for task {task_id}")

    except WebSocketDisconnect:
        manager.disconnect(f"backtest_{task_id}")
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
        manager.disconnect(f"backtest_{task_id}")


@router.websocket("/market")
async def market_stream(websocket: WebSocket):
    """
    市场数据实时流（预留）

    未来可接入实时行情数据。
    """
    await manager.connect("market", websocket)

    try:
        while True:
            # Placeholder - send heartbeat
            await manager.send_json(
                "market",
                {
                    "type": "heartbeat",
                    "message": "Market stream not yet implemented",
                },
            )
            await asyncio.sleep(30)

    except WebSocketDisconnect:
        manager.disconnect("market")


@router.websocket("/agent/{session_id}")
async def agent_stream(websocket: WebSocket, session_id: str):
    """
    Agent 对话流式响应（预留）

    未来可接入 LLM Agent 的流式对话。
    """
    await manager.connect(f"agent_{session_id}", websocket)

    try:
        while True:
            # Wait for client messages
            data = await websocket.receive_json()

            # Echo back for now (placeholder)
            await manager.send_json(
                f"agent_{session_id}",
                {
                    "type": "message",
                    "session_id": session_id,
                    "content": f"Agent response to: {data.get('content', '')}",
                    "status": "placeholder",
                },
            )

    except WebSocketDisconnect:
        manager.disconnect(f"agent_{session_id}")
