"""
知识图谱数据模型

定义知识图谱的核心数据结构:
- Entity: 实体节点
- Relation: 关系边
- Triple: 三元组（主语-谓语-宾语）

实体类型和关系类型针对量化研究领域设计。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class EntityType(str, Enum):
    """实体类型枚举"""

    FACTOR = "factor"  # 因子
    STRATEGY = "strategy"  # 策略
    MARKET_REGIME = "market_regime"  # 市场状态（牛市/熊市/震荡）
    CONCEPT = "concept"  # 概念（动量、反转、均值回归等）
    METRIC = "metric"  # 指标（IC、Sharpe、回撤等）
    TIME_WINDOW = "time_window"  # 时间窗口（日内/周度/月度）
    ASSET = "asset"  # 资产（BTC、ETH 等）
    PARAMETER = "parameter"  # 参数（如窗口长度、阈值）
    CONDITION = "condition"  # 条件（如高波动、低流动性）
    ACTION = "action"  # 操作（如开仓、平仓、调参）


class RelationType(str, Enum):
    """关系类型枚举"""

    # 基础关系
    RELATED_TO = "related_to"  # 相关
    DERIVED_FROM = "derived_from"  # 派生自
    BELONGS_TO = "belongs_to"  # 属于

    # 因子/策略关系
    EFFECTIVE_IN = "effective_in"  # 在某环境下有效
    CONFLICTS_WITH = "conflicts_with"  # 与...冲突
    OPTIMIZED_BY = "optimized_by"  # 被...优化
    COMPOSED_OF = "composed_of"  # 由...组成
    OUTPERFORMS_IN = "outperforms_in"  # 在某条件下优于

    # 因果关系
    CAUSES = "causes"  # 导致
    INDICATES = "indicates"  # 指示
    PRECEDES = "precedes"  # 先于
    FOLLOWS = "follows"  # 后于

    # 参数关系
    HAS_PARAMETER = "has_parameter"  # 有参数
    SENSITIVE_TO = "sensitive_to"  # 对...敏感

    # 适用性关系
    APPLIES_TO = "applies_to"  # 适用于
    REQUIRES = "requires"  # 需要


@dataclass
class Entity:
    """
    实体节点

    表示知识图谱中的一个节点，如因子、策略、概念等。

    Attributes:
        id: 数据库 ID（创建后分配）
        uuid: 唯一标识符
        entity_type: 实体类型
        name: 实体名称
        properties: 扩展属性（JSONB）
        embedding: 向量嵌入（用于语义搜索）
        source_type: 来源类型
        source_ref: 来源引用
        created_at: 创建时间
        updated_at: 更新时间
    """

    entity_type: EntityType
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    uuid: Optional[str] = None
    embedding: Optional[List[float]] = None
    source_type: str = "manual"  # manual, llm_extracted, imported
    source_ref: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "uuid": self.uuid,
            "entity_type": self.entity_type.value if isinstance(self.entity_type, EntityType) else self.entity_type,
            "name": self.name,
            "properties": self.properties,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """从字典创建实体"""
        entity_type = data.get("entity_type", "concept")
        if isinstance(entity_type, str):
            try:
                entity_type = EntityType(entity_type)
            except ValueError:
                entity_type = EntityType.CONCEPT

        return cls(
            id=data.get("id"),
            uuid=data.get("uuid"),
            entity_type=entity_type,
            name=data.get("name", ""),
            properties=data.get("properties", {}),
            embedding=data.get("embedding"),
            source_type=data.get("source_type", "manual"),
            source_ref=data.get("source_ref", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class Relation:
    """
    关系边

    表示两个实体之间的关系。

    Attributes:
        id: 数据库 ID
        relation_type: 关系类型
        source_id: 源实体 ID
        target_id: 目标实体 ID
        source_uuid: 源实体 UUID
        target_uuid: 目标实体 UUID
        properties: 扩展属性
        weight: 关系权重（0-1）
        created_at: 创建时间
    """

    relation_type: RelationType
    source_id: int
    target_id: int
    properties: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    source_uuid: Optional[str] = None
    target_uuid: Optional[str] = None
    weight: float = 1.0
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "relation_type": self.relation_type.value if isinstance(self.relation_type, RelationType) else self.relation_type,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "source_uuid": self.source_uuid,
            "target_uuid": self.target_uuid,
            "properties": self.properties,
            "weight": self.weight,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relation":
        """从字典创建关系"""
        relation_type = data.get("relation_type", "related_to")
        if isinstance(relation_type, str):
            try:
                relation_type = RelationType(relation_type)
            except ValueError:
                relation_type = RelationType.RELATED_TO

        return cls(
            id=data.get("id"),
            relation_type=relation_type,
            source_id=data.get("source_id", 0),
            target_id=data.get("target_id", 0),
            source_uuid=data.get("source_uuid"),
            target_uuid=data.get("target_uuid"),
            properties=data.get("properties", {}),
            weight=data.get("weight", 1.0),
            created_at=data.get("created_at"),
        )


@dataclass
class Triple:
    """
    三元组

    表示知识图谱中的一条知识：主语-谓语-宾语。
    用于 LLM 抽取结果的中间表示。

    Attributes:
        subject: 主语（实体名称或描述）
        subject_type: 主语实体类型
        predicate: 谓语（关系类型）
        object: 宾语（实体名称或描述）
        object_type: 宾语实体类型
        confidence: 置信度（0-1）
        context: 抽取上下文
    """

    subject: str
    subject_type: EntityType
    predicate: RelationType
    object: str
    object_type: EntityType
    confidence: float = 1.0
    context: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "subject": self.subject,
            "subject_type": self.subject_type.value if isinstance(self.subject_type, EntityType) else self.subject_type,
            "predicate": self.predicate.value if isinstance(self.predicate, RelationType) else self.predicate,
            "object": self.object,
            "object_type": self.object_type.value if isinstance(self.object_type, EntityType) else self.object_type,
            "confidence": self.confidence,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Triple":
        """从字典创建三元组"""
        subject_type = data.get("subject_type", "concept")
        if isinstance(subject_type, str):
            try:
                subject_type = EntityType(subject_type)
            except ValueError:
                subject_type = EntityType.CONCEPT

        object_type = data.get("object_type", "concept")
        if isinstance(object_type, str):
            try:
                object_type = EntityType(object_type)
            except ValueError:
                object_type = EntityType.CONCEPT

        predicate = data.get("predicate", "related_to")
        if isinstance(predicate, str):
            try:
                predicate = RelationType(predicate)
            except ValueError:
                predicate = RelationType.RELATED_TO

        return cls(
            subject=data.get("subject", ""),
            subject_type=subject_type,
            predicate=predicate,
            object=data.get("object", ""),
            object_type=object_type,
            confidence=data.get("confidence", 1.0),
            context=data.get("context", ""),
        )


@dataclass
class EntityWithNeighbors:
    """
    带邻居的实体

    用于图遍历查询结果。

    Attributes:
        entity: 中心实体
        incoming: 入边关系和源实体
        outgoing: 出边关系和目标实体
    """

    entity: Entity
    incoming: List[tuple[Relation, Entity]] = field(default_factory=list)
    outgoing: List[tuple[Relation, Entity]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entity": self.entity.to_dict(),
            "incoming": [
                {"relation": r.to_dict(), "entity": e.to_dict()}
                for r, e in self.incoming
            ],
            "outgoing": [
                {"relation": r.to_dict(), "entity": e.to_dict()}
                for r, e in self.outgoing
            ],
        }


@dataclass
class GraphPath:
    """
    图路径

    表示两个实体之间的一条路径。

    Attributes:
        entities: 路径上的实体列表
        relations: 路径上的关系列表
        length: 路径长度
    """

    entities: List[Entity]
    relations: List[Relation]

    @property
    def length(self) -> int:
        """路径长度"""
        return len(self.relations)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "length": self.length,
        }


# 实体类型和关系类型的中文映射（用于 Prompt）
ENTITY_TYPE_NAMES = {
    EntityType.FACTOR: "因子",
    EntityType.STRATEGY: "策略",
    EntityType.MARKET_REGIME: "市场状态",
    EntityType.CONCEPT: "概念",
    EntityType.METRIC: "指标",
    EntityType.TIME_WINDOW: "时间窗口",
    EntityType.ASSET: "资产",
    EntityType.PARAMETER: "参数",
    EntityType.CONDITION: "条件",
    EntityType.ACTION: "操作",
}

RELATION_TYPE_NAMES = {
    RelationType.RELATED_TO: "相关",
    RelationType.DERIVED_FROM: "派生自",
    RelationType.BELONGS_TO: "属于",
    RelationType.EFFECTIVE_IN: "在...下有效",
    RelationType.CONFLICTS_WITH: "与...冲突",
    RelationType.OPTIMIZED_BY: "被...优化",
    RelationType.COMPOSED_OF: "由...组成",
    RelationType.OUTPERFORMS_IN: "在...下优于",
    RelationType.CAUSES: "导致",
    RelationType.INDICATES: "指示",
    RelationType.PRECEDES: "先于",
    RelationType.FOLLOWS: "后于",
    RelationType.HAS_PARAMETER: "有参数",
    RelationType.SENSITIVE_TO: "对...敏感",
    RelationType.APPLIES_TO: "适用于",
    RelationType.REQUIRES: "需要",
}
