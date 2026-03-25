"""A股因子AI评估模型"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ModuleScore(BaseModel):
    """单模块评估结果"""
    score: float  # 1.0-5.0
    analysis: str  # 分析文本


class FactorEvaluation(BaseModel):
    """因子完整评估结果"""
    factor_name: str
    factor_category: str = ""
    evaluated_at: float  # timestamp

    # 分模块评估 (each 1.0-5.0)
    logic: Optional[ModuleScore] = None       # 因子逻辑评估
    backtest: Optional[ModuleScore] = None    # 回测表现评估
    effectiveness: Optional[ModuleScore] = None  # 因子有效性评估(IC)

    # 综合评估
    overall_score: Optional[float] = None     # 综合评分 (1.0-5.0)
    overall_summary: Optional[str] = None     # 综合总结
    tags: List[str] = []                       # AI标签
    verdict: str = ""                          # "推荐"/"观望"/"弃用"

    # 输入数据快照 (保留用于回溯)
    backtest_snapshot: Optional[Dict[str, Any]] = None
    ic_snapshot: Optional[Dict[str, Any]] = None


class EvaluationRequest(BaseModel):
    """评估请求"""
    factor_name: str
    factor_code: Optional[str] = None       # 因子源代码 (可选,从缓存获取)
    factor_category: str = ""
    factor_description: str = ""

    # 回测数据 (从回测结果中获取)
    backtest_result: Optional[Dict[str, Any]] = None

    # IC分析数据 (从分析结果中获取)
    ic_data: Optional[Dict[str, Any]] = None


class EvaluationListItem(BaseModel):
    """评估列表项（轻量）"""
    factor_name: str
    factor_category: str = ""
    evaluated_at: float
    overall_score: Optional[float] = None
    verdict: str = ""
    tags: List[str] = []
