"""
项目路径管理

提供统一的项目路径获取接口，避免各模块重复实现。
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional


@lru_cache(maxsize=1)
def get_project_root() -> Path:
    """
    获取项目根目录

    通过查找 .git 目录来确定项目根目录。
    结果被缓存，多次调用不会重复计算。

    Returns:
        项目根目录路径
    """
    current = Path(__file__).resolve()

    # 向上最多查找 10 层
    for _ in range(10):
        current = current.parent
        if (current / ".git").exists():
            return current

    # 回退：从当前文件向上推断
    # backend/domains/mcp_core/paths.py -> 项目根
    return Path(__file__).resolve().parent.parent.parent.parent


def get_data_dir() -> Path:
    """
    获取数据目录（项目根目录/data）

    自动创建目录（如果不存在）。
    """
    data_dir = get_project_root() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_config_dir() -> Path:
    """
    获取配置目录（项目根目录/config）

    自动创建目录（如果不存在）。
    """
    config_dir = get_project_root() / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_factors_dir() -> Path:
    """
    获取因子代码目录（项目根目录/factors）

    自动创建目录（如果不存在）。
    """
    factors_dir = get_project_root() / "factors"
    factors_dir.mkdir(parents=True, exist_ok=True)
    return factors_dir


def get_sections_dir() -> Path:
    """
    获取截面因子目录（项目根目录/sections）

    自动创建目录（如果不存在）。
    """
    sections_dir = get_project_root() / "sections"
    sections_dir.mkdir(parents=True, exist_ok=True)
    return sections_dir


def get_backend_dir() -> Path:
    """获取 backend 目录"""
    return get_project_root() / "backend"


def get_domain_dir(domain_name: str) -> Path:
    """获取指定业务域目录"""
    return get_backend_dir() / "domains" / domain_name


__all__ = [
    "get_project_root",
    "get_data_dir",
    "get_config_dir",
    "get_factors_dir",
    "get_sections_dir",
    "get_backend_dir",
    "get_domain_dir",
]
