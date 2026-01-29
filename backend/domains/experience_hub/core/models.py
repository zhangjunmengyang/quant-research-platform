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
from typing import Any


class SourceType(str, Enum):
    """来源类型"""
    RESEARCH = "research"        # 研究会话
    BACKTEST = "backtest"        # 回测结果
    LIVE_TRADE = "live_trade"    # 实盘交易
    EXTERNAL = "external"        # 外部输入
    MANUAL = "manual"            # 手动录入


class EntityType(str, Enum):
    """关联实体类型"""
    FACTOR = "factor"            # 因子
    STRATEGY = "strategy"        # 策略
    NOTE = "note"                # 笔记
    RESEARCH = "research"        # 研报
    EXPERIENCE = "experience"    # 经验


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

    def to_dict(self) -> dict[str, str]:
        """转换为字典"""
        return {
            'problem': self.problem,
            'approach': self.approach,
            'result': self.result,
            'lesson': self.lesson,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ExperienceContent':
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
        """生成用于向量化的文本"""
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
        tags: 自定义标签（核心分类方式）
        factor_styles: 相关的因子风格
        market_regime: 市场状态（牛市/熊市/震荡）
        time_horizon: 适用的时间范围（短期/中期/长期）
        asset_class: 资产类别（BTC/ETH/山寨币/全市场）
    """
    tags: list[str] = field(default_factory=list)
    factor_styles: list[str] = field(default_factory=list)
    market_regime: str = ""
    time_horizon: str = ""
    asset_class: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            'tags': self.tags,
            'factor_styles': self.factor_styles,
            'market_regime': self.market_regime,
            'time_horizon': self.time_horizon,
            'asset_class': self.asset_class,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ExperienceContext':
        """从字典创建"""
        return cls(
            tags=data.get('tags', []),
            factor_styles=data.get('factor_styles', []),
            market_regime=data.get('market_regime', ''),
            time_horizon=data.get('time_horizon', ''),
            asset_class=data.get('asset_class', ''),
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

    存储结构化的研究经验，通过标签进行分类管理。
    """
    # === 基础信息 ===
    id: int | None = None
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""

    # === 核心内容（PARL） ===
    content: ExperienceContent = field(default_factory=ExperienceContent)

    # === 上下文（包含标签） ===
    context: ExperienceContext = field(default_factory=ExperienceContext)

    # === 来源追溯 ===
    source_type: str = SourceType.MANUAL.value
    source_ref: str = ""

    # === 时间戳 ===
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'content': self.content.to_dict() if isinstance(self.content, ExperienceContent) else self.content,
            'context': self.context.to_dict() if isinstance(self.context, ExperienceContext) else self.context,
            'source_type': self.source_type,
            'source_ref': self.source_ref,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Experience':
        """从字典创建经验实例"""
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
            content=content,
            context=context,
            source_type=data.get('source_type', SourceType.MANUAL.value),
            source_ref=data.get('source_ref', ''),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    @property
    def tags(self) -> list[str]:
        """获取标签列表"""
        return self.context.tags

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
        """生成用于向量化的文本"""
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
    id: int | None = None
    experience_id: int | None = None
    experience_uuid: str = ""
    entity_type: str = ""
    entity_id: str = ""
    relation: str = "related"
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
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
    def from_dict(cls, data: dict[str, Any]) -> 'ExperienceLink':
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
