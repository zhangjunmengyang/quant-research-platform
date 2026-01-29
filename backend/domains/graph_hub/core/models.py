"""
图谱数据模型

定义 Neo4j 图数据库的节点和边数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    """
    节点类型枚举

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


class RelationType(str, Enum):
    """
    关系主类型枚举

    简化为两个主类型，具体语义通过 subtype 字段细化:
    - DERIVES: 有方向的派生/因果关系（A 产生/影响 B）
    - RELATES: 语义关联关系（A 与 B 相关，默认双向）
    """

    DERIVES = "derives"  # 派生关系: A -> B（A 产生/影响 B）
    RELATES = "relates"  # 关联关系: A <-> B（A 与 B 相关）


class DeriveSubtype:
    """
    DERIVES 关系的子类型常量

    这些是建议值，实际使用时可以传入任意字符串，便于扩展。
    """

    BASED = "based"  # 基于（代码/数据直接派生）
    INSPIRED = "inspired"  # 启发自（思路来源）
    USES = "uses"  # 使用（策略使用因子）
    PRODUCES = "produces"  # 产出（检验产出因子，经验产出自笔记）
    EVOLVES = "evolves"  # 演化（版本迭代）
    ENABLES = "enables"  # 使能（A 使 B 成为可能）


class RelateSubtype:
    """
    RELATES 关系的子类型常量

    这些是建议值，实际使用时可以传入任意字符串，便于扩展。
    """

    REFS = "refs"  # 引用（笔记引用研报）
    SIMILAR = "similar"  # 相似（两个因子逻辑相似）
    VALIDATES = "validates"  # 验证（支持/反驳，direction 放 metadata）
    CONTRASTS = "contrasts"  # 对比（A 与 B 形成对照）
    TEMPORAL = "temporal"  # 时序共现（同时发生的事件）


# 旧关系类型 -> 新关系类型映射（用于数据迁移和兼容）
LEGACY_RELATION_MAPPING: dict[str, tuple[str, str]] = {
    "derived_from": ("derives", "based"),
    "applied_to": ("derives", "uses"),
    "verifies": ("relates", "validates"),
    "references": ("relates", "refs"),
    "summarizes": ("derives", "produces"),
    "related": ("relates", "similar"),
    # has_tag 不再映射，改为节点属性
}


# 典型双向关系（RELATES 默认双向）
BIDIRECTIONAL_RELATIONS = {
    RelationType.RELATES,
}

# 实体类型中文映射
ENTITY_TYPE_NAMES = {
    NodeType.DATA: "数据",
    NodeType.FACTOR: "因子",
    NodeType.STRATEGY: "策略",
    NodeType.NOTE: "笔记",
    NodeType.RESEARCH: "研报",
    NodeType.EXPERIENCE: "经验",
    NodeType.TAG: "标签",
}

# 关系类型中文映射
RELATION_TYPE_NAMES = {
    RelationType.DERIVES: "派生",
    RelationType.RELATES: "关联",
}

# 子类型中文映射
SUBTYPE_NAMES = {
    # DERIVES subtypes
    "based": "基于",
    "inspired": "启发自",
    "uses": "使用",
    "produces": "产出",
    "evolves": "演化自",
    "enables": "使能",
    # RELATES subtypes
    "refs": "引用",
    "similar": "相似",
    "validates": "验证",
    "contrasts": "对比",
    "temporal": "共现",
}


# 兼容别名
EdgeEntityType = NodeType
EdgeRelationType = RelationType


__all__ = [
    "NodeType",
    "RelationType",
    "DeriveSubtype",
    "RelateSubtype",
    "EdgeEntityType",
    "EdgeRelationType",
    "BIDIRECTIONAL_RELATIONS",
    "LEGACY_RELATION_MAPPING",
    "ENTITY_TYPE_NAMES",
    "RELATION_TYPE_NAMES",
    "SUBTYPE_NAMES",
    "GraphNode",
    "GraphEdge",
    "KnowledgeEdge",
    "LineageNode",
    "LineageResult",
    "PathResult",
]


@dataclass
class GraphNode:
    """图节点"""

    node_type: NodeType
    node_id: str
    properties: dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        """Neo4j 标签名 (首字母大写)"""
        return self.node_type.value.capitalize()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "node_type": self.node_type.value,
            "node_id": self.node_id,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphNode":
        """从字典创建"""
        node_type = data.get("node_type", "data")
        if isinstance(node_type, str):
            try:
                node_type = NodeType(node_type)
            except ValueError:
                node_type = NodeType.DATA

        return cls(
            node_type=node_type,
            node_id=data.get("node_id", ""),
            properties=data.get("properties", {}),
        )


