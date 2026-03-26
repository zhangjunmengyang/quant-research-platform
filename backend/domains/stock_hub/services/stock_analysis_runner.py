"""Stock Hub 分析任务执行器。"""

import logging
import os
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from domains.stock_hub.services.stock_analysis_service import (
    StockAnalysisService,
    get_stock_analysis_service,
)

logger = logging.getLogger(__name__)


def _get_default_workers() -> int:
    """根据 CPU 核心数计算默认分析并行数。"""
    cpu_count = os.cpu_count() or 2
    return max(1, min(cpu_count // 2, 4))


@dataclass
class AnalysisTaskInfo:
    """分析任务状态。"""

    task_id: str
    task_type: str
    status: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    message: str = ""
    error_message: str | None = None
    result: dict[str, Any] | None = None


class StockAnalysisRunner:
    """使用线程池异步执行 stock_hub 分析任务。"""

    def __init__(
        self,
        service: StockAnalysisService | None = None,
        max_workers: int | None = None,
    ) -> None:
        if max_workers is None:
            max_workers = _get_default_workers()

        self._service = service or get_stock_analysis_service()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: dict[str, AnalysisTaskInfo] = {}
        self._futures: dict[str, Future] = {}
        self._lock = threading.Lock()

    def submit_enhanced(
        self,
        factor_name: str,
        period_offset_list: list[str],
        rebalance_time: str = "0955",
        bins: int = 10,
        backtest_name: str | None = None,
    ) -> str:
        """提交增强单因子分析任务。"""
        return self._submit(
            "enhanced",
            self._service.run_enhanced_analysis,
            factor_name=factor_name,
            period_offset_list=period_offset_list,
            rebalance_time=rebalance_time,
            bins=bins,
            backtest_name=backtest_name,
        )

    def submit_dual(
        self,
        main_factor: str,
        sub_factor: str,
        period_offset_list: list[str],
        rebalance_time: str = "0955",
        bins: int = 5,
        backtest_name: str | None = None,
    ) -> str:
        """提交双因子分析任务。"""
        return self._submit(
            "dual",
            self._service.run_dual_analysis,
            main_factor=main_factor,
            sub_factor=sub_factor,
            period_offset_list=period_offset_list,
            rebalance_time=rebalance_time,
            bins=bins,
            backtest_name=backtest_name,
        )

    def _submit(
        self,
        task_type: str,
        func: Callable[..., dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        task_id = str(uuid.uuid4())
        task = AnalysisTaskInfo(
            task_id=task_id,
            task_type=task_type,
            status="pending",
            created_at=datetime.now(),
            message="分析任务已提交",
        )

        with self._lock:
            self._tasks[task_id] = task
            future = self._executor.submit(self._run_task, task_id, func, kwargs)
            self._futures[task_id] = future

        return task_id

    def _run_task(
        self,
        task_id: str,
        func: Callable[..., dict[str, Any]],
        kwargs: dict[str, Any],
    ) -> None:
        self._update_task(
            task_id,
            status="running",
            started_at=datetime.now(),
            message="分析任务执行中",
        )

        try:
            result = func(**kwargs)
            if "error" in result:
                self._update_task(
                    task_id,
                    status="failed",
                    completed_at=datetime.now(),
                    message="分析任务执行失败",
                    error_message=str(result["error"]),
                )
                return

            self._update_task(
                task_id,
                status="completed",
                completed_at=datetime.now(),
                message="分析任务执行完成",
                result=result,
            )
        except Exception as exc:
            logger.exception("分析任务执行异常 task_id=%s", task_id)
            self._update_task(
                task_id,
                status="failed",
                completed_at=datetime.now(),
                message="分析任务执行失败",
                error_message=str(exc),
            )
        finally:
            with self._lock:
                self._futures.pop(task_id, None)

    def _update_task(self, task_id: str, **changes: Any) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return

            for key, value in changes.items():
                setattr(task, key, value)

    def get_status(self, task_id: str) -> AnalysisTaskInfo | None:
        """查询任务状态。"""
        with self._lock:
            return self._tasks.get(task_id)

    def get_result(self, task_id: str) -> dict[str, Any] | None:
        """查询任务结果。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            return task.result


_runner: StockAnalysisRunner | None = None


def get_stock_analysis_runner() -> StockAnalysisRunner:
    """获取分析任务执行器单例。"""
    global _runner
    if _runner is None:
        _runner = StockAnalysisRunner()
    return _runner
