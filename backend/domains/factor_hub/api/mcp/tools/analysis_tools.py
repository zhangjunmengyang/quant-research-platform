"""
因子分析相关的 MCP 工具

提供因子分析能力的 MCP 工具封装。
"""

from typing import Any, Dict, List, Optional
import logging

from .base import BaseTool, ToolResult
from domains.mcp_core.base.tool import ExecutionMode

logger = logging.getLogger(__name__)


class AnalyzeFactorTool(BaseTool):
    """因子分析工具 - 执行单因子深度分析"""

    category = "analysis"
    execution_mode = ExecutionMode.COMPUTE  # CPU 密集型计算
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "analyze_factor"

    @property
    def description(self) -> str:
        return """执行单因子深度分析，包括IC分析、分组收益、分布特征和稳定性分析。
需要提供因子数据（包含因子值和收益率列）。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "factor_name": {
                    "type": "string",
                    "description": "因子名称",
                },
                "param": {
                    "type": ["string", "integer"],
                    "description": "因子参数",
                },
                "n_groups": {
                    "type": "integer",
                    "description": "分组数量，默认5组",
                    "default": 5,
                },
            },
            "required": ["factor_name"],
        }

    async def execute(
        self,
        factor_name: str,
        param: Optional[str] = None,
        n_groups: int = 5,
    ) -> ToolResult:
        try:
            from ....services import get_factor_analysis_service

            service = get_factor_analysis_service(n_groups=n_groups)

            # 构建因子列名
            factor_col = f"{factor_name}_{param}" if param else factor_name

            # 获取因子数据（需要从数据层获取）
            # 这里返回分析能力说明，实际使用时需要传入数据
            return ToolResult.ok({
                "message": f"因子分析服务已就绪，可分析因子: {factor_col}",
                "capabilities": [
                    "IC分析（IC均值、ICIR、RankIC）",
                    "分组收益分析（多空收益、单调性）",
                    "分布分析（偏度、峰度、正态性）",
                    "稳定性分析（滚动IC、IC衰减、半衰期）",
                ],
                "usage": "需要提供包含因子值和收益率的DataFrame进行分析",
            })

        except Exception as e:
            logger.exception("因子分析失败")
            return ToolResult.fail(str(e))


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
                    "description": "因子文件名",
                },
            },
            "required": ["filename"],
        }

    async def execute(self, filename: str) -> ToolResult:
        try:
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
                result["note"] = "因子尚未进行IC分析，请使用 analyze_factor 工具执行分析"

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
                    "description": "因子文件名列表",
                },
            },
            "required": ["filenames"],
        }

    async def execute(self, filenames: List[str]) -> ToolResult:
        try:
            if len(filenames) < 2:
                return ToolResult.fail("至少需要2个因子进行对比")

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
                    "description": "参考因子文件名",
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
                    "description": "因子名称列表（至少2个）",
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


class DetectCollinearityTool(BaseTool):
    """共线性检测工具 - 检测因子多重共线性"""

    category = "analysis"
    execution_mode = ExecutionMode.COMPUTE  # CPU 密集型计算
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "detect_collinearity"

    @property
    def description(self) -> str:
        return """检测多个因子之间的多重共线性问题。
使用VIF（方差膨胀因子）和条件数进行诊断。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "factor_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "因子名称列表",
                },
                "vif_threshold": {
                    "type": "number",
                    "description": "VIF阈值，默认10（超过此值认为存在共线性）",
                    "default": 10.0,
                },
            },
            "required": ["factor_names"],
        }

    async def execute(
        self,
        factor_names: List[str],
        vif_threshold: float = 10.0,
    ) -> ToolResult:
        try:
            from ....services import get_multi_factor_analysis_service

            service = get_multi_factor_analysis_service(vif_threshold=vif_threshold)

            return ToolResult.ok({
                "message": "共线性检测服务已就绪",
                "factor_count": len(factor_names),
                "capabilities": [
                    "VIF（方差膨胀因子）计算",
                    "条件数分析",
                    "特征值诊断",
                    "共线性因子识别",
                ],
                "vif_threshold": vif_threshold,
                "interpretation": {
                    "vif_1": "无共线性",
                    "vif_1_5": "轻微共线性",
                    "vif_5_10": "中度共线性",
                    "vif_>10": "严重共线性",
                },
            })

        except Exception as e:
            logger.exception("共线性检测失败")
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
        return """执行完整的多因子分析，包括相关性、共线性、正交化、合成、冗余检测和增量贡献分析。
一次调用获取所有多因子分析结果。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "factor_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "因子名称列表（至少2个）",
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
                        "name": "共线性检测",
                        "description": "使用VIF和条件数检测多重共线性",
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
            from ....services import get_factor_group_analysis_service

            service = get_factor_group_analysis_service()
            # 使用异步方法避免阻塞事件循环
            results = await service.analyze_multiple_factors_async(
                factor_dict=factor_dict,
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