@dataclass
class GraphEdge:
    """图边"""

    source_type: NodeType
    source_id: str
    target_type: NodeType
    target_id: str
    relation: RelationType = RelationType.RELATES
    subtype: str = ""  # 关系子类型，用于细化语义
    is_bidirectional: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    def __post_init__(self):
        """初始化后自动设置双向标记"""
        # RELATES 默认双向，DERIVES 默认单向
        if self.relation in BIDIRECTIONAL_RELATIONS and not self.is_bidirectional:
            self.is_bidirectional = True

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "source_type": (
                self.source_type.value
                if isinstance(self.source_type, NodeType)
                else self.source_type
            ),
            "source_id": self.source_id,
            "target_type": (
                self.target_type.value
                if isinstance(self.target_type, NodeType)
                else self.target_type
            ),
            "target_id": self.target_id,
            "relation": (
                self.relation.value
                if isinstance(self.relation, RelationType)
                else self.relation
            ),
            "subtype": self.subtype,
            "is_bidirectional": self.is_bidirectional,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphEdge":
        """从字典创建，支持旧格式自动迁移"""
        # 解析 source_type
        source_type = data.get("source_type", "data")
        if isinstance(source_type, str):
            try:
                source_type = NodeType(source_type)
            except ValueError:
                source_type = NodeType.DATA

        # 解析 target_type
        target_type = data.get("target_type", "data")
        if isinstance(target_type, str):
            try:
                target_type = NodeType(target_type)
            except ValueError:
                target_type = NodeType.DATA

        # 解析 relation 和 subtype（支持旧格式迁移）
        relation_raw = data.get("relation", "relates")
        subtype = data.get("subtype", "")

        if isinstance(relation_raw, str):
            # 检查是否为旧格式关系类型
            if relation_raw in LEGACY_RELATION_MAPPING:
                new_rel, default_subtype = LEGACY_RELATION_MAPPING[relation_raw]
                relation = RelationType(new_rel)
                if not subtype:
                    subtype = default_subtype
            else:
                try:
                    relation = RelationType(relation_raw)
                except ValueError:
                    relation = RelationType.RELATES
        else:
            relation = relation_raw if isinstance(relation_raw, RelationType) else RelationType.RELATES

        # 处理 created_at 类型转换
        created_at_raw = data.get("created_at")
        created_at: datetime | None = None
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
            source_type=source_type,
            source_id=data.get("source_id", ""),
            target_type=target_type,
            target_id=data.get("target_id", ""),
            relation=relation,
            subtype=subtype,
            is_bidirectional=data.get("is_bidirectional", False),
            metadata=data.get("metadata", {}),
            created_at=created_at,
        )


@dataclass
class LineageNode:
    """链路节点"""

    depth: int
    node_type: NodeType
    node_id: str
    relation: RelationType
    subtype: str = ""  # 关系子类型
    direction: str = "forward"  # "forward" 或 "backward"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "depth": self.depth,
            "node_type": (
                self.node_type.value
                if isinstance(self.node_type, NodeType)
                else self.node_type
            ),
            "node_id": self.node_id,
            "relation": (
                self.relation.value
                if isinstance(self.relation, RelationType)
                else self.relation
            ),
            "subtype": self.subtype,
            "direction": self.direction,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LineageNode":
        """从字典创建，支持旧格式自动迁移"""
        # 解析 node_type
        node_type = data.get("node_type", "data")
        if isinstance(node_type, str):
            try:
                node_type = NodeType(node_type)
            except ValueError:
                node_type = NodeType.DATA

        # 解析 relation 和 subtype（支持旧格式迁移）
        relation_raw = data.get("relation", "relates")
        subtype = data.get("subtype", "")

        if isinstance(relation_raw, str):
            if relation_raw in LEGACY_RELATION_MAPPING:
                new_rel, default_subtype = LEGACY_RELATION_MAPPING[relation_raw]
                relation = RelationType(new_rel)
                if not subtype:
                    subtype = default_subtype
            else:
                try:
                    relation = RelationType(relation_raw)
                except ValueError:
                    relation = RelationType.RELATES
        else:
            relation = relation_raw if isinstance(relation_raw, RelationType) else RelationType.RELATES

        return cls(
            depth=data.get("depth", 0),
            node_type=node_type,
            node_id=data.get("node_id", ""),
            relation=relation,
            subtype=subtype,
            direction=data.get("direction", "forward"),
        )


