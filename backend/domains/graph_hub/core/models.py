"""
图谱数据模型

定义 Neo4j 图数据库的节点和边数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


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
    RelationType.RELATED,
    RelationType.REFERENCES,
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
    RelationType.DERIVED_FROM: "派生自",
    RelationType.APPLIED_TO: "应用于",
    RelationType.VERIFIES: "验证",
    RelationType.REFERENCES: "引用",
    RelationType.SUMMARIZES: "总结为",
    RelationType.HAS_TAG: "拥有标签",
    RelationType.RELATED: "关联",
}


# 兼容别名
EdgeEntityType = NodeType
EdgeRelationType = RelationType


__all__ = [
    "NodeType",
    "RelationType",
    "EdgeEntityType",
    "EdgeRelationType",
    "BIDIRECTIONAL_RELATIONS",
    "ENTITY_TYPE_NAMES",
    "RELATION_TYPE_NAMES",
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
    properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        """Neo4j 标签名 (首字母大写)"""
        return self.node_type.value.capitalize()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_type": self.node_type.value,
            "node_id": self.node_id,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphNode":
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
    relation: RelationType = RelationType.RELATED
    is_bidirectional: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """初始化后自动设置双向标记"""
        if self.relation in BIDIRECTIONAL_RELATIONS and not self.is_bidirectional:
            self.is_bidirectional = True

    def to_dict(self) -> Dict[str, Any]:
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
            "is_bidirectional": self.is_bidirectional,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphEdge":
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

        # 解析 relation
        relation = data.get("relation", "related")
        if isinstance(relation, str):
            try:
                relation = RelationType(relation)
            except ValueError:
                relation = RelationType.RELATED

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
            source_type=source_type,
            source_id=data.get("source_id", ""),
            target_type=target_type,
            target_id=data.get("target_id", ""),
            relation=relation,
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
    direction: str  # "forward" 或 "backward"

    def to_dict(self) -> Dict[str, Any]:
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
            "direction": self.direction,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LineageNode":
        """从字典创建"""
        # 解析 node_type
        node_type = data.get("node_type", "data")
        if isinstance(node_type, str):
            try:
                node_type = NodeType(node_type)
            except ValueError:
                node_type = NodeType.DATA

        # 解析 relation
        relation = data.get("relation", "related")
        if isinstance(relation, str):
            try:
                relation = RelationType(relation)
            except ValueError:
                relation = RelationType.RELATED

        return cls(
            depth=data.get("depth", 0),
            node_type=node_type,
            node_id=data.get("node_id", ""),
            relation=relation,
            direction=data.get("direction", "forward"),
        )


@dataclass
class LineageResult:
    """链路追溯结果"""

    start_type: NodeType
    start_id: str
    direction: str
    max_depth: int
    nodes: List[LineageNode] = field(default_factory=list)

    @property
    def count(self) -> int:
        """节点数量"""
        return len(self.nodes)

    def to_dict(self) -> Dict[str, Any]:
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
    def from_dict(cls, data: Dict[str, Any]) -> "LineageResult":
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
    paths: List[List[Dict[str, Any]]] = field(default_factory=list)

    @property
    def count(self) -> int:
        """路径数量"""
        return len(self.paths)

    def to_dict(self) -> Dict[str, Any]:
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
    def from_dict(cls, data: Dict[str, Any]) -> "PathResult":
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
    relation: RelationType = RelationType.RELATED
    is_bidirectional: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.relation in BIDIRECTIONAL_RELATIONS and not self.is_bidirectional:
            self.is_bidirectional = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "source_type": self.source_type.value if isinstance(self.source_type, NodeType) else self.source_type,
            "source_id": self.source_id,
            "target_type": self.target_type.value if isinstance(self.target_type, NodeType) else self.target_type,
            "target_id": self.target_id,
            "relation": self.relation.value if isinstance(self.relation, RelationType) else self.relation,
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
                source_type = NodeType(source_type)
            except ValueError:
                source_type = NodeType.DATA

        target_type = data.get("target_type", "data")
        if isinstance(target_type, str):
            try:
                target_type = NodeType(target_type)
            except ValueError:
                target_type = NodeType.DATA

        relation = data.get("relation", "related")
        if isinstance(relation, str):
            try:
                relation = RelationType(relation)
            except ValueError:
                relation = RelationType.RELATED

        created_at_raw = data.get("created_at")
        created_at: Optional[datetime] = None
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
            is_bidirectional=data.get("is_bidirectional", False),
            metadata=data.get("metadata", {}),
            created_at=created_at,
        )
