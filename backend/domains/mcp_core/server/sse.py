"""
SSE (Server-Sent Events) 支持模块

用于长时间运行的任务（如回测）进度推送。

内存管理:
- 任务完成后自动清理（延迟清理以允许客户端获取最终状态）
- 定时清理过期任务
- 限制最大任务数量
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# 配置常量
TASK_CLEANUP_DELAY = 60  # 任务完成后延迟清理时间（秒）
TASK_MAX_AGE = 3600  # 任务最大存活时间（秒）
MAX_TASKS = 1000  # 最大任务数量
CLEANUP_INTERVAL = 300  # 定期清理间隔（秒）


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskProgress:
    """任务进度信息"""
    task_id: str
    status: TaskStatus
    progress: float = 0.0  # 0-100
    message: str = ""
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    current_step_num: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    _created_timestamp: float = field(default_factory=time.time)  # 用于清理判断

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "current_step_num": self.current_step_num,
            "data": self.data,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_sse_event(self, event_type: str = "progress") -> str:
        """转换为 SSE 事件格式"""
        data = json.dumps(self.to_dict(), ensure_ascii=False)
        return f"event: {event_type}\ndata: {data}\n\n"


class TaskProgressManager:
    """
    任务进度管理器

    管理长时间运行任务的进度，支持 SSE 推送给订阅的客户端。

    内存管理:
    - 任务完成后延迟清理，允许客户端获取最终状态
    - 定期清理过期任务
    - 限制最大任务数量

    使用方式:
        manager = TaskProgressManager.get_instance()

        # 创建任务
        task_id = manager.create_task()

        # 更新进度
        manager.update_progress(task_id, progress=50, message="处理中...")

        # 客户端订阅进度
        async for event in manager.subscribe(task_id):
            yield event
    """

    _instance = None

    @classmethod
    def get_instance(cls) -> 'TaskProgressManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._tasks: Dict[str, TaskProgress] = {}
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """启动后台清理任务"""
        if self._running:
            return
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.debug("[SSE] TaskProgressManager 后台清理任务已启动")

    async def stop(self):
        """停止后台清理任务"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.debug("[SSE] TaskProgressManager 后台清理任务已停止")

    async def _cleanup_loop(self):
        """后台清理循环"""
        while self._running:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL)
                self._cleanup_expired_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SSE] 清理任务出错: {e}")

    def _cleanup_expired_tasks(self):
        """清理过期任务（线程安全）"""
        now = time.time()
        expired_tasks = []

        # 先复制字典避免遍历时修改
        tasks_snapshot = list(self._tasks.items())

        for task_id, task in tasks_snapshot:
            # 检查是否超过最大存活时间
            age = now - task._created_timestamp
            if age > TASK_MAX_AGE:
                expired_tasks.append(task_id)
                continue

            # 检查已完成任务是否超过延迟清理时间
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                # 使用 updated_at 判断完成时间
                completed_age = now - task._created_timestamp
                if completed_age > TASK_CLEANUP_DELAY and age > TASK_CLEANUP_DELAY:
                    expired_tasks.append(task_id)

        # 执行清理
        for task_id in expired_tasks:
            self.cleanup_task(task_id)
            logger.debug(f"[SSE] 清理过期任务: {task_id}")

        if expired_tasks:
            logger.info(f"[SSE] 清理了 {len(expired_tasks)} 个过期任务，剩余 {len(self._tasks)} 个")

    def create_task(self, task_id: Optional[str] = None) -> str:
        """创建新任务，返回任务ID"""
        if task_id is None:
            task_id = str(uuid.uuid4())

        # 检查是否超过最大任务数量
        if len(self._tasks) >= MAX_TASKS:
            # 强制清理最旧的已完成任务
            self._force_cleanup_oldest()

        self._tasks[task_id] = TaskProgress(
            task_id=task_id,
            status=TaskStatus.PENDING,
        )
        self._subscribers[task_id] = set()

        logger.debug(f"[SSE] 创建任务: {task_id}, 当前任务数: {len(self._tasks)}")
        return task_id

    def _force_cleanup_oldest(self):
        """强制清理最旧的任务（线程安全）"""
        if not self._tasks:
            return

        # 先复制字典避免遍历时修改
        tasks_snapshot = list(self._tasks.items())

        # 优先清理已完成的任务
        completed_tasks = [
            (task_id, task)
            for task_id, task in tasks_snapshot
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]

        if completed_tasks:
            # 按创建时间排序，清理最旧的一半
            completed_tasks.sort(key=lambda x: x[1]._created_timestamp)
            to_cleanup = completed_tasks[:len(completed_tasks) // 2 + 1]
            for task_id, _ in to_cleanup:
                self.cleanup_task(task_id)
            logger.warning(f"[SSE] 强制清理 {len(to_cleanup)} 个已完成任务")
        else:
            # 没有已完成任务，清理最旧的运行中任务
            tasks_snapshot.sort(key=lambda x: x[1]._created_timestamp)
            oldest = tasks_snapshot[0]
            self.cleanup_task(oldest[0])
            logger.warning(f"[SSE] 强制清理最旧任务: {oldest[0]}")

    def get_task(self, task_id: str) -> Optional[TaskProgress]:
        """获取任务进度"""
        return self._tasks.get(task_id)

    async def update_progress(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        current_step: Optional[str] = None,
        total_steps: Optional[int] = None,
        current_step_num: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        更新任务进度并通知所有订阅者

        Args:
            task_id: 任务ID
            status: 任务状态
            progress: 进度百分比 (0-100)
            message: 进度消息
            current_step: 当前步骤名称
            total_steps: 总步骤数
            current_step_num: 当前步骤编号
            data: 附加数据
            error: 错误信息
        """
        task = self._tasks.get(task_id)
        if task is None:
            logger.warning(f"[SSE] 任务不存在: {task_id}")
            return

        # 更新字段
        if status is not None:
            task.status = status
        if progress is not None:
            task.progress = progress
        if message is not None:
            task.message = message
        if current_step is not None:
            task.current_step = current_step
        if total_steps is not None:
            task.total_steps = total_steps
        if current_step_num is not None:
            task.current_step_num = current_step_num
        if data is not None:
            task.data = data
        if error is not None:
            task.error = error

        task.updated_at = datetime.now()

        # 通知所有订阅者
        await self._notify_subscribers(task_id, task)

    async def _notify_subscribers(self, task_id: str, task: TaskProgress) -> None:
        """通知所有订阅者（线程安全）"""
        subscribers = self._subscribers.get(task_id, set())
        if not subscribers:
            return

        # 复制集合避免遍历时修改
        subscribers_snapshot = list(subscribers)

        # 移除已断开的订阅者
        dead_queues = []

        for queue in subscribers_snapshot:
            try:
                await queue.put(task.to_sse_event())
            except Exception as e:
                logger.warning(f"[SSE] 通知订阅者失败: {e}")
                dead_queues.append(queue)

        # 清理死亡的队列
        for queue in dead_queues:
            subscribers.discard(queue)

    async def subscribe(
        self,
        task_id: str,
        timeout: float = 300,  # 5分钟超时
    ) -> AsyncGenerator[str, None]:
        """
        订阅任务进度

        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）

        Yields:
            SSE 事件字符串
        """
        task = self._tasks.get(task_id)
        if task is None:
            yield f"event: error\ndata: {json.dumps({'error': f'任务不存在: {task_id}'}, ensure_ascii=False)}\n\n"
            return

        # 创建订阅队列
        queue: asyncio.Queue = asyncio.Queue()

        async with self._lock:
            self._subscribers[task_id].add(queue)

        try:
            # 先发送当前状态
            yield task.to_sse_event()

            # 持续监听更新
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=timeout)
                    yield event

                    # 检查是否已完成
                    current_task = self._tasks.get(task_id)
                    if current_task and current_task.status in (
                        TaskStatus.COMPLETED,
                        TaskStatus.FAILED,
                        TaskStatus.CANCELLED,
                    ):
                        break

                except asyncio.TimeoutError:
                    # 发送心跳
                    yield ": heartbeat\n\n"

        finally:
            # 清理订阅
            async with self._lock:
                self._subscribers[task_id].discard(queue)

    def start_task(self, task_id: str) -> None:
        """标记任务开始"""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.RUNNING
            task.updated_at = datetime.now()

    async def complete_task(
        self,
        task_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """标记任务完成"""
        await self.update_progress(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="任务完成",
            data=data,
        )

    async def fail_task(
        self,
        task_id: str,
        error: str,
    ) -> None:
        """标记任务失败"""
        await self.update_progress(
            task_id,
            status=TaskStatus.FAILED,
            error=error,
            message=f"任务失败: {error}",
        )

    async def cancel_task(self, task_id: str) -> None:
        """取消任务"""
        await self.update_progress(
            task_id,
            status=TaskStatus.CANCELLED,
            message="任务已取消",
        )

    def cleanup_task(self, task_id: str) -> None:
        """清理已完成的任务"""
        self._tasks.pop(task_id, None)
        self._subscribers.pop(task_id, None)

    def list_tasks(self) -> List[TaskProgress]:
        """列出所有任务"""
        return list(self._tasks.values())


# 便捷函数
def get_task_manager() -> TaskProgressManager:
    """获取任务进度管理器实例"""
    return TaskProgressManager.get_instance()
