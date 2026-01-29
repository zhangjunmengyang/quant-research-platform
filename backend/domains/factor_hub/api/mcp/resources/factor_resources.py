"""
因子资源定义

提供 MCP Resources，用于向 LLM 提供只读数据上下文。
基于 mcp_core.BaseResourceProvider 实现。
"""

import json
import logging

from domains.mcp_core import (
    BaseResourceProvider,
    ResourceContent,
)

logger = logging.getLogger(__name__)


class FactorResourceProvider(BaseResourceProvider):
    """
    因子资源提供者

    管理所有可用的 MCP 资源，支持动态资源发现和模板资源。
    继承 mcp_core.BaseResourceProvider。
    """

    def __init__(self, factor_service=None):
        super().__init__()
        self._factor_service = factor_service
        self._register_factor_resources()

    @property
    def factor_service(self):
        """延迟获取 factor_service"""
        if self._factor_service is None:
            from ....services.factor_service import get_factor_service
            self._factor_service = get_factor_service()
        return self._factor_service

    def _register_factor_resources(self):
        """注册因子相关的资源"""
        # 统计信息资源
        self.register_static(
            uri="factor://stats",
            name="因子库统计",
            description="因子库的整体统计信息，包括总数、评分分布、风格分布等",
            handler=self._read_stats,
        )

        # 风格列表资源
        self.register_static(
            uri="factor://styles",
            name="风格列表",
            description="因子库中所有可用的风格分类",
            handler=self._read_styles,
        )

        # 排除因子列表
        self.register_static(
            uri="factor://excluded",
            name="排除因子列表",
            description="已排除的因子文件名列表及排除原因",
            handler=self._read_excluded,
        )

        # 高分因子列表
        self.register_static(
            uri="factor://top-scored",
            name="高分因子",
            description="评分最高的因子列表（前20个）",
            handler=self._read_top_scored,
        )

        # 验证通过的因子列表
        self.register_static(
            uri="factor://passed",
            name="验证通过因子",
            description="验证通过的因子列表",
            handler=self._read_passed,
        )

        # 废弃（失败研究）的因子列表
        self.register_static(
            uri="factor://failed",
            name="废弃因子",
            description="废弃（失败研究）的因子列表",
            handler=self._read_failed,
        )

        # 动态资源模板
        self.register_dynamic(
            pattern="factor://factor/{filename}",
            name="因子详情",
            description="获取指定因子的详细信息，将 {filename} 替换为实际文件名",
            handler=self._read_factor_detail,
        )

        self.register_dynamic(
            pattern="factor://factor/{filename}/code",
            name="因子代码",
            description="获取指定因子的源代码",
            handler=self._read_factor_code,
            mime_type="text/x-python",
        )

    async def _read_stats(self) -> ResourceContent:
        """读取统计信息"""
        stats = self.factor_service.get_stats()
        return ResourceContent(
            uri="factor://stats",
            mime_type="application/json",
            text=json.dumps(stats, ensure_ascii=False, indent=2),
        )

    async def _read_styles(self) -> ResourceContent:
        """读取风格列表"""
        styles = self.factor_service.get_styles()
        return ResourceContent(
            uri="factor://styles",
            mime_type="application/json",
            text=json.dumps({"styles": styles}, ensure_ascii=False),
        )

    async def _read_excluded(self) -> ResourceContent:
        """读取排除因子列表"""
        excluded = self.factor_service.get_excluded_factors()
        return ResourceContent(
            uri="factor://excluded",
            mime_type="application/json",
            text=json.dumps(excluded, ensure_ascii=False, indent=2),
        )

    async def _read_top_scored(self) -> ResourceContent:
        """读取高分因子列表"""
        factors, _ = self.factor_service.list_factors(
            score_filter="4.5+",
            order_by="llm_score",
            order_desc=True,
            page=1,
            page_size=20,
        )

        result = []
        for f in factors:
            formula = f.formula or ""
            result.append({
                "filename": f.filename,
                "style": f.style,
                "llm_score": f.llm_score,
                "formula": formula[:100] + "..." if len(formula) > 100 else formula,
            })

        return ResourceContent(
            uri="factor://top-scored",
            mime_type="application/json",
            text=json.dumps(result, ensure_ascii=False, indent=2),
        )

    async def _read_passed(self) -> ResourceContent:
        """读取验证通过的因子列表"""
        factors, _ = self.factor_service.list_factors(
            verify_filter="通过",
            page=1,
            page_size=100,
        )

        result = []
        for f in factors:
            result.append({
                "filename": f.filename,
                "style": f.style,
                "llm_score": f.llm_score,
                "verify_note": f.verify_note,
            })

        return ResourceContent(
            uri="factor://passed",
            mime_type="application/json",
            text=json.dumps(result, ensure_ascii=False, indent=2),
        )

    async def _read_failed(self) -> ResourceContent:
        """读取废弃（失败研究）的因子列表"""
        factors, _ = self.factor_service.list_factors(
            verify_filter="废弃",
            page=1,
            page_size=100,
        )

        result = []
        for f in factors:
            result.append({
                "filename": f.filename,
                "style": f.style,
                "llm_score": f.llm_score,
                "verify_note": f.verify_note,
            })

        return ResourceContent(
            uri="factor://failed",
            mime_type="application/json",
            text=json.dumps(result, ensure_ascii=False, indent=2),
        )

    async def _read_factor_detail(self, filename: str) -> ResourceContent | None:
        """读取因子详情"""
        factor = self.factor_service.get_factor(filename)
        if factor is None:
            return None

        # 验证状态映射
        status_map = {0: "未验证", 1: "通过", 2: "废弃"}
        data = {
            "filename": factor.filename,
            "uuid": factor.uuid,
            "style": factor.style,
            "formula": factor.formula,
            "input_data": factor.input_data,
            "value_range": factor.value_range,
            "description": factor.description,
            "analysis": factor.analysis,
            "llm_score": factor.llm_score,
            "ic": factor.ic,
            "rank_ic": factor.rank_ic,
            "verification_status": status_map.get(factor.verification_status, "未验证"),
            "verify_note": factor.verify_note,
            "code_path": factor.code_path,
            "created_at": str(factor.created_at) if factor.created_at else None,
        }

        return ResourceContent(
            uri=f"factor://factor/{filename}",
            mime_type="application/json",
            text=json.dumps(data, ensure_ascii=False, indent=2),
        )

    async def _read_factor_code(self, filename: str) -> ResourceContent | None:
        """读取因子代码"""
        factor = self.factor_service.get_factor(filename)
        if factor is None:
            return None

        code = factor.code_content or "# 暂无代码内容"

        return ResourceContent(
            uri=f"factor://factor/{filename}/code",
            mime_type="text/x-python",
            text=code,
        )
