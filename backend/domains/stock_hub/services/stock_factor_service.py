"""Stock Hub 因子查询服务。

从选股框架目录扫描因子库文件，提供因子列表和详情查询。
"""

import ast
import logging
import re
from pathlib import Path
from typing import Optional

from domains.stock_hub.config import get_framework_path

logger = logging.getLogger(__name__)

# 因子分类映射
_CATEGORY_MAP = {
    "因子库": "技术",
    "截面因子库": "截面",
}


class StockFactorService:
    """因子查询服务。"""

    def __init__(self) -> None:
        self._cache: dict[str, dict] | None = None

    def _scan_factors(self) -> dict[str, dict]:
        """扫描因子库目录，构建因子缓存。"""
        framework = get_framework_path()
        if not framework:
            return {}

        result: dict[str, dict] = {}
        for lib_dir_name, default_cat in [("因子库", "技术"), ("截面因子库", "截面")]:
            lib_path = framework / lib_dir_name
            if not lib_path.is_dir():
                continue
            for py_file in sorted(lib_path.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue
                name = py_file.stem
                meta = self._parse_factor_file(py_file, default_cat)
                meta["name"] = name
                result[name] = meta
        return result

    def _parse_factor_file(self, path: Path, default_category: str) -> dict:
        """解析因子文件，提取元数据。"""
        meta: dict = {
            "category": default_category,
            "description": "",
            "has_add_factor": False,
            "source_code": "",
            "fin_cols": [],
            "ov_cols": [],
            "example_select": "",
            "example_filter": "",
        }
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            meta["source_code"] = source

            # 检测 H财务 分类
            if source.startswith("# H") or "H财务" in source[:200]:
                meta["category"] = "H财务"

            # 检测 add_factor 方法
            meta["has_add_factor"] = "def add_factor" in source

            # 提取描述 (第一个三引号 docstring)
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    ds = ast.get_docstring(node)
                    if ds:
                        meta["description"] = ds[:300]
                        break

            # 提取 fin_cols / ov_cols
            for match in re.finditer(
                r"(fin_cols|ov_cols)\s*=\s*\[([^\]]*)\]", source
            ):
                key = match.group(1)
                vals = [
                    s.strip().strip("'\"")
                    for s in match.group(2).split(",")
                    if s.strip()
                ]
                meta[key] = vals

        except Exception:
            logger.debug("解析因子文件失败: %s", path, exc_info=True)
        return meta

    def get_factors_cache(self) -> dict[str, dict]:
        """获取因子缓存，首次调用时扫描。"""
        if self._cache is None:
            self._cache = self._scan_factors()
        return self._cache

    def refresh_cache(self) -> int:
        """刷新因子缓存，返回因子总数。"""
        self._cache = self._scan_factors()
        return len(self._cache)

    def list_factors(
        self,
        page: int = 1,
        page_size: int = 50,
        search: str = "",
        category: str = "",
    ) -> tuple[list[dict], int]:
        """列出因子（分页+搜索+分类）。"""
        cache = self.get_factors_cache()
        items = list(cache.values())

        # 分类过滤
        if category:
            items = [f for f in items if f.get("category") == category]

        # 搜索
        if search:
            kw = search.lower()
            items = [
                f
                for f in items
                if kw in f.get("name", "").lower()
                or kw in f.get("description", "").lower()
            ]

        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end], total

    def get_factor_detail(self, name: str) -> dict | None:
        """获取因子详情。"""
        cache = self.get_factors_cache()
        return cache.get(name)

    def get_categories(self) -> dict[str, int]:
        """获取分类统计。"""
        cache = self.get_factors_cache()
        counts: dict[str, int] = {}
        for f in cache.values():
            cat = f.get("category", "未分类")
            counts[cat] = counts.get(cat, 0) + 1
        return counts


_service: StockFactorService | None = None


def get_stock_factor_service() -> StockFactorService:
    """获取因子查询服务单例。"""
    global _service
    if _service is None:
        _service = StockFactorService()
    return _service
