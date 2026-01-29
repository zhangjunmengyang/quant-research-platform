"""
Graph 模块 Pydantic Schemas

定义 Graph API 的请求和响应模型。
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GraphNodeType(str, Enum):
    """节点类型"""

    DATA = "data"
    FACTOR = "factor"
    STRATEGY = "strategy"
    NOTE = "note"
    RESEARCH = "research"
    EXPERIENCE = "experience"
    TAG = "tag"


class GraphRelationType(str, Enum):
    """关系类型

    2 主类型 + subtype 设计:
    - DERIVES: 派生关系 (有方向)，subtype: based/inspired/uses/produces/evolves/enables
    - RELATES: 关联关系 (默认双向)，subtype: refs/similar/validates/contrasts/temporal
    """

    DERIVES = "derives"
    RELATES = "relates"


# ==================== 边相关 ====================


class GraphEdge(BaseModel):
    """图边"""

    source_type: GraphNodeType
    source_id: str
    target_type: GraphNodeType
    target_id: str
    relation: GraphRelationType
    subtype: str = ""
    is_bidirectional: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class GetEdgesResponse(BaseModel):
    """获取边响应"""

    entity_type: GraphNodeType
    entity_id: str
    count: int
    edges: list[GraphEdge]


# ==================== 链路追溯 ====================


class LineageNode(BaseModel):
    """链路节点"""

    depth: int
    node_type: GraphNodeType
    node_id: str
    relation: GraphRelationType
    subtype: str = ""
    direction: str


class LineageResult(BaseModel):
    """链路追溯结果"""

    start_type: GraphNodeType
    start_id: str
    direction: str
    max_depth: int
    count: int
    nodes: list[LineageNode]


# ==================== 路径查找 ====================


class PathElement(BaseModel):
    """路径元素"""

    type: str  # "node" 或 "relationship"
    label: str | None = None
    id: str | None = None
    relation: str | None = None
    position: int


class PathResult(BaseModel):
    """路径查找结果"""

    source_type: GraphNodeType
    source_id: str
    target_type: GraphNodeType
    target_id: str
    count: int
    paths: list[list[dict[str, Any]]]


# ==================== 标签相关 ====================


class TagInfo(BaseModel):
    """标签信息"""

    tag: str
    count: int


class TaggedEntity(BaseModel):
    """带标签的实体"""

    type: GraphNodeType
    id: str


class EntityTagsResponse(BaseModel):
    """实体标签响应"""

    entity_type: GraphNodeType
    entity_id: str
    tags: list[str]
    count: int


# ==================== 图谱概览 ====================


class GraphNode(BaseModel):
    """图节点"""

    type: GraphNodeType
    id: str
    degree: int = 0


class GraphOverviewStats(BaseModel):
    """图谱统计信息"""

    total_nodes: int
    total_edges: int
    node_counts: dict[str, int]
    returned_nodes: int
    returned_edges: int


class GraphOverviewEdge(BaseModel):
    """概览边 (简化版)"""

    source_type: GraphNodeType
    source_id: str
    target_type: GraphNodeType
    target_id: str
    relation: GraphRelationType
    subtype: str = ""
    is_bidirectional: bool = False


class GraphOverviewResponse(BaseModel):
    """图谱概览响应"""

    nodes: list[GraphNode]
    edges: list[GraphOverviewEdge]
    stats: GraphOverviewStats
