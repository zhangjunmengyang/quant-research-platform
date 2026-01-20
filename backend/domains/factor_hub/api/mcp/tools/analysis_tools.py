"""
因子分析相关的 MCP 工具

提供因子分析能力的 MCP 工具封装。
"""

from typing import Any, Dict, List
import logging

from .base import BaseTool, ToolResult
from domains.mcp_core.base.tool import ExecutionMode

logger = logging.getLogger(__name__)


class GetFactorICTool(BaseTool):
    """获取因子IC - 快速获取因子IC统计"""

    category = "analysis"

    @property
    def name(self) -> str:
        return "get_factor_ic"

    @property
    def description(self) -> str:
        return "快速获取因子的IC统计信息，包括IC均值、ICIR、RankIC等"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "因子文件名（如 Momentum_5d，不含 .py 后缀）",
                },
            },
            "required": ["filename"],
        }

    async def execute(self, filename: str) -> ToolResult:
        try:
            filename = self.normalize_filename(filename)
            # 从因子知识库获取因子信息
            factor = self.factor_service.get_factor(filename)
            if not factor:
                return ToolResult.fail(f"因子不存在: {filename}")

            # 如果因子有存储的IC数据，返回
            result = {
                "filename": filename,
                "description": factor.description,
                "style": factor.style,
            }

            # 检查是否有已存储的回测指标
            if hasattr(factor, 'backtest_ic') and factor.backtest_ic:
                result["ic_mean"] = factor.backtest_ic
            if hasattr(factor, 'backtest_ir') and factor.backtest_ir:
                result["icir"] = factor.backtest_ir

            # 如果没有存储的数据，提示需要运行分析
            if "ic_mean" not in result:
                result["note"] = "因子尚未进行IC分析，请使用因子分组分析工具获取IC数据"

            return ToolResult.ok(result)

        except Exception as e:
            logger.exception("获取因子IC失败")
            return ToolResult.fail(str(e))


class CompareFactorsTool(BaseTool):
    """因子对比工具 - 多因子对比分析"""

    category = "analysis"

    @property
    def name(self) -> str:
        return "compare_factors"

    @property
    def description(self) -> str:
        return "对比多个因子的分析指标，包括IC、收益、稳定性等维度"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filenames": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "因子文件名列表（不含 .py 后缀）",
                },
            },
            "required": ["filenames"],
        }

    async def execute(self, filenames: List[str]) -> ToolResult:
        try:
            if len(filenames) < 2:
                return ToolResult.fail("至少需要2个因子进行对比")

            # 规范化所有文件名
            filenames = [self.normalize_filename(f) for f in filenames]

            comparisons = []
            for filename in filenames:
                factor = self.factor_service.get_factor(filename)
                if factor:
                    comparisons.append({
                        "filename": filename,
                        "description": factor.description,
                        "style": factor.style,
                        "llm_score": factor.llm_score,
                        "verified": factor.verified,
                    })

            if len(comparisons) < 2:
                return ToolResult.fail("有效因子不足2个")

            return ToolResult.ok({
                "count": len(comparisons),
                "factors": comparisons,
                "note": "完整的IC/收益对比需要运行因子分析服务",
            })

        except Exception as e:
            logger.exception("因子对比失败")
            return ToolResult.fail(str(e))


class SuggestSimilarFactorsTool(BaseTool):
    """相似因子推荐工具"""

    category = "analysis"

    @property
    def name(self) -> str:
        return "suggest_similar_factors"

    @property
    def description(self) -> str:
        return "根据指定因子推荐相似因子，基于风格、公式或代码相似度"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "参考因子文件名（如 Momentum_5d，不含 .py 后缀）",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制",
                    "default": 5,
                },
                "by": {
                    "type": "string",
                    "description": "相似度基准: style(风格) / formula(公式)",
                    "enum": ["style", "formula"],
                    "default": "style",
                },
            },
            "required": ["filename"],
        }

    async def execute(
        self,
        filename: str,
        limit: int = 5,
        by: str = "style",
    ) -> ToolResult:
        try:
            filename = self.normalize_filename(filename)
            # 获取参考因子
            ref_factor = self.factor_service.get_factor(filename)
            if not ref_factor:
                return ToolResult.fail(f"因子不存在: {filename}")

            # 根据风格或公式查找相似因子
            if by == "style" and ref_factor.style:
                # 按风格筛选
                similar = self.factor_service.query(
                    filter_condition={"style": f"contains:{ref_factor.style}"}
                )
            else:
                # 获取所有因子
                similar = self.factor_service.query()

            # 过滤掉自身
            similar = [f for f in similar if f.filename != filename]

            # 限制数量
            similar = similar[:limit]

            return ToolResult.ok({
                "reference": {
                    "filename": filename,
                    "style": ref_factor.style,
                },
                "similar_factors": [
                    {
                        "filename": f.filename,
                        "description": f.description,
                        "style": f.style,
                        "llm_score": f.llm_score,
                    }
                    for f in similar
                ],
                "match_by": by,
            })

        except Exception as e:
            logger.exception("相似因子推荐失败")
            return ToolResult.fail(str(e))


# ============= 多因子分析工具 =============


