"""Experience-related Pydantic schemas.

定义经验知识库 API 的请求和响应 Schema。
简化版本: 移除层级/状态/置信度，以标签为核心管理。
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ==================== 枚举定义 ====================


class SourceTypeEnum(str, Enum):
    """来源类型枚举"""
    RESEARCH = "research"        # 研究会话
    BACKTEST = "backtest"        # 回测结果
    LIVE_TRADE = "live_trade"    # 实盘交易
    EXTERNAL = "external"        # 外部输入
    MANUAL = "manual"            # 手动录入


class EntityTypeEnum(str, Enum):
    """关联实体类型枚举"""
    FACTOR = "factor"            # 因子
    STRATEGY = "strategy"        # 策略
    NOTE = "note"                # 笔记
    RESEARCH = "research"        # 研报
    EXPERIENCE = "experience"    # 经验（父级经验）


# ==================== 内容 Schema ====================


class ExperienceContentSchema(BaseModel):
    """
    经验的核心内容（PARL 框架）

    Attributes:
        problem: 面临的问题或挑战
        approach: 采用的方法或策略
        result: 得到的结果
        lesson: 总结的教训或规律
    """
    problem: str = Field("", description="面临的问题或挑战")
    approach: str = Field("", description="采用的方法或策略")
    result: str = Field("", description="得到的结果")
    lesson: str = Field("", description="总结的教训或规律")


class ExperienceContextSchema(BaseModel):
    """
    经验的上下文信息

    Attributes:
        market_regime: 市场状态（牛市/熊市/震荡）
        factor_styles: 相关的因子风格
        time_horizon: 适用的时间范围（短期/中期/长期）
        asset_class: 资产类别（BTC/ETH/山寨币/全市场）
        tags: 自定义标签
    """
    market_regime: str = Field("", description="市场状态（牛市/熊市/震荡）")
    factor_styles: List[str] = Field(default_factory=list, description="相关的因子风格")
    time_horizon: str = Field("", description="适用的时间范围（短期/中期/长期）")
    asset_class: str = Field("", description="资产类别（BTC/ETH/山寨币/全市场）")
    tags: List[str] = Field(default_factory=list, description="自定义标签")


# ==================== 请求 Schema ====================


class ExperienceCreateRequest(BaseModel):
    """创建经验请求"""
    title: str = Field(..., description="经验标题", min_length=1, max_length=500)
    content: ExperienceContentSchema = Field(
        default_factory=ExperienceContentSchema,
        description="PARL 内容"
    )
    context: Optional[ExperienceContextSchema] = Field(
        None,
        description="上下文信息"
    )
    source_type: SourceTypeEnum = Field(
        SourceTypeEnum.MANUAL,
        description="来源类型"
    )
    source_ref: str = Field("", description="来源引用")


class ExperienceUpdateRequest(BaseModel):
    """更新经验请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[ExperienceContentSchema] = None
    context: Optional[ExperienceContextSchema] = None


class ExperienceQueryRequest(BaseModel):
    """语义查询经验请求"""
    query: str = Field(..., description="自然语言查询", min_length=1)
    tags: Optional[List[str]] = Field(None, description="过滤标签")
    market_regime: Optional[str] = Field(None, description="过滤市场环境")
    factor_styles: Optional[List[str]] = Field(None, description="过滤因子风格")
    top_k: int = Field(5, ge=1, le=50, description="返回数量")


class ExperienceLinkRequest(BaseModel):
    """关联经验请求"""
    entity_type: EntityTypeEnum = Field(..., description="实体类型")
    entity_id: str = Field(..., description="实体 ID")
    relation: str = Field("related", description="关系类型（related/derived_from/applied_to）")


# ==================== 响应 Schema ====================


class ExperienceLinkSchema(BaseModel):
    """经验关联 Schema"""
    id: Optional[int] = None
    experience_id: Optional[int] = None
    experience_uuid: str = ""
    entity_type: str = ""
    entity_id: str = ""
    relation: str = "related"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExperienceResponse(BaseModel):
    """经验响应"""
    id: Optional[int] = None
    uuid: str = ""
    title: str = ""
    content: ExperienceContentSchema = Field(default_factory=ExperienceContentSchema)
    context: ExperienceContextSchema = Field(default_factory=ExperienceContextSchema)
    source_type: str = SourceTypeEnum.MANUAL.value
    source_ref: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExperienceListParams(BaseModel):
    """经验列表查询参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    tags: Optional[str] = Field(None, description="标签筛选（逗号分隔）")
    source_type: Optional[SourceTypeEnum] = Field(None, description="来源筛选")
    market_regime: Optional[str] = Field(None, description="市场环境筛选")
    factor_styles: Optional[str] = Field(None, description="因子风格筛选（逗号分隔）")
    created_after: Optional[str] = Field(None, description="创建时间起始（ISO 格式）")
    created_before: Optional[str] = Field(None, description="创建时间截止（ISO 格式）")
    updated_after: Optional[str] = Field(None, description="更新时间起始（ISO 格式）")
    updated_before: Optional[str] = Field(None, description="更新时间截止（ISO 格式）")
    order_by: str = Field("updated_at", description="排序字段")
    order_desc: bool = Field(True, description="降序排序")


class ExperienceStatsResponse(BaseModel):
    """经验统计信息"""
    total: int = Field(..., description="经验总数")
    tags: List[str] = Field(default_factory=list, description="所有标签")
    tags_count: int = Field(0, description="标签数量")


class ExperienceLinkResponse(BaseModel):
    """关联经验响应"""
    link_id: int
    experience_id: int
    entity_type: str
    entity_id: str
