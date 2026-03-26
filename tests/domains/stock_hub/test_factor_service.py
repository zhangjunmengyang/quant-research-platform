"""stock_hub.services.stock_factor_service 单元测试。"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from domains.stock_hub.services.stock_factor_service import StockFactorService


@pytest.fixture
def mock_framework(tmp_path):
    """创建模拟的选股框架目录结构。"""
    factor_lib = tmp_path / "因子库"
    factor_lib.mkdir()

    # 创建模拟因子文件
    (factor_lib / "市值.py").write_text(
        '# 技术因子\n\ndef add_factor(df):\n    """计算市值因子。"""\n    pass\n',
        encoding="utf-8",
    )
    (factor_lib / "换手率.py").write_text(
        "# 技术因子\ndef calc(df):\n    pass\n",
        encoding="utf-8",
    )
    (factor_lib / "_helper.py").write_text(
        "# 私有模块\n",
        encoding="utf-8",
    )

    section_lib = tmp_path / "截面因子库"
    section_lib.mkdir()
    (section_lib / "排名差值.py").write_text(
        "# 截面因子\ndef add_factor(df):\n    pass\n",
        encoding="utf-8",
    )

    return tmp_path


def test_scan_factors_with_mock_framework(mock_framework):
    """扫描因子库目录。"""
    with patch(
        "domains.stock_hub.services.stock_factor_service.get_framework_path",
        return_value=mock_framework,
    ):
        svc = StockFactorService()
        cache = svc.get_factors_cache()

        assert len(cache) == 3  # 市值 + 换手率 + 排名差值 (_helper 被跳过)
        assert "市值" in cache
        assert "换手率" in cache
        assert "排名差值" in cache
        assert "_helper" not in cache

        # 检查 add_factor 检测
        assert cache["市值"]["has_add_factor"] is True
        assert cache["换手率"]["has_add_factor"] is False


def test_list_factors_pagination(mock_framework):
    """分页查询。"""
    with patch(
        "domains.stock_hub.services.stock_factor_service.get_framework_path",
        return_value=mock_framework,
    ):
        svc = StockFactorService()

        items, total = svc.list_factors(page=1, page_size=2)
        assert total == 3
        assert len(items) == 2

        items, total = svc.list_factors(page=2, page_size=2)
        assert total == 3
        assert len(items) == 1


def test_list_factors_search(mock_framework):
    """搜索过滤。"""
    with patch(
        "domains.stock_hub.services.stock_factor_service.get_framework_path",
        return_value=mock_framework,
    ):
        svc = StockFactorService()

        items, total = svc.list_factors(search="市值")
        assert total == 1
        assert items[0]["name"] == "市值"


def test_list_factors_category(mock_framework):
    """分类过滤。"""
    with patch(
        "domains.stock_hub.services.stock_factor_service.get_framework_path",
        return_value=mock_framework,
    ):
        svc = StockFactorService()

        items, total = svc.list_factors(category="截面")
        assert total == 1
        assert items[0]["name"] == "排名差值"


def test_get_factor_detail(mock_framework):
    """获取因子详情。"""
    with patch(
        "domains.stock_hub.services.stock_factor_service.get_framework_path",
        return_value=mock_framework,
    ):
        svc = StockFactorService()

        detail = svc.get_factor_detail("市值")
        assert detail is not None
        assert detail["name"] == "市值"
        assert "add_factor" in detail["source_code"]

        assert svc.get_factor_detail("不存在") is None


def test_get_categories(mock_framework):
    """分类统计。"""
    with patch(
        "domains.stock_hub.services.stock_factor_service.get_framework_path",
        return_value=mock_framework,
    ):
        svc = StockFactorService()
        cats = svc.get_categories()

        assert "技术" in cats
        assert "截面" in cats
        assert cats["技术"] == 2
        assert cats["截面"] == 1


def test_refresh_cache(mock_framework):
    """刷新缓存。"""
    with patch(
        "domains.stock_hub.services.stock_factor_service.get_framework_path",
        return_value=mock_framework,
    ):
        svc = StockFactorService()
        count = svc.refresh_cache()
        assert count == 3


def test_empty_when_not_configured():
    """未配置时返回空结果。"""
    with patch(
        "domains.stock_hub.services.stock_factor_service.get_framework_path",
        return_value=None,
    ):
        svc = StockFactorService()
        items, total = svc.list_factors()
        assert total == 0
        assert items == []