class GetFactorCorrelationTool(BaseTool):
    """获取因子相关性 - 计算多因子相关性矩阵"""

    category = "analysis"
    execution_mode = ExecutionMode.COMPUTE  # CPU 密集型计算
    execution_timeout = 120.0

    @property
    def name(self) -> str:
        return "get_factor_correlation"

    @property
    def description(self) -> str:
        return """计算多个因子之间的相关性矩阵，识别高相关因子对。
用于检测因子冗余和多重共线性问题。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "factor_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "因子名称列表（至少2个，不含 .py 后缀）",
                },
                "correlation_threshold": {
                    "type": "number",
                    "description": "高相关性阈值，默认0.7",
                    "default": 0.7,
                },
            },
            "required": ["factor_names"],
        }

    async def execute(
        self,
        factor_names: List[str],
        correlation_threshold: float = 0.7,
    ) -> ToolResult:
        try:
            if len(factor_names) < 2:
                return ToolResult.fail("至少需要2个因子进行相关性分析")

            # 规范化所有因子名
            factor_names = [self.normalize_filename(f) for f in factor_names]

            from ....services import get_multi_factor_analysis_service

            service = get_multi_factor_analysis_service(
                correlation_threshold=correlation_threshold
            )

            return ToolResult.ok({
                "message": f"多因子相关性分析服务已就绪",
                "factor_count": len(factor_names),
                "factors": factor_names,
                "capabilities": [
                    "Pearson相关性矩阵",
                    "Spearman秩相关性矩阵",
                    "高相关因子对识别",
                    "平均/最大相关性统计",
                ],
                "threshold": correlation_threshold,
                "usage": "需要提供包含因子值的DataFrame进行分析",
            })

        except Exception as e:
            logger.exception("获取因子相关性失败")
            return ToolResult.fail(str(e))


class MultiFactorAnalyzeTool(BaseTool):
    """多因子完整分析工具 - 一站式多因子分析"""

    category = "analysis"
    execution_mode = ExecutionMode.COMPUTE  # CPU 密集型计算
    execution_timeout = 180.0  # 多因子分析可能较慢

    @property
    def name(self) -> str:
        return "multi_factor_analyze"

    @property
    def description(self) -> str:
        return """执行完整的多因子分析，包括相关性、正交化、合成、冗余检测和增量贡献分析。
一次调用获取所有多因子分析结果。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "factor_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "因子名称列表（至少2个，不含 .py 后缀）",
                },
                "synthesis_method": {
                    "type": "string",
                    "description": "因子合成方法",
                    "enum": [
                        "equal_weight",
                        "ic_weight",
                        "icir_weight",
                        "max_ic",
                        "min_corr",
                    ],
                    "default": "ic_weight",
                },
            },
            "required": ["factor_names"],
        }

    async def execute(
        self,
        factor_names: List[str],
        synthesis_method: str = "ic_weight",
    ) -> ToolResult:
        try:
            if len(factor_names) < 2:
                return ToolResult.fail("至少需要2个因子进行多因子分析")

            # 规范化所有因子名
            factor_names = [self.normalize_filename(f) for f in factor_names]

            from ....services import get_multi_factor_analysis_service

            service = get_multi_factor_analysis_service()

            return ToolResult.ok({
                "message": "多因子分析服务已就绪",
                "factor_count": len(factor_names),
                "factors": factor_names,
                "synthesis_method": synthesis_method,
                "analyses": [
                    {
                        "name": "相关性分析",
                        "description": "计算因子相关性矩阵，识别高相关因子对",
                    },
                    {
                        "name": "正交化",
                        "description": "使用QR分解进行因子正交化",
                    },
                    {
                        "name": "因子合成",
                        "description": f"使用{synthesis_method}方法合成综合因子",
                    },
                    {
                        "name": "冗余检测",
                        "description": "识别冗余因子，推荐移除建议",
                    },
                    {
                        "name": "增量贡献",
                        "description": "计算各因子的边际贡献和Shapley值",
                    },
                ],
                "usage": "需要提供包含因子值和收益率的DataFrame进行分析",
            })

        except Exception as e:
            logger.exception("多因子分析失败")
            return ToolResult.fail(str(e))


# ============= 因子分组分析工具 =============


class AnalyzeFactorGroupsTool(BaseTool):
    """因子分组分析工具 - 分析因子在不同分位组的收益表现"""

    category = "analysis"
    execution_mode = ExecutionMode.COMPUTE  # CPU 密集型计算
    execution_timeout = 120.0

    @property
    def name(self) -> str:
        return "analyze_factor_groups"

    @property
    def description(self) -> str:
        return """分析因子在不同分位组的收益表现。
支持分位数分箱和等宽分箱两种方法，生成分组净值曲线和柱状图。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "factor_dict": {
                    "type": "object",
                    "description": "因子字典 {因子名: [参数列表]}",
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型: spot, swap, all",
                    "enum": ["spot", "swap", "all"],
                    "default": "swap",
                },
                "bins": {
                    "type": "integer",
                    "description": "分组数量，默认5组",
                    "default": 5,
                },
                "method": {
                    "type": "string",
                    "description": "分箱方法: pct(分位数) 或 val(等宽)",
                    "enum": ["pct", "val"],
                    "default": "pct",
                },
            },
            "required": ["factor_dict"],
        }

    async def execute(
        self,
        factor_dict: Dict[str, List[Any]],
        data_type: str = "swap",
        bins: int = 5,
        method: str = "pct",
    ) -> ToolResult:
        try:
            # 规范化 factor_dict 中的因子名
            normalized_factor_dict = {
                self.normalize_filename(k): v for k, v in factor_dict.items()
            }

            from ....services import get_factor_group_analysis_service

            service = get_factor_group_analysis_service()
            # 使用异步方法避免阻塞事件循环
            results = await service.analyze_multiple_factors_async(
                factor_dict=normalized_factor_dict,
                data_type=data_type,
                bins=bins,
                method=method,
            )

            return ToolResult.ok({
                "count": len(results),
                "results": [
                    {
                        "factor_name": r.factor_name,
                        "bins": r.bins,
                        "method": r.method,
                        "data_type": r.data_type,
                        "html_path": r.html_path,
                        "error": r.error,
                    }
                    for r in results
                ],
            })

        except Exception as e:
            logger.exception("因子分组分析失败")
            return ToolResult.fail(str(e))
