"""
知识边数据模型 - 兼容层

此模块已迁移至 graph_hub，保留此文件以兼容旧代码。
请在新代码中直接使用 domains.graph_hub.core 中的类型。
"""

# 从 graph_hub 导入并重新导出
from domains.graph_hub.core.models import (
    BIDIRECTIONAL_RELATIONS,
    ENTITY_TYPE_NAMES,
    RELATION_TYPE_NAMES,
    EdgeEntityType,
    EdgeRelationType,
    KnowledgeEdge,
    NodeType,
    RelationType,
)

__all__ = [
    "EdgeEntityType",
    "EdgeRelationType",
    "NodeType",
    "RelationType",
    "KnowledgeEdge",
    "BIDIRECTIONAL_RELATIONS",
    "ENTITY_TYPE_NAMES",
    "RELATION_TYPE_NAMES",
]
