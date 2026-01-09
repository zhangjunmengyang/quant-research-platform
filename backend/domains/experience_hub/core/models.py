"""
经验知识库数据模型

定义经验、上下文、关联等核心数据结构。
基于 PARL 框架（Problem-Approach-Result-Lesson）存储结构化经验。
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ExperienceLevel(str, Enum):
    """经验层级"""
    STRATEGIC = "strategic"      # 战略级: 长期有效的研究原则
    TACTICAL = "tactical"        # 战术级: 特定场景下的研究结论
    OPERATIONAL = "operational"  # 操作级: 具体的研究记录


class ExperienceStatus(str, Enum):
    """经验状态"""
    DRAFT = "draft"              # 草稿: 新记录的经验，待验证
    VALIDATED = "validated"      # 已验证: 经过后续研究验证
    DEPRECATED = "deprecated"    # 已废弃: 被证伪或已过时


class ExperienceCategory(str, Enum):
    """经验分类"""
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


class SourceType(str, Enum):
    """来源类型"""
    RESEARCH = "research"        # 研究会话
    BACKTEST = "backtest"        # 回测结果
    LIVE_TRADE = "live_trade"    # 实盘交易
    EXTERNAL = "external"        # 外部输入
    MANUAL = "manual"            # 手动录入
    CURATED = "curated"          # 提炼生成


class EntityType(str, Enum):
    """关联实体类型"""
    FACTOR = "factor"            # 因子
    STRATEGY = "strategy"        # 策略
    NOTE = "note"                # 笔记
    RESEARCH = "research"        # 研报
    EXPERIENCE = "experience"    # 经验（父级经验）


@dataclass
class ExperienceContent:
    """
    经验的核心内容（PARL 框架）

    Attributes:
        problem: 面临的问题或挑战
        approach: 采用的方法或策略
        result: 得到的结果
        lesson: 总结的教训或规律
    """
    problem: str = ""
    approach: str = ""
    result: str = ""
    lesson: str = ""

    def to_dict(self) -> Dict[str, str]:
        """转换为字典"""
        return {
            'problem': self.problem,
            'approach': self.approach,
            'result': self.result,
            'lesson': self.lesson,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperienceContent':
        """从字典创建"""
        return cls(
            problem=data.get('problem', ''),
            approach=data.get('approach', ''),
            result=data.get('result', ''),
            lesson=data.get('lesson', ''),
        )

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> 'ExperienceContent':
        """从 JSON 字符串创建"""
        if not json_str:
            return cls()
        data = json.loads(json_str)
        return cls.from_dict(data)

    def to_embedding_text(self) -> str:
        """
        生成用于向量化的文本

        组合 problem 和 lesson，这两个字段最能代表经验的核心语义。
        """
        parts = []
        if self.problem:
            parts.append(f"问题: {self.problem}")
        if self.lesson:
            parts.append(f"教训: {self.lesson}")
        return "\n".join(parts)


@dataclass
class ExperienceContext:
    """
    经验的上下文信息

    Attributes:
        market_regime: 市场状态（牛市/熊市/震荡）
        factor_styles: 相关的因子风格
        time_horizon: 适用的时间范围（短期/中期/长期）
        asset_class: 资产类别（BTC/ETH/山寨币/全市场）
        tags: 自定义标签
    """
    market_regime: str = ""
    factor_styles: List[str] = field(default_factory=list)
    time_horizon: str = ""
    asset_class: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'market_regime': self.market_regime,
            'factor_styles': self.factor_styles,
            'time_horizon': self.time_horizon,
            'asset_class': self.asset_class,
            'tags': self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperienceContext':
        """从字典创建"""
        return cls(
            market_regime=data.get('market_regime', ''),
            factor_styles=data.get('factor_styles', []),
            time_horizon=data.get('time_horizon', ''),
            asset_class=data.get('asset_class', ''),
            tags=data.get('tags', []),
        )

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> 'ExperienceContext':
        """从 JSON 字符串创建"""
        if not json_str:
            return cls()
        data = json.loads(json_str)
        return cls.from_dict(data)

    @property
    def tags_str(self) -> str:
        """获取标签的逗号分隔字符串"""
        return ','.join(self.tags)

    @property
    def factor_styles_str(self) -> str:
        """获取因子风格的逗号分隔字符串"""
        return ','.join(self.factor_styles)


@dataclass
class Experience:
    """
    经验实体

    存储结构化的研究经验，支持语义检索和生命周期管理。
    """
    # === 基础信息 ===
    id: Optional[int] = None
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    experience_level: str = ExperienceLevel.OPERATIONAL.value
    category: str = ""

    # === 核心内容（PARL） ===
    content: ExperienceContent = field(default_factory=ExperienceContent)

    # === 上下文 ===
    context: ExperienceContext = field(default_factory=ExperienceContext)

    # === 来源追溯 ===
    source_type: str = SourceType.MANUAL.value
    source_ref: str = ""

    # === 置信度与验证 ===
    confidence: float = 0.5
    validation_count: int = 0
    last_validated: Optional[datetime] = None

    # === 生命周期 ===
    status: str = ExperienceStatus.DRAFT.value
    deprecated_reason: str = ""

    # === 时间戳 ===
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # === 语义检索 ===
    # embedding 存储在单独的向量存储中

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'experience_level': self.experience_level,
            'category': self.category,
            'content': self.content.to_dict() if isinstance(self.content, ExperienceContent) else self.content,
            'context': self.context.to_dict() if isinstance(self.context, ExperienceContext) else self.context,
            'source_type': self.source_type,
            'source_ref': self.source_ref,
            'confidence': self.confidence,
            'validation_count': self.validation_count,
            'last_validated': self.last_validated,
            'status': self.status,
            'deprecated_reason': self.deprecated_reason,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Experience':
        """从字典创建经验实例"""
        # 处理嵌套对象
        content = data.get('content')
        if isinstance(content, str):
            content = ExperienceContent.from_json(content)
        elif isinstance(content, dict):
            content = ExperienceContent.from_dict(content)
        elif content is None:
            content = ExperienceContent()

        context = data.get('context')
        if isinstance(context, str):
            context = ExperienceContext.from_json(context)
        elif isinstance(context, dict):
            context = ExperienceContext.from_dict(context)
        elif context is None:
            context = ExperienceContext()

        return cls(
            id=data.get('id'),
            uuid=data.get('uuid', str(uuid.uuid4())),
            title=data.get('title', ''),
            experience_level=data.get('experience_level', ExperienceLevel.OPERATIONAL.value),
            category=data.get('category', ''),
            content=content,
            context=context,
            source_type=data.get('source_type', SourceType.MANUAL.value),
            source_ref=data.get('source_ref', ''),
            confidence=data.get('confidence', 0.5),
            validation_count=data.get('validation_count', 0),
            last_validated=data.get('last_validated'),
            status=data.get('status', ExperienceStatus.DRAFT.value),
            deprecated_reason=data.get('deprecated_reason', ''),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    @property
    def is_validated(self) -> bool:
        """是否已验证"""
        return self.status == ExperienceStatus.VALIDATED.value

    @property
    def is_deprecated(self) -> bool:
        """是否已废弃"""
        return self.status == ExperienceStatus.DEPRECATED.value

    @property
    def is_strategic(self) -> bool:
        """是否为战略级经验"""
        return self.experience_level == ExperienceLevel.STRATEGIC.value

    @property
    def is_tactical(self) -> bool:
        """是否为战术级经验"""
        return self.experience_level == ExperienceLevel.TACTICAL.value

    @property
    def is_operational(self) -> bool:
        """是否为操作级经验"""
        return self.experience_level == ExperienceLevel.OPERATIONAL.value

    @property
    def summary(self) -> str:
        """获取经验摘要"""
        if self.content.lesson:
            lesson = self.content.lesson
            if len(lesson) <= 200:
                return lesson
            return lesson[:200] + "..."
        return ""

    def to_embedding_text(self) -> str:
        """
        生成用于向量化的文本

        组合标题和核心内容。
        """
        parts = [self.title]
        content_text = self.content.to_embedding_text()
        if content_text:
            parts.append(content_text)
        return "\n".join(parts)


@dataclass
class ExperienceLink:
    """
    经验关联

    建立经验与其他实体（因子、策略、笔记、研报）的关联关系。
    """
    id: Optional[int] = None
    experience_id: Optional[int] = None
    experience_uuid: str = ""
    entity_type: str = ""           # factor, strategy, note, research, experience
    entity_id: str = ""             # 实体 ID（因子名、策略ID等）
    relation: str = "related"       # 关系类型: related, derived_from, applied_to, curated_from
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'experience_id': self.experience_id,
            'experience_uuid': self.experience_uuid,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'relation': self.relation,
            'created_at': self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperienceLink':
        """从字典创建"""
        return cls(
            id=data.get('id'),
            experience_id=data.get('experience_id'),
            experience_uuid=data.get('experience_uuid', ''),
            entity_type=data.get('entity_type', ''),
            entity_id=data.get('entity_id', ''),
            relation=data.get('relation', 'related'),
            created_at=data.get('created_at'),
        )
