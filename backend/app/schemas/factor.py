"""Factor-related Pydantic schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class FactorTypeEnum(str, Enum):
    """因子类型枚举"""
    TIME_SERIES = "time_series"
    CROSS_SECTION = "cross_section"


class FactorBase(BaseModel):
    """Base factor fields."""

    filename: str = Field(..., description="因子文件名")
    style: Optional[str] = Field(None, description="因子风格")
    formula: Optional[str] = Field(None, description="核心公式")
    input_data: Optional[str] = Field(None, description="输入数据字段")
    value_range: Optional[str] = Field(None, description="值域范围")
    description: Optional[str] = Field(None, description="刻画特征")


class Factor(FactorBase):
    """Complete factor model for API responses."""

    factor_type: FactorTypeEnum = Field(
        FactorTypeEnum.TIME_SERIES,
        description="因子类型（time_series=时序, cross_section=截面）"
    )
    uuid: Optional[str] = None
    analysis: Optional[str] = None
    code_path: Optional[str] = None
    code_content: Optional[str] = None

    # Scores
    llm_score: Optional[float] = None
    code_complexity: Optional[float] = None

    # Performance metrics
    ic: Optional[float] = None
    rank_ic: Optional[float] = None
    backtest_sharpe: Optional[float] = None
    backtest_ic: Optional[float] = None
    backtest_ir: Optional[float] = None
    turnover: Optional[float] = None
    decay: Optional[int] = None
    last_backtest_date: Optional[str] = None

    # Classification
    market_regime: Optional[str] = None
    best_holding_period: Optional[int] = None
    tags: Optional[str] = Field(None, description="标签（英文逗号分隔）")

    # Status
    verification_status: int = Field(0, description="验证状态（0=未验证, 1=通过, 2=废弃）")
    verify_note: Optional[str] = Field(None, description="验证备注")

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 参数分析结果 (JSON 字符串)
    param_analysis: Optional[str] = Field(None, description="参数分析结果 JSON")

    class Config:
        from_attributes = True


class FactorUpdate(BaseModel):
    """Factor update request."""

    style: Optional[str] = None
    formula: Optional[str] = None
    input_data: Optional[str] = None
    value_range: Optional[str] = None
    description: Optional[str] = None
    analysis: Optional[str] = None
    llm_score: Optional[float] = None
    verify_note: Optional[str] = None
    market_regime: Optional[str] = None
    best_holding_period: Optional[int] = None
    tags: Optional[str] = None


class FactorListRequest(BaseModel):
    """Factor list query parameters."""

    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(50, ge=1, le=300, description="每页数量")
    search: Optional[str] = Field(None, description="搜索关键词")
    style: Optional[str] = Field(None, description="风格筛选")
    factor_type: Optional[FactorTypeEnum] = Field(None, description="因子类型筛选")
    score_min: Optional[float] = Field(None, ge=0, le=5, description="最低评分")
    score_max: Optional[float] = Field(None, ge=0, le=5, description="最高评分")
    verification_status: Optional[int] = Field(None, description="验证状态筛选（0=未验证, 1=通过, 2=废弃）")
    order_by: str = Field("created_at", description="排序字段")
    order_desc: bool = Field(True, description="降序排序")


class FactorStats(BaseModel):
    """Factor statistics."""

    total: int = Field(..., description="有效因子总数（不含已排除）")
    excluded: int = Field(0, description="已排除因子数量")
    scored: int = Field(..., description="已评分数量")
    passed: int = Field(..., description="验证通过数量")
    failed: int = Field(0, description="废弃（失败研究）数量")
    avg_score: Optional[float] = Field(None, description="平均评分")
    style_distribution: Dict[str, int] = Field(default_factory=dict, description="风格分布")
    score_distribution: Dict[str, int] = Field(default_factory=dict, description="评分分布")
    factor_type_distribution: Dict[str, int] = Field(default_factory=dict, description="因子类型分布")


class FactorVerifyRequest(BaseModel):
    """Factor verify request."""

    note: Optional[str] = Field(None, description="验证备注")


class FactorCodeValidation(BaseModel):
    """Factor code validation result."""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class FactorCreateRequest(BaseModel):
    """Factor create request."""

    code_content: str = Field(..., description="因子代码内容")
    filename: Optional[str] = Field(None, description="因子文件名（可选）")
    style: Optional[str] = Field(None, description="风格分类")
    formula: Optional[str] = Field(None, description="核心公式")
    description: Optional[str] = Field(None, description="刻画特征")


class FactorCreateResponse(BaseModel):
    """Factor create response."""

    filename: str = Field(..., description="创建的因子文件名")
    message: str = Field(..., description="结果消息")
    auto_named: bool = Field(..., description="是否自动命名")


class FactorCodeUpdate(BaseModel):
    """Factor code update request."""

    code_content: str = Field(..., description="新的代码内容")


class ExcludedFilter(str, Enum):
    """排除状态筛选枚举"""
    ALL = "all"           # 全部（有效 + 已排除）
    ACTIVE = "active"     # 仅有效（默认）
    EXCLUDED = "excluded" # 仅已排除


class ExcludeRequest(BaseModel):
    """排除因子请求"""
    reason: Optional[str] = Field(None, description="排除原因")
