"""
知识边（关联）基础设施

提供简单的实体关联追溯能力:
- 数据模型: KnowledgeEdge, EdgeEntityType, EdgeRelationType
- 存储层: EdgeStore

用于建立数据-信息-知识-经验的完整链路追溯。

使用示例:
    from domains.mcp_core.edge import (
        KnowledgeEdge,
        EdgeEntityType,
        EdgeRelationType,
        get_edge_store,
    )

    # 创建关联
    store = get_edge_store()
    edge = KnowledgeEdge(
        source_type=EdgeEntityType.FACTOR,
        source_id="Momentum_5d",
        target_type=EdgeEntityType.DATA,
        target_id="BTC-USDT",
        relation=EdgeRelationType.DERIVED_FROM,
    )
    edge_id = store.create(edge)

    # 查询关联
    edges = store.get_edges_by_entity(EdgeEntityType.FACTOR, "Momentum_5d")
"""

from .models import (
    KnowledgeEdge,
    EdgeEntityType,
    EdgeRelationType,
)

from .store import (
    EdgeStore,
    get_edge_store,
)

__all__ = [
    # 数据模型
    "KnowledgeEdge",
    "EdgeEntityType",
    "EdgeRelationType",
    # 存储
    "EdgeStore",
    "get_edge_store",
]
