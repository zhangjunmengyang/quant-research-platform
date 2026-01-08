"""Experience-related Pydantic schemas.

定义经验知识库 API 的请求和响应 Schema。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 枚举定义 ====================


class ExperienceLevelEnum(str, Enum):
    """经验层级枚举"""
    STRATEGIC = "strategic"      # 战略级: 长期有效的研究原则
    TACTICAL = "tactical"        # 战术级: 特定场景下的研究结论
    OPERATIONAL = "operational"  # 操作级: 具体的研究记录


class ExperienceStatusEnum(str, Enum):
    """经验状态枚举"""
    DRAFT = "draft"              # 草稿: 新记录的经验，待验证
    VALIDATED = "validated"      # 已验证: 经过后续研究验证
    DEPRECATED = "deprecated"    # 已废弃: 被证伪或已过时


class ExperienceCategoryEnum(str, Enum):
    """经验分类枚举"""
    # 战略级分类
    MARKET_REGIME_PRINCIPLE = "market_regime_principle"      # 市场环境原则
    FACTOR_DESIGN_PRINCIPLE = "factor_design_principle"      # 因子设计原则
    RISK_MANAGEMENT_PRINCIPLE = "risk_management_principle"  # 风险管理原则

    # 战术级分类
    FACTOR_PERFORMANCE = "factor_performance"          # 因子表现结论
    STRATEGY_OPTIMIZATION = "strategy_optimization"    # 策略优化结论
    PARAM_SENSITIVITY = "param_sensitivity"            # 参数敏感性结论

    # 操作级分类
    SUCCESSFUL_EXPERIMENT = "successful_experiment"    # 成功实验
    FAILED_EXPERIMENT = "failed_experiment"            # 失败实验
    RESEARCH_OBSERVATION = "research_observation"      # 研究观察


class SourceTypeEnum(str, Enum):
    """来源类型枚举"""
    RESEARCH = "research"        # 研究会话
    BACKTEST = "backtest"        # 回测结果
    LIVE_TRADE = "live_trade"    # 实盘交易
    EXTERNAL = "external"        # 外部输入
    MANUAL = "manual"            # 手动录入
    CURATED = "curated"          # 提炼生成


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
    experience_level: ExperienceLevelEnum = Field(
        ExperienceLevelEnum.OPERATIONAL,
        description="经验层级"
    )
    category: str = Field("", description="分类")
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
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="初始置信度（0-1）"
    )


class ExperienceUpdateRequest(BaseModel):
    """更新经验请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    experience_level: Optional[ExperienceLevelEnum] = None
    category: Optional[str] = None
    content: Optional[ExperienceContentSchema] = None
    context: Optional[ExperienceContextSchema] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class ExperienceQueryRequest(BaseModel):
    """语义查询经验请求"""
    query: str = Field(..., description="自然语言查询", min_length=1)
    experience_level: Optional[ExperienceLevelEnum] = Field(None, description="过滤层级")
    category: Optional[str] = Field(None, description="过滤分类")
    market_regime: Optional[str] = Field(None, description="过滤市场环境")
    factor_styles: Optional[List[str]] = Field(None, description="过滤因子风格")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0, description="最低置信度")
    include_deprecated: bool = Field(False, description="是否包含已废弃经验")
    top_k: int = Field(5, ge=1, le=50, description="返回数量")


class ExperienceValidateRequest(BaseModel):
    """验证经验请求"""
    validation_note: Optional[str] = Field(None, description="验证说明")
    confidence_delta: Optional[float] = Field(
        None,
        ge=0.0,
        le=0.5,
        description="置信度增量（默认使用系统配置）"
    )


class ExperienceDeprecateRequest(BaseModel):
    """废弃经验请求"""
    reason: str = Field(..., description="废弃原因", min_length=1)


class ExperienceLinkRequest(BaseModel):
    """关联经验请求"""
    entity_type: EntityTypeEnum = Field(..., description="实体类型")
    entity_id: str = Field(..., description="实体 ID")
    relation: str = Field("related", description="关系类型（related/derived_from/applied_to）")


class ExperienceCurateRequest(BaseModel):
    """提炼经验请求"""
    source_experience_ids: List[int] = Field(
        ...,
        min_length=2,
        description="源经验 ID 列表（至少两个）"
    )
    target_level: ExperienceLevelEnum = Field(..., description="目标层级")
    title: str = Field(..., description="新经验标题", min_length=1, max_length=500)
    content: ExperienceContentSchema = Field(..., description="PARL 内容")
    context: Optional[ExperienceContextSchema] = Field(None, description="上下文信息")


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
    experience_level: str = ExperienceLevelEnum.OPERATIONAL.value
    category: str = ""
    content: ExperienceContentSchema = Field(default_factory=ExperienceContentSchema)
    context: ExperienceContextSchema = Field(default_factory=ExperienceContextSchema)
    source_type: str = SourceTypeEnum.MANUAL.value
    source_ref: str = ""
    confidence: float = 0.5
    validation_count: int = 0
    last_validated: Optional[datetime] = None
    status: str = ExperienceStatusEnum.DRAFT.value
    deprecated_reason: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExperienceListParams(BaseModel):
    """经验列表查询参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    experience_level: Optional[ExperienceLevelEnum] = Field(None, description="层级筛选")
    category: Optional[str] = Field(None, description="分类筛选")
    status: Optional[ExperienceStatusEnum] = Field(None, description="状态筛选")
    source_type: Optional[SourceTypeEnum] = Field(None, description="来源筛选")
    market_regime: Optional[str] = Field(None, description="市场环境筛选")
    factor_styles: Optional[str] = Field(None, description="因子风格筛选（逗号分隔）")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0, description="最低置信度")
    include_deprecated: bool = Field(False, description="是否包含已废弃经验")
    order_by: str = Field("updated_at", description="排序字段")
    order_desc: bool = Field(True, description="降序排序")


class ExperienceStatsResponse(BaseModel):
    """经验统计信息"""
    total: int = Field(..., description="经验总数")
    by_status: Dict[str, int] = Field(default_factory=dict, description="按状态分布")
    by_level: Dict[str, int] = Field(default_factory=dict, description="按层级分布")
    categories: List[str] = Field(default_factory=list, description="所有分类")
    categories_count: int = Field(0, description="分类数量")


class ExperienceValidateResponse(BaseModel):
    """验证经验响应"""
    experience_id: int
    new_confidence: float
    validation_count: int


class ExperienceDeprecateResponse(BaseModel):
    """废弃经验响应"""
    experience_id: int
    status: str


class ExperienceLinkResponse(BaseModel):
    """关联经验响应"""
    link_id: int
    experience_id: int
    entity_type: str
    entity_id: str


class ExperienceCurateResponse(BaseModel):
    """提炼经验响应"""
    experience_id: int
    message: str
