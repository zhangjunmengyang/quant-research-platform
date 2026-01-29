"""
文件锁机制

提供跨进程的文件锁，防止并发写入问题。
"""

import fcntl
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


class FileLock:
    """
    文件锁

    使用 fcntl.flock 实现跨进程文件锁。
    """

    def __init__(self, lock_file: Path, timeout: float = 10.0):
        """
        初始化文件锁

        Args:
            lock_file: 锁文件路径
            timeout: 获取锁的超时时间（秒）
        """
        self.lock_file = lock_file
        self.timeout = timeout
        self._fd: int | None = None

    def acquire(self, blocking: bool = True) -> bool:
        """
        获取锁

        Args:
            blocking: 是否阻塞等待锁

        Returns:
            是否成功获取锁
        """
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self.lock_file), os.O_CREAT | os.O_RDWR)

        if blocking:
            # 阻塞模式：带超时的重试
            start_time = time.time()
            while True:
                try:
                    fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return True
                except BlockingIOError:
                    if time.time() - start_time > self.timeout:
                        os.close(self._fd)
                        self._fd = None
                        return False
                    time.sleep(0.1)
        else:
            # 非阻塞模式：立即返回
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except BlockingIOError:
                os.close(self._fd)
                self._fd = None
                return False

    def release(self) -> None:
        """释放锁"""
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                os.close(self._fd)
            except Exception as e:
                logger.warning(f"release_lock_error: {e}")
            finally:
                self._fd = None

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(f"Failed to acquire lock: {self.lock_file}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


@contextmanager
def sync_lock(data_dir: Path, resource_type: str, timeout: float = 10.0):
    """
    同步锁上下文管理器

    为指定资源类型获取文件锁，确保同步操作的原子性。

    Args:
        data_dir: 数据目录
        resource_type: 资源类型（notes, factors, strategies, experiences）
        timeout: 获取锁的超时时间

    Example:
        with sync_lock(data_dir, "notes"):
            # 执行同步操作
            pass
    """
    lock_dir = data_dir / ".locks"
    lock_file = lock_dir / f"{resource_type}.lock"

    lock = FileLock(lock_file, timeout)
    acquired = False

    try:
        acquired = lock.acquire()
        if not acquired:
            logger.warning(f"sync_lock_timeout: {resource_type}")
            raise RuntimeError(f"Failed to acquire sync lock for {resource_type}")
        yield
    finally:
        if acquired:
            lock.release()


def try_sync_lock(data_dir: Path, resource_type: str) -> FileLock | None:
    """
    尝试获取同步锁（非阻塞）

    如果锁已被占用，立即返回 None。

    Args:
        data_dir: 数据目录
        resource_type: 资源类型

    Returns:
        FileLock 实例（成功）或 None（失败）

    Example:
        lock = try_sync_lock(data_dir, "notes")
        if lock:
            try:
                # 执行同步操作
            finally:
                lock.release()
    """
    lock_dir = data_dir / ".locks"
    lock_file = lock_dir / f"{resource_type}.lock"

    lock = FileLock(lock_file)
    if lock.acquire(blocking=False):
        return lock
    return None
