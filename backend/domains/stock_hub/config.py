"""Stock Hub 配置。

所有路径通过环境变量读取，不硬编码本机路径。
如果环境变量未设置，对应功能标记为不可用。
"""

import os
from pathlib import Path


# 外部依赖路径 (全部通过环境变量配置)
STOCK_FRAMEWORK_PATH: str | None = os.environ.get("STOCK_FRAMEWORK_PATH")
FUEL_PYTHON_PATH: str | None = os.environ.get("FUEL_PYTHON_PATH")
DATA_CENTER_PATH: str | None = os.environ.get("DATA_CENTER_PATH")

# 超时设置 (秒)
BACKTEST_TIMEOUT: int = int(os.environ.get("STOCK_HUB_BACKTEST_TIMEOUT", "1800"))
ANALYSIS_TIMEOUT: int = int(os.environ.get("STOCK_HUB_ANALYSIS_TIMEOUT", "600"))
BATCH_ANALYSIS_TIMEOUT: int = int(
    os.environ.get("STOCK_HUB_BATCH_TIMEOUT", "7200")
)

# MCP 服务端口
MCP_PORT: int = int(os.environ.get("STOCK_HUB_MCP_PORT", "6795"))


def get_framework_path() -> Path | None:
    """返回选股框架路径，未配置则返回 None。"""
    if STOCK_FRAMEWORK_PATH:
        p = Path(STOCK_FRAMEWORK_PATH)
        if p.exists():
            return p
    return None


def get_fuel_python() -> Path | None:
    """返回 Fuel Python 可执行文件路径，未配置则返回 None。"""
    if FUEL_PYTHON_PATH:
        p = Path(FUEL_PYTHON_PATH)
        if p.exists():
            return p
    return None


def is_available() -> bool:
    """检查 stock_hub 核心依赖是否可用。"""
    return get_framework_path() is not None and get_fuel_python() is not None
