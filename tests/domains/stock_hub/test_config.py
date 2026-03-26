"""stock_hub.config 单元测试。"""

import os
from unittest.mock import patch

import pytest


def test_is_available_returns_false_when_not_configured():
    """未配置环境变量时返回 False。"""
    with patch.dict(os.environ, {}, clear=True):
        # 需要重新导入以让模块重新读取环境变量
        import importlib
        import domains.stock_hub.config as cfg

        importlib.reload(cfg)
        assert cfg.is_available() is False


def test_is_available_returns_false_with_nonexistent_path():
    """路径不存在时返回 False。"""
    with patch.dict(
        os.environ,
        {
            "STOCK_FRAMEWORK_PATH": "/nonexistent/path/stock-pro",
            "FUEL_PYTHON_PATH": "/nonexistent/python.exe",
        },
    ):
        import importlib
        import domains.stock_hub.config as cfg

        importlib.reload(cfg)
        assert cfg.get_framework_path() is None
        assert cfg.get_fuel_python() is None
        assert cfg.is_available() is False


def test_default_timeout_values():
    """默认超时配置。"""
    from domains.stock_hub.config import BACKTEST_TIMEOUT, ANALYSIS_TIMEOUT, MCP_PORT

    assert BACKTEST_TIMEOUT == 1800
    assert ANALYSIS_TIMEOUT == 600
    assert MCP_PORT == 6795


def test_custom_timeout_from_env():
    """自定义超时通过环境变量覆盖。"""
    with patch.dict(
        os.environ,
        {"STOCK_HUB_BACKTEST_TIMEOUT": "3600", "STOCK_HUB_MCP_PORT": "7000"},
    ):
        import importlib
        import domains.stock_hub.config as cfg

        importlib.reload(cfg)
        assert cfg.BACKTEST_TIMEOUT == 3600
        assert cfg.MCP_PORT == 7000
