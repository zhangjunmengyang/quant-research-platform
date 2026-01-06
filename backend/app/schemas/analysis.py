"""
分析 API Schema

定义分析相关的请求和响应模型。
"""

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


# ============= 参数搜索 =============

class ParamSearchRequest(BaseModel):
    """参数搜索请求"""
    name: str = Field(..., description="搜索任务名称")
    batch_params: Dict[str, List[Any]] = Field(
        ..., description="参数搜索范围 {参数名: [参数值列表]}"
    )
    strategy_template: Dict[str, Any] = Field(
        ..., description="策略模板配置"
    )
    max_workers: int = Field(default=4, description="最大并行数")


class ParamSearchResponse(BaseModel):
    """参数搜索响应"""
    name: str
    total_combinations: int
    status: str
    output_path: Optional[str] = None
    error: Optional[str] = None


# ============= 参数分析 =============

class ParamAnalysisRequest(BaseModel):
    """参数分析请求"""
    trav_name: str = Field(..., description="遍历结果名称")
    batch_params: Dict[str, List[Any]] = Field(
        ..., description="参数范围"
    )
    param_x: str = Field(..., description="X轴参数")
    param_y: Optional[str] = Field(default=None, description="Y轴参数，为空则单参数分析")
    limit_dict: Optional[Dict[str, List[Any]]] = Field(
        default=None, description="固定参数条件"
    )
    indicator: str = Field(
        default="annual_return",
        description="评价指标"
    )


class ParamAnalysisResponse(BaseModel):
    """参数分析响应"""
    name: str
    analysis_type: str
    indicator: str
    html_path: Optional[str] = None
    error: Optional[str] = None


# ============= 因子分组分析 =============

class FactorGroupAnalysisRequest(BaseModel):
    """因子分组分析请求"""
    factor_dict: Dict[str, List[Any]] = Field(
        ..., description="因子字典 {因子名: [参数列表]}"
    )
    filter_list: Optional[List[tuple]] = Field(
        default=None, description="过滤条件列表"
    )
    data_type: Literal['spot', 'swap', 'all'] = Field(
        default='swap', description="数据类型"
    )
    bins: int = Field(default=5, ge=2, le=20, description="分组数量")
    method: Literal['pct', 'val'] = Field(
        default='pct', description="分箱方法: pct(分位数) 或 val(等宽)"
    )


class GroupCurvePoint(BaseModel):
    """分组净值曲线数据点"""
    date: str
    values: Dict[str, float]  # {group_name: nav_value}


class GroupBarData(BaseModel):
    """分组柱状图数据"""
    group: str
    nav: float
    label: str = ""  # Min Value / Max Value


class FactorGroupAnalysisResponse(BaseModel):
    """因子分组分析响应"""
    factor_name: str
    bins: int
    method: str
    data_type: str
    labels: List[str] = []  # 分组标签列表
    curve_data: List[GroupCurvePoint] = []  # 净值曲线数据
    bar_data: List[GroupBarData] = []  # 柱状图数据
    error: Optional[str] = None


# ============= 回测实盘对比 =============

class BacktestComparisonRequest(BaseModel):
    """回测实盘对比请求"""
    backtest_name: str = Field(..., description="回测策略名称")
    start_time: str = Field(..., description="对比开始时间")
    end_time: str = Field(..., description="对比结束时间")


class BacktestComparisonResponse(BaseModel):
    """回测实盘对比响应"""
    backtest_name: str
    start_time: str
    end_time: str
    coin_selection_similarity: Optional[float] = None
    html_path: Optional[str] = None
    error: Optional[str] = None


class FactorComparisonRequest(BaseModel):
    """因子值对比请求"""
    backtest_name: str = Field(..., description="回测策略名称")
    coin: str = Field(..., description="币种名称")
    factor_names: Optional[List[str]] = Field(
        default=None, description="因子名称列表，为空则自动检测"
    )


class FactorComparisonResponse(BaseModel):
    """因子值对比响应"""
    backtest_name: str
    coin: str
    factors: List[str] = []
    html_path: Optional[str] = None
    error: Optional[str] = None


# ============= 策略对比 =============

class StrategyComparisonRequest(BaseModel):
    """策略对比请求"""
    strategy_list: List[str] = Field(..., min_length=2, description="策略名称列表")
    comparison_type: Literal['coin_similarity', 'equity_correlation'] = Field(
        ..., description="对比类型"
    )


class CoinSimilarityResponse(BaseModel):
    """选币相似度响应"""
    strategies: List[str]
    html_path: Optional[str] = None
    error: Optional[str] = None


class EquityCorrelationResponse(BaseModel):
    """资金曲线相关性响应"""
    strategies: List[str]
    html_path: Optional[str] = None
    error: Optional[str] = None


# ============= 报告获取 =============

class ReportResponse(BaseModel):
    """报告响应"""
    path: str
    exists: bool
    content_type: str = "text/html"
