"""
知识边数据模型

定义简单的实体关联结构，用于数据-信息-知识-经验的链路追溯。

与 knowledge_graph 模块的区别:
- knowledge_graph: 用于 LLM 知识抽取，包含复杂的图结构和向量嵌入
- edge: 简单的实体关联表，聚焦于链路追溯
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class EdgeEntityType(str, Enum):
    """
    实体类型枚举

    按知识层级分类:
    - Data: 数据层（原始数据）
    - Information: 信息层（加工信息）
    - Knowledge: 知识层（研究产出）
    - Wisdom: 经验层（实践智慧）
    - Meta: 元数据层（标签、分类）
    """

    # 数据层
    DATA = "data"  # 原始数据：币种、K线

    # 信息层
    FACTOR = "factor"  # 因子
    STRATEGY = "strategy"  # 策略

    # 知识层
    NOTE = "note"  # 研究笔记
    RESEARCH = "research"  # 外部研报

    # 经验层
    EXPERIENCE = "experience"  # 经验记录

    # 元数据层
    TAG = "tag"  # 标签（如：妖币、蓝筹、高波动）


class EdgeRelationType(str, Enum):
    """
    关系类型枚举

    定义实体间的关联关系，支持链路追溯。
    """

    # 派生关系
    DERIVED_FROM = "derived_from"  # A 派生自 B（如：因子 derived_from 数据）

    # 应用关系
    APPLIED_TO = "applied_to"  # A 应用于 B（如：策略 applied_to 因子）

    # 验证关系
    VERIFIES = "verifies"  # A 验证 B（如：检验笔记 verifies 假设笔记）

    # 引用关系
    REFERENCES = "references"  # A 引用 B（如：笔记 references 研报）

    # 总结关系
    SUMMARIZES = "summarizes"  # A 总结 B（如：经验 summarizes 笔记）

    # 标签关系
    HAS_TAG = "has_tag"  # A 拥有标签 B（如：data:BTC-USDT has_tag tag:妖币）

    # 通用关联
    RELATED = "related"  # 一般关联（默认）


# 典型双向关系
BIDIRECTIONAL_RELATIONS = {
    EdgeRelationType.RELATED,
    EdgeRelationType.REFERENCES,
}


@dataclass
class KnowledgeEdge:
    """
    知识边（关联）

    表示两个实体之间的关联关系，用于链路追溯。

    Attributes:
        id: 数据库 ID
        source_type: 源实体类型
        source_id: 源实体 ID
        target_type: 目标实体类型
        target_id: 目标实体 ID
        relation: 关系类型
        is_bidirectional: 是否双向
        metadata: 扩展元数据
        created_at: 创建时间
    """

    source_type: EdgeEntityType
    source_id: str
    target_type: EdgeEntityType
    target_id: str
    relation: EdgeRelationType = EdgeRelationType.RELATED
    is_bidirectional: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """初始化后处理"""
        # 自动设置双向标记
        if self.relation in BIDIRECTIONAL_RELATIONS and not self.is_bidirectional:
            self.is_bidirectional = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "source_type": self.source_type.value if isinstance(self.source_type, EdgeEntityType) else self.source_type,
            "source_id": self.source_id,
            "target_type": self.target_type.value if isinstance(self.target_type, EdgeEntityType) else self.target_type,
            "target_id": self.target_id,
            "relation": self.relation.value if isinstance(self.relation, EdgeRelationType) else self.relation,
            "is_bidirectional": self.is_bidirectional,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeEdge":
        """从字典创建"""
        source_type = data.get("source_type", "data")
        if isinstance(source_type, str):
            try:
                source_type = EdgeEntityType(source_type)
            except ValueError:
                source_type = EdgeEntityType.DATA

        target_type = data.get("target_type", "data")
        if isinstance(target_type, str):
            try:
                target_type = EdgeEntityType(target_type)
            except ValueError:
                target_type = EdgeEntityType.DATA

        relation = data.get("relation", "related")
        if isinstance(relation, str):
            try:
                relation = EdgeRelationType(relation)
            except ValueError:
                relation = EdgeRelationType.RELATED

        # 处理 created_at 类型转换
        created_at_raw = data.get("created_at")
        created_at: Optional[datetime] = None
        if created_at_raw is not None:
            if isinstance(created_at_raw, datetime):
                created_at = created_at_raw
            elif isinstance(created_at_raw, str):
                try:
                    # 支持 ISO 格式，包括带 Z 后缀的 UTC 时间
                    created_at = datetime.fromisoformat(
                        created_at_raw.replace("Z", "+00:00")
                    )
                except ValueError:
                    created_at = None

        return cls(
            id=data.get("id"),
            source_type=source_type,
            source_id=data.get("source_id", ""),
            target_type=target_type,
            target_id=data.get("target_id", ""),
            relation=relation,
            is_bidirectional=data.get("is_bidirectional", False),
            metadata=data.get("metadata", {}),
            created_at=created_at,
        )


# 实体类型中文映射
ENTITY_TYPE_NAMES = {
    EdgeEntityType.DATA: "数据",
    EdgeEntityType.FACTOR: "因子",
    EdgeEntityType.STRATEGY: "策略",
    EdgeEntityType.NOTE: "笔记",
    EdgeEntityType.RESEARCH: "研报",
    EdgeEntityType.EXPERIENCE: "经验",
    EdgeEntityType.TAG: "标签",
}

# 关系类型中文映射
RELATION_TYPE_NAMES = {
    EdgeRelationType.DERIVED_FROM: "派生自",
    EdgeRelationType.APPLIED_TO: "应用于",
    EdgeRelationType.VERIFIES: "验证",
    EdgeRelationType.REFERENCES: "引用",
    EdgeRelationType.SUMMARIZES: "总结为",
    EdgeRelationType.HAS_TAG: "拥有标签",
    EdgeRelationType.RELATED: "关联",
}
