"""
因子评估库数据模型

定义因子评估的核心数据结构，用于保存因子分析结果和 AI 评估文本。
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FactorEvaluationContent:
    """
    因子评估的核心内容

    Attributes:
        evaluations: 评估类型到 AI 评估文本的映射
            (ic_performance, grouping_ability, style_profile, market_cap, comprehensive)
        analysis_snapshot: 保存时的分析结果数据快照
    """
    evaluations: dict[str, str] = field(default_factory=dict)
    analysis_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            'evaluations': self.evaluations,
            'analysis_snapshot': self.analysis_snapshot,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'FactorEvaluationContent':
        """从字典创建"""
        return cls(
            evaluations=data.get('evaluations', {}),
            analysis_snapshot=data.get('analysis_snapshot', {}),
        )

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> 'FactorEvaluationContent':
        """从 JSON 字符串创建"""
        if not json_str:
            return cls()
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class FactorEvaluation:
    """
    因子评估实体

    保存因子分析结果和 AI 评估文本，通过标签进行分类管理。
    """
    # === 基础信息 ===
    id: int | None = None
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    factor_name: str = ""
    title: str = ""

    # === 核心内容 ===
    content: FactorEvaluationContent = field(default_factory=FactorEvaluationContent)

    # === 标签 ===
    tags: list[str] = field(default_factory=list)

    # === 时间戳 ===
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'factor_name': self.factor_name,
            'title': self.title,
            'content': self.content.to_dict() if isinstance(self.content, FactorEvaluationContent) else self.content,
            'tags': self.tags,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'FactorEvaluation':
        """从字典创建因子评估实例"""
        content = data.get('content')
        if isinstance(content, str):
            content = FactorEvaluationContent.from_json(content)
        elif isinstance(content, dict):
            content = FactorEvaluationContent.from_dict(content)
        elif content is None:
            content = FactorEvaluationContent()

        return cls(
            id=data.get('id'),
            uuid=data.get('uuid', str(uuid.uuid4())),
            factor_name=data.get('factor_name', ''),
            title=data.get('title', ''),
            content=content,
            tags=data.get('tags', []),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )
