"""stock_hub.services.stock_analysis_service 单元测试。"""

from pathlib import Path
from unittest.mock import patch

import pytest
from domains.stock_hub.services.stock_analysis_service import (
    StockAnalysisService,
    _get_backtest_dir,
    _validate_data_path,
)


@pytest.fixture
def mock_framework_with_cache(tmp_path):
    """创建带回测缓存的模拟框架目录。"""
    cache_root = tmp_path / "data" / "运行缓存"
    cache_root.mkdir(parents=True)

    # 创建回测目录
    bt1 = cache_root / "test_backtest"
    bt1.mkdir()
    (bt1 / "factor_市值.pkl").write_bytes(b"mock_data")
    (bt1 / "factor_ROE.pkl").write_bytes(b"mock_data")

    bt2 = cache_root / "empty_backtest"
    bt2.mkdir()
    # 无 pkl 文件

    return tmp_path


def test_validate_data_path_within_cache(tmp_path):
    """白名单内路径校验通过。"""
    cache = tmp_path / "data" / "运行缓存" / "test"
    cache.mkdir(parents=True)
    assert _validate_data_path(cache, tmp_path) is True


def test_validate_data_path_outside_cache(tmp_path):
    """白名单外路径校验失败。"""
    outside = tmp_path / "other" / "dir"
    outside.mkdir(parents=True)
    assert _validate_data_path(outside, tmp_path) is False


def test_list_available_backtests(mock_framework_with_cache):
    """列出可用回测数据源。"""
    with patch(
        "domains.stock_hub.services.stock_analysis_service.get_framework_path",
        return_value=mock_framework_with_cache,
    ):
        svc = StockAnalysisService()
        backtests = svc.list_available_backtests()

        assert len(backtests) == 1  # empty_backtest 没有 pkl 文件，不列出
        assert backtests[0]["name"] == "test_backtest"
        assert backtests[0]["factor_count"] == 2


def test_list_cached_factors(mock_framework_with_cache):
    """列出缓存因子。"""
    with patch(
        "domains.stock_hub.services.stock_analysis_service.get_framework_path",
        return_value=mock_framework_with_cache,
    ):
        svc = StockAnalysisService()
        factors = svc.list_cached_factors("test_backtest")

        assert len(factors) == 2
        names = [f["name"] for f in factors]
        assert "factor_市值" in names
        assert "factor_ROE" in names


def test_list_cached_factors_empty_when_not_configured():
    """未配置时返回空。"""
    with patch(
        "domains.stock_hub.services.stock_analysis_service.get_framework_path",
        return_value=None,
    ):
        svc = StockAnalysisService()
        assert svc.list_cached_factors() == []


def test_get_status_not_configured():
    """未配置时 available=False。"""
    with patch(
        "domains.stock_hub.services.stock_analysis_service.get_framework_path",
        return_value=None,
    ), patch(
        "domains.stock_hub.services.stock_analysis_service.get_fuel_python",
        return_value=None,
    ):
        svc = StockAnalysisService()
        status = svc.get_status()

        assert status["available"] is False
        assert status["factor_lib_exists"] is False


def test_get_status_configured(mock_framework_with_cache):
    """配置时返回正确状态。"""
    # 创建因子库目录
    (mock_framework_with_cache / "因子库").mkdir()

    with patch(
        "domains.stock_hub.services.stock_analysis_service.get_framework_path",
        return_value=mock_framework_with_cache,
    ), patch(
        "domains.stock_hub.services.stock_analysis_service.get_fuel_python",
        return_value=Path("/some/python"),
    ):
        svc = StockAnalysisService()
        status = svc.get_status()

        assert status["available"] is True
        assert status["analysis_ready"] is False
        assert status["factor_lib_exists"] is True
        assert status["section_factor_lib_exists"] is False
        assert status["available_backtests_count"] == 1


def test_get_status_analysis_ready_when_scripts_exist(mock_framework_with_cache):
    """脚本和回测数据齐全时，analysis_ready=True。"""
    (mock_framework_with_cache / "因子库").mkdir()
    (mock_framework_with_cache / "run_enhanced_analysis.py").write_text("", encoding="utf-8")
    (mock_framework_with_cache / "run_dual_analysis.py").write_text("", encoding="utf-8")

    with patch(
        "domains.stock_hub.services.stock_analysis_service.get_framework_path",
        return_value=mock_framework_with_cache,
    ), patch(
        "domains.stock_hub.services.stock_analysis_service.get_fuel_python",
        return_value=Path("/some/python"),
    ):
        svc = StockAnalysisService()
        status = svc.get_status()

        assert status["analysis_ready"] is True
        assert status["cache_root_exists"] is True
        assert status["enhanced_script_exists"] is True
        assert status["dual_script_exists"] is True


def test_get_backtest_dir_rejects_default_path_outside_cache(tmp_path):
    """默认 backtest_name 也必须受白名单限制。"""
    cache_root = tmp_path / "data" / "运行缓存"
    cache_root.mkdir(parents=True)
    (tmp_path / "config.py").write_text("backtest_name = '../escape'", encoding="utf-8")

    assert _get_backtest_dir(tmp_path) is None


def test_run_enhanced_analysis_not_configured():
    """未配置时分析返回错误。"""
    with patch(
        "domains.stock_hub.services.stock_analysis_service.get_framework_path",
        return_value=None,
    ), patch(
        "domains.stock_hub.services.stock_analysis_service.get_fuel_python",
        return_value=None,
    ):
        svc = StockAnalysisService()
        result = svc.run_enhanced_analysis("factor_市值", ["5_0"])
        assert "error" in result
