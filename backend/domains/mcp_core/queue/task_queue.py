"""
任务队列实现

基于 Redis 的轻量级任务队列，支持:
- 异步任务提交
- 任务状态查询
- 任务结果获取
- 优先级队列
"""

import asyncio
import json
import logging
import os
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: TaskStatus
    result: Any | None = None
    error: str | None = None
    task_type: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    runtime_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "task_type": self.task_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "runtime_seconds": self.runtime_seconds,
        }


class TaskQueue:
    """
    轻量级任务队列

    使用 Redis 存储任务状态，支持:
    - 任务提交和状态追踪
    - 异步结果获取
    - 任务取消

    使用示例:
        queue = TaskQueue()
        await queue.connect()

        # 提交任务
        task_id = await queue.submit("backtest", {"strategy": "Rsi"})

        # 查询状态
        result = await queue.get_result(task_id)
    """

    def __init__(self, redis_url: str | None = None):
        """
        初始化任务队列

        Args:
            redis_url: Redis 连接 URL，默认从环境变量获取
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._redis = None
        self._handlers: dict[str, Callable[..., Awaitable]] = {}

    async def connect(self):
        """连接 Redis"""
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info(f"任务队列已连接: {self.redis_url}")
        except ImportError:
            logger.warning("redis 包未安装，任务队列将使用内存模式")
            self._redis = None
        except Exception as e:
            logger.warning(f"Redis 连接失败，使用内存模式: {e}")
            self._redis = None

    async def close(self):
        """关闭连接"""
        if self._redis:
            await self._redis.close()

    def register(self, task_type: str):
        """
        注册任务处理器

        使用装饰器:
            @queue.register("backtest")
            async def handle_backtest(params):
                ...
        """
        def decorator(func: Callable[..., Awaitable]):
            self._handlers[task_type] = func
            return func
        return decorator

    async def submit(
        self,
        task_type: str,
        params: dict[str, Any],
        priority: int = 0,
    ) -> str:
        """
        提交任务

        Args:
            task_type: 任务类型
            params: 任务参数
            priority: 优先级（0=普通，1=高）

        Returns:
            任务 ID
        """
        task_id = str(uuid.uuid4())
        now = datetime.now()

        meta = {
            "task_id": task_id,
            "task_type": task_type,
            "params": params,
            "status": TaskStatus.PENDING.value,
            "priority": priority,
            "created_at": now.isoformat(),
        }

        if self._redis:
            # Redis 模式
            await self._redis.set(
                f"task:{task_id}:meta",
                json.dumps(meta, ensure_ascii=False),
                ex=86400 * 7  # 7 天过期
            )
            # 加入队列
            queue_name = "task:queue:high" if priority > 0 else "task:queue:default"
            await self._redis.lpush(queue_name, task_id)
        else:
            # 内存模式：直接执行
            if task_type in self._handlers:
                asyncio.create_task(self._execute_task(task_id, task_type, params))

        logger.info(f"任务已提交: {task_type} ({task_id})")
        return task_id

    async def _execute_task(self, task_id: str, task_type: str, params: dict):
        """执行任务（内存模式）"""
        handler = self._handlers.get(task_type)
        if not handler:
            logger.error(f"未找到任务处理器: {task_type}")
            return

        try:
            result = await handler(params)
            await self._update_task_status(
                task_id, TaskStatus.COMPLETED, result=result
            )
        except Exception as e:
            logger.exception(f"任务执行失败: {task_id}")
            await self._update_task_status(
                task_id, TaskStatus.FAILED, error=str(e)
            )

    async def _update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Any = None,
        error: str = None,
    ):
        """更新任务状态"""
        if not self._redis:
            return

        meta_key = f"task:{task_id}:meta"
        meta_str = await self._redis.get(meta_key)

        if meta_str:
            meta = json.loads(meta_str)
            meta["status"] = status.value
            meta["completed_at"] = datetime.now().isoformat()

            if result is not None:
                await self._redis.set(
                    f"task:{task_id}:result",
                    json.dumps(result, ensure_ascii=False),
                    ex=86400 * 7
                )

            if error:
                meta["error"] = error

            await self._redis.set(meta_key, json.dumps(meta, ensure_ascii=False), ex=86400 * 7)

    async def get_result(
        self,
        task_id: str,
        wait: bool = False,
        timeout: float = 60.0,
    ) -> TaskResult:
        """
        获取任务结果

        Args:
            task_id: 任务 ID
            wait: 是否等待完成
            timeout: 等待超时时间（秒）

        Returns:
            TaskResult 对象
        """
        if not self._redis:
            return TaskResult(task_id=task_id, status=TaskStatus.PENDING)

        meta_key = f"task:{task_id}:meta"
        result_key = f"task:{task_id}:result"

        if wait:
            # 轮询等待
            start = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start < timeout:
                meta_str = await self._redis.get(meta_key)
                if meta_str:
                    meta = json.loads(meta_str)
                    status = TaskStatus(meta["status"])
                    if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                        break
                await asyncio.sleep(0.5)

        meta_str = await self._redis.get(meta_key)
        if not meta_str:
            return TaskResult(task_id=task_id, status=TaskStatus.PENDING)

        meta = json.loads(meta_str)

        # 获取结果
        result = None
        result_str = await self._redis.get(result_key)
        if result_str:
            result = json.loads(result_str)

        # 计算运行时间
        runtime = None
        if meta.get("started_at") and meta.get("completed_at"):
            started = datetime.fromisoformat(meta["started_at"])
            completed = datetime.fromisoformat(meta["completed_at"])
            runtime = (completed - started).total_seconds()

        return TaskResult(
            task_id=task_id,
            status=TaskStatus(meta["status"]),
            result=result,
            error=meta.get("error"),
            task_type=meta.get("task_type"),
            created_at=datetime.fromisoformat(meta["created_at"]) if meta.get("created_at") else None,
            started_at=datetime.fromisoformat(meta["started_at"]) if meta.get("started_at") else None,
            completed_at=datetime.fromisoformat(meta["completed_at"]) if meta.get("completed_at") else None,
            runtime_seconds=runtime,
        )

    async def cancel(self, task_id: str) -> bool:
        """取消任务"""
        if not self._redis:
            return False

        meta_key = f"task:{task_id}:meta"
        meta_str = await self._redis.get(meta_key)

        if not meta_str:
            return False

        meta = json.loads(meta_str)
        current_status = TaskStatus(meta["status"])

        if current_status == TaskStatus.PENDING:
            meta["status"] = TaskStatus.CANCELLED.value
            meta["completed_at"] = datetime.now().isoformat()
            await self._redis.set(meta_key, json.dumps(meta))
            return True
        elif current_status == TaskStatus.RUNNING:
            # 运行中的任务只能标记取消请求
            meta["cancel_requested"] = True
            await self._redis.set(meta_key, json.dumps(meta))
            return True

        return False

    async def list_tasks(
        self,
        status: TaskStatus | None = None,
        task_type: str | None = None,
        limit: int = 50,
    ) -> list[TaskResult]:
        """
        列出任务

        Args:
            status: 按状态过滤
            task_type: 按类型过滤
            limit: 限制数量

        Returns:
            TaskResult 列表
        """
        if not self._redis:
            return []

        # 扫描所有任务
        results = []
        cursor = 0
        while len(results) < limit:
            cursor, keys = await self._redis.scan(
                cursor, match="task:*:meta", count=100
            )
            for key in keys:
                if len(results) >= limit:
                    break

                meta_str = await self._redis.get(key)
                if not meta_str:
                    continue

                meta = json.loads(meta_str)

                # 过滤
                if status and meta["status"] != status.value:
                    continue
                if task_type and meta.get("task_type") != task_type:
                    continue

                results.append(TaskResult(
                    task_id=meta["task_id"],
                    status=TaskStatus(meta["status"]),
                    task_type=meta.get("task_type"),
                    error=meta.get("error"),
                    created_at=datetime.fromisoformat(meta["created_at"]) if meta.get("created_at") else None,
                ))

            if cursor == 0:
                break

        return results


# 全局任务队列
_task_queue: TaskQueue | None = None
_task_queue_lock = asyncio.Lock()


async def get_task_queue() -> TaskQueue:
    """获取任务队列（单例，线程安全）"""
    global _task_queue
    if _task_queue is None:
        async with _task_queue_lock:
            # 双重检查锁定
            if _task_queue is None:
                queue = TaskQueue()
                await queue.connect()
                _task_queue = queue
    return _task_queue
