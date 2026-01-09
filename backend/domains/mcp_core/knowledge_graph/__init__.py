"""
知识图谱基础设施

提供知识图谱的核心能力:
- 数据模型: Entity, Relation, Triple
- 实体/关系抽取: EntityExtractor, RelationExtractor, KnowledgeExtractor
- 图谱存储: KnowledgeGraphStore
- 图谱查询: KnowledgeGraphQuery

使用示例:
    from domains.mcp_core.knowledge_graph import (
        Entity, EntityType,
        Relation, RelationType,
        Triple,
        KnowledgeExtractor,
        get_kg_store,
        get_kg_query,
    )
    from domains.mcp_core.llm import get_llm_client

    # 1. 从文本抽取知识
    extractor = KnowledgeExtractor(get_llm_client())
    triples = await extractor.extract("动量因子在牛市中表现优异")

    # 2. 存储到图谱
    store = get_kg_store()
    for triple in triples:
        store.save_triple(triple)

    # 3. 查询图谱
    query = get_kg_query()
    related = query.get_related_entities(entity_id=1, depth=2)
    path = query.find_path(source_id=1, target_id=2)
"""

# 数据模型
from .models import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    Triple,
    EntityWithNeighbors,
    GraphPath,
    ENTITY_TYPE_NAMES,
    RELATION_TYPE_NAMES,
)

# 抽取器
from .extractor import (
    EntityExtractor,
    RelationExtractor,
    KnowledgeExtractor,
)

# 存储
from .store import (
    KnowledgeGraphStore,
    get_kg_store,
)

# 查询
from .query import (
    KnowledgeGraphQuery,
    get_kg_query,
)

__all__ = [
    # 数据模型
    "Entity",
    "EntityType",
    "Relation",
    "RelationType",
    "Triple",
    "EntityWithNeighbors",
    "GraphPath",
    "ENTITY_TYPE_NAMES",
    "RELATION_TYPE_NAMES",
    # 抽取器
    "EntityExtractor",
    "RelationExtractor",
    "KnowledgeExtractor",
    # 存储
    "KnowledgeGraphStore",
    "get_kg_store",
    # 查询
    "KnowledgeGraphQuery",
    "get_kg_query",
]
