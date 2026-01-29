"""
缓存隔离机制

通过环境变量实现多任务回测的缓存隔离。

注意: 使用环境变量而非 threading.local()，因为回测引擎的选币阶段
使用 ProcessPoolExecutor 在子进程中运行，子进程无法继承线程本地变量，
但会继承环境变量。

限制: 当前实现不支持同一进程内的多线程并行回测（环境变量是进程级共享的）。
如需支持，需要修改回测引擎的选币代码，将缓存路径作为参数传递。
"""

import logging
import os
import shutil
import threading
from contextlib import contextmanager
from pathlib import Path

from domains.mcp_core.paths import get_data_dir

logger = logging.getLogger(__name__)

# 环境变量名
_ENV_CACHE_DIR = "BACKTEST_CACHE_DIR"

# 用于保护环境变量操作的锁（同一进程内串行）
_env_lock = threading.Lock()


def get_thread_cache_dir() -> str | None:
    """
    获取当前的缓存目录

    Returns:
        缓存目录路径字符串，如果未设置则返回 None
    """
    return os.environ.get(_ENV_CACHE_DIR)


def set_thread_cache_dir(cache_dir: str | None):
    """
    设置缓存目录

    Args:
        cache_dir: 缓存目录路径，None 表示清除
    """
    if cache_dir is None:
        os.environ.pop(_ENV_CACHE_DIR, None)
    else:
        os.environ[_ENV_CACHE_DIR] = cache_dir


@contextmanager
def isolated_cache(
    task_id: str,
    base_dir: Path | None = None,
    cleanup_on_exit: bool = False,
):
    """
    缓存隔离上下文管理器

    使用环境变量注入隔离的缓存路径，支持子进程继承。
    回测引擎的 path_kit.py 会读取 BACKTEST_CACHE_DIR 环境变量。

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

    # 使用锁保护环境变量操作（串行执行回测任务）
    with _env_lock:
        # 保存旧的缓存目录
        old_cache_dir = get_thread_cache_dir()

        # 设置新的缓存目录
        set_thread_cache_dir(str(task_dir))
        logger.info(f"设置缓存隔离目录: {task_dir}")

        try:
            yield task_dir
        finally:
            # 恢复缓存目录
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


def cleanup_task_cache(task_id: str, base_dir: Path | None = None) -> bool:
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


def list_task_caches(base_dir: Path | None = None) -> list:
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