@dataclass
class LineageResult:
    """链路追溯结果"""

    start_type: NodeType
    start_id: str
    direction: str
    max_depth: int
    nodes: list[LineageNode] = field(default_factory=list)

    @property
    def count(self) -> int:
        """节点数量"""
        return len(self.nodes)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "start_type": (
                self.start_type.value
                if isinstance(self.start_type, NodeType)
                else self.start_type
            ),
            "start_id": self.start_id,
            "direction": self.direction,
            "max_depth": self.max_depth,
            "count": self.count,
            "nodes": [n.to_dict() for n in self.nodes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LineageResult":
        """从字典创建"""
        # 解析 start_type
        start_type = data.get("start_type", "data")
        if isinstance(start_type, str):
            try:
                start_type = NodeType(start_type)
            except ValueError:
                start_type = NodeType.DATA

        # 解析 nodes 列表
        nodes_data = data.get("nodes", [])
        nodes = [LineageNode.from_dict(n) for n in nodes_data]

        return cls(
            start_type=start_type,
            start_id=data.get("start_id", ""),
            direction=data.get("direction", "forward"),
            max_depth=data.get("max_depth", 3),
            nodes=nodes,
        )


@dataclass
class PathResult:
    """路径查找结果"""

    source_type: NodeType
    source_id: str
    target_type: NodeType
    target_id: str
    paths: list[list[dict[str, Any]]] = field(default_factory=list)

    @property
    def count(self) -> int:
        """路径数量"""
        return len(self.paths)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "source_type": (
                self.source_type.value
                if isinstance(self.source_type, NodeType)
                else self.source_type
            ),
            "source_id": self.source_id,
            "target_type": (
                self.target_type.value
                if isinstance(self.target_type, NodeType)
                else self.target_type
            ),
            "target_id": self.target_id,
            "count": self.count,
            "paths": self.paths,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PathResult":
        """从字典创建"""
        # 解析 source_type
        source_type = data.get("source_type", "data")
        if isinstance(source_type, str):
            try:
                source_type = NodeType(source_type)
            except ValueError:
                source_type = NodeType.DATA

        # 解析 target_type
        target_type = data.get("target_type", "data")
        if isinstance(target_type, str):
            try:
                target_type = NodeType(target_type)
            except ValueError:
                target_type = NodeType.DATA

        return cls(
            source_type=source_type,
            source_id=data.get("source_id", ""),
            target_type=target_type,
            target_id=data.get("target_id", ""),
            paths=data.get("paths", []),
        )


@dataclass
class KnowledgeEdge:
    """
    知识边（关联）

    表示两个实体之间的关联关系，用于链路追溯。
    保留此类以兼容旧代码。
    """

    source_type: NodeType
    source_id: str
    target_type: NodeType
    target_id: str
    relation: RelationType = RelationType.RELATES
    subtype: str = ""  # 关系子类型
    is_bidirectional: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None
    created_at: datetime | None = None

    def __post_init__(self):
        """初始化后处理"""
        if self.relation in BIDIRECTIONAL_RELATIONS and not self.is_bidirectional:
            self.is_bidirectional = True

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "source_type": self.source_type.value if isinstance(self.source_type, NodeType) else self.source_type,
            "source_id": self.source_id,
            "target_type": self.target_type.value if isinstance(self.target_type, NodeType) else self.target_type,
            "target_id": self.target_id,
            "relation": self.relation.value if isinstance(self.relation, RelationType) else self.relation,
            "subtype": self.subtype,
            "is_bidirectional": self.is_bidirectional,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeEdge":
        """从字典创建，支持旧格式自动迁移"""
        source_type = data.get("source_type", "data")
        if isinstance(source_type, str):
            try:
                source_type = NodeType(source_type)
            except ValueError:
                source_type = NodeType.DATA

        target_type = data.get("target_type", "data")
        if isinstance(target_type, str):
            try:
                target_type = NodeType(target_type)
            except ValueError:
                target_type = NodeType.DATA

        # 解析 relation 和 subtype（支持旧格式迁移）
        relation_raw = data.get("relation", "relates")
        subtype = data.get("subtype", "")

        if isinstance(relation_raw, str):
            if relation_raw in LEGACY_RELATION_MAPPING:
                new_rel, default_subtype = LEGACY_RELATION_MAPPING[relation_raw]
                relation = RelationType(new_rel)
                if not subtype:
                    subtype = default_subtype
            else:
                try:
                    relation = RelationType(relation_raw)
                except ValueError:
                    relation = RelationType.RELATES
        else:
            relation = relation_raw if isinstance(relation_raw, RelationType) else RelationType.RELATES

        created_at_raw = data.get("created_at")
        created_at: datetime | None = None
        if created_at_raw is not None:
            if isinstance(created_at_raw, datetime):
                created_at = created_at_raw
            elif isinstance(created_at_raw, str):
                try:
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
            subtype=subtype,
            is_bidirectional=data.get("is_bidirectional", False),
            metadata=data.get("metadata", {}),
            created_at=created_at,
        )
