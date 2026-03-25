"""A股因子元数据查询服务"""
import json
import ast
import logging
from typing import List, Optional, Tuple, Dict
from pathlib import Path

from domains.stock_hub.config import (
    FACTOR_LIB_PATH,
    SECTION_FACTOR_LIB_PATH,
    FACTOR_META_CACHE,
)
from domains.stock_hub.models.factor_meta import FactorMeta

logger = logging.getLogger(__name__)


class StockFactorService:
    """因子元数据服务 - 扫描因子库，提供查询"""

    def __init__(self):
        self._factors: Dict[str, FactorMeta] = {}
        self._loaded = False

    def _ensure_loaded(self):
        """确保因子元数据已加载"""
        if not self._loaded:
            self._load_factors()

    def _load_factors(self):
        """加载因子元数据（优先从缓存，否则扫描）"""
        if FACTOR_META_CACHE.exists():
            try:
                data = json.loads(FACTOR_META_CACHE.read_text(encoding="utf-8"))
                for item in data:
                    meta = FactorMeta(**item)
                    self._factors[meta.name] = meta
                self._loaded = True
                logger.info(f"从缓存加载了 {len(self._factors)} 个因子元数据")
                return
            except Exception as e:
                logger.warning(f"缓存加载失败，重新扫描: {e}")

        self._scan_factors()
        self._save_cache()
        self._loaded = True

    def _scan_factors(self):
        """扫描因子库目录，提取元数据"""
        self._factors.clear()

        if not FACTOR_LIB_PATH.exists() and not SECTION_FACTOR_LIB_PATH.exists():
            logger.warning(
                "因子库目录均不存在: %s, %s — 选股框架未安装或未配置",
                FACTOR_LIB_PATH, SECTION_FACTOR_LIB_PATH,
            )

        # 扫描主因子库
        if FACTOR_LIB_PATH.exists():
            for py_file in sorted(FACTOR_LIB_PATH.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue
                meta = self._extract_meta(py_file, "因子库")
                if meta:
                    self._factors[meta.name] = meta

        # 扫描截面因子库
        if SECTION_FACTOR_LIB_PATH.exists():
            for py_file in sorted(SECTION_FACTOR_LIB_PATH.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue
                meta = self._extract_meta(py_file, "截面因子库")
                if meta:
                    self._factors[meta.name] = meta

        logger.info(f"扫描完成: {len(self._factors)} 个因子")

    def _extract_meta(self, py_file: Path, library: str) -> Optional[FactorMeta]:
        """从单个.py文件提取因子元数据（静态AST解析，不import）"""
        name = py_file.stem
        try:
            source = py_file.read_text(encoding="utf-8-sig")
            tree = ast.parse(source)
        except Exception as e:
            logger.warning(f"解析失败 {name}: {e}")
            return FactorMeta(
                name=name,
                category=self._classify(name, library),
                library=library,
                has_add_factor=False,
                file_path=str(py_file),
            )

        has_add_factor = False
        fin_cols: List[str] = []
        ov_cols: List[str] = []
        extra_data: List[str] = []
        fa_intro: Dict = {}

        for node in ast.walk(tree):
            # 检查 add_factor 函数
            if isinstance(node, ast.FunctionDef) and node.name == "add_factor":
                has_add_factor = True

            # 提取顶层变量赋值
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        if var_name == "fin_cols":
                            fin_cols = self._extract_list(node.value)
                        elif var_name == "ov_cols":
                            ov_cols = self._extract_list(node.value)
                        elif var_name == "extra_data":
                            extra_data = self._extract_list(node.value)
                        elif var_name == "FA_INTRO":
                            fa_intro = self._extract_dict(node.value, source)

        description = fa_intro.get("因子说明", "")
        example_select = str(fa_intro.get("选股因子案例", "")) if "选股因子案例" in fa_intro else None
        example_filter = str(fa_intro.get("过滤因子案例", "")) if "过滤因子案例" in fa_intro else None

        return FactorMeta(
            name=name,
            category=self._classify(name, library),
            library=library,
            has_add_factor=has_add_factor,
            fin_cols=fin_cols,
            ov_cols=ov_cols,
            extra_data=extra_data,
            description=description,
            example_select=example_select,
            example_filter=example_filter,
            file_path=str(py_file),
        )

    def _classify(self, name: str, library: str) -> str:
        """分类因子"""
        if library == "截面因子库":
            return "截面"
        if name.startswith("H"):
            return "H财务"
        return "技术"

    def _extract_list(self, node) -> List[str]:
        """从AST节点提取字符串列表"""
        result = []
        if isinstance(node, ast.List):
            for elt in node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    result.append(elt.value)
        return result

    def _extract_dict(self, node, source: str) -> Dict:
        """从AST节点提取字典（尽力而为）"""
        try:
            code = ast.get_source_segment(source, node)
            if code:
                return ast.literal_eval(code)
        except Exception:
            pass
        return {}

    def _save_cache(self):
        """保存缓存"""
        try:
            data = [meta.model_dump() for meta in self._factors.values()]
            FACTOR_META_CACHE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(f"缓存已保存: {len(data)} 个因子")
        except Exception as e:
            logger.warning(f"缓存保存失败: {e}")

    # ---- 查询接口 ----

    def list_factors(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        library: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[FactorMeta], int]:
        """列出因子，支持筛选和分页"""
        self._ensure_loaded()

        factors = list(self._factors.values())

        if category and category != "全部":
            factors = [f for f in factors if f.category == category]
        if library:
            factors = [f for f in factors if f.library == library]
        if search:
            search_lower = search.lower()
            factors = [
                f for f in factors
                if search_lower in f.name.lower() or search_lower in f.description.lower()
            ]

        total = len(factors)
        start = (page - 1) * page_size
        factors = factors[start:start + page_size]

        return factors, total

    def get_factor(self, name: str) -> Optional[FactorMeta]:
        """获取单个因子详情"""
        self._ensure_loaded()
        return self._factors.get(name)

    def get_categories(self) -> Dict[str, int]:
        """获取各分类的因子数量"""
        self._ensure_loaded()
        counts: Dict[str, int] = {}
        for meta in self._factors.values():
            counts[meta.category] = counts.get(meta.category, 0) + 1
        return counts

    def get_factor_code(self, name: str) -> Optional[str]:
        """获取因子源代码"""
        self._ensure_loaded()
        meta = self._factors.get(name)
        if not meta:
            return None
        try:
            return Path(meta.file_path).read_text(encoding="utf-8")
        except Exception:
            return None

    def refresh(self):
        """强制重新扫描因子库"""
        self._scan_factors()
        self._save_cache()
        logger.info(f"因子库已刷新: {len(self._factors)} 个因子")


# 单例
_service: Optional[StockFactorService] = None


def get_stock_factor_service() -> StockFactorService:
    """获取服务单例"""
    global _service
    if _service is None:
        _service = StockFactorService()
    return _service
