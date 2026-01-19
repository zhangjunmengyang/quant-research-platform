"""
缓存隔离机制

通过线程本地存储实现多任务并行回测的缓存隔离。

注意：环境变量 os.environ 在多线程环境下是全局共享的，会导致并发冲突。
本模块使用 threading.local() 实现线程安全的缓存路径隔离。
"""

import shutil
import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from domains.mcp_core.paths import get_data_dir

logger = logging.getLogger(__name__)

# 线程本地存储，用于存储每个线程的缓存目录
_thread_local = threading.local()


def get_thread_cache_dir() -> Optional[str]:
    """
    获取当前线程的缓存目录（线程安全）

    Returns:
        缓存目录路径字符串，如果未设置则返回 None
    """
    return getattr(_thread_local, "cache_dir", None)


def set_thread_cache_dir(cache_dir: Optional[str]):
    """
    设置当前线程的缓存目录（线程安全）

    Args:
        cache_dir: 缓存目录路径，None 表示清除
    """
    if cache_dir is None:
        if hasattr(_thread_local, "cache_dir"):
            delattr(_thread_local, "cache_dir")
    else:
        _thread_local.cache_dir = cache_dir


@contextmanager
def isolated_cache(
    task_id: str,
    base_dir: Optional[Path] = None,
    cleanup_on_exit: bool = False,
):
    """
    缓存隔离上下文管理器（线程安全）

    使用线程本地存储注入隔离的缓存路径，支持多线程并行回测。
    回测引擎的 path_kit.py 需要调用 get_thread_cache_dir() 获取缓存路径。

    Args:
        task_id: 任务ID
        base_dir: 任务基础目录，默认为 data/tasks/
        cleanup_on_exit: 退出时是否清理缓存目录

    Yields:
        缓存目录路径
    """
    if base_dir is None:
        base_dir = get_data_dir() / "tasks"

    task_dir = base_dir / task_id / "cache"
    task_dir.mkdir(parents=True, exist_ok=True)

    # 保存旧的线程本地缓存目录
    old_cache_dir = get_thread_cache_dir()

    # 设置新的缓存目录（线程安全）
    set_thread_cache_dir(str(task_dir))
    logger.info(f"[线程 {threading.current_thread().name}] 设置缓存隔离目录: {task_dir}")

    try:
        yield task_dir
    finally:
        # 恢复线程本地缓存目录
        set_thread_cache_dir(old_cache_dir)

        # 清理缓存目录
        if cleanup_on_exit and task_dir.exists():
            try:
                shutil.rmtree(task_dir)
                logger.info(f"清理缓存目录: {task_dir}")
            except Exception as e:
                logger.warning(f"清理缓存目录失败: {e}")


def get_cache_dir() -> Path:
    """
    获取当前缓存目录（线程安全）

    使用线程本地存储获取缓存目录，如果未设置则返回默认目录。
    所有回测任务都应该通过 isolated_cache 上下文管理器设置缓存目录。
    """
    thread_cache = get_thread_cache_dir()
    if thread_cache:
        return Path(thread_cache)

    return get_data_dir() / "cache"


def cleanup_task_cache(task_id: str, base_dir: Optional[Path] = None) -> bool:
    """
    清理指定任务的缓存

    Args:
        task_id: 任务ID
        base_dir: 任务基础目录

    Returns:
        是否清理成功
    """
    if base_dir is None:
        base_dir = get_data_dir() / "tasks"

    task_dir = base_dir / task_id
    if task_dir.exists():
        try:
            shutil.rmtree(task_dir)
            logger.info(f"清理任务目录: {task_dir}")
            return True
        except Exception as e:
            logger.error(f"清理任务目录失败: {e}")
            return False
    return True


def list_task_caches(base_dir: Optional[Path] = None) -> list:
    """
    列出所有任务缓存目录

    Args:
        base_dir: 任务基础目录

    Returns:
        任务ID列表
    """
    if base_dir is None:
        base_dir = get_data_dir() / "tasks"

    if not base_dir.exists():
        return []

    return [d.name for d in base_dir.iterdir() if d.is_dir()]
