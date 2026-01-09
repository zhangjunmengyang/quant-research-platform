"""
知识图谱存储层

基于 PostgreSQL 的知识图谱存储:
- 实体存储（entities 表）
- 关系存储（relations 表）
- 向量索引（pgvector HNSW）
- CRUD 操作
- 图遍历支持

继承自 mcp_core.base.store.BaseStore 模式。
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from ..base.store import ThreadSafeConnectionMixin, get_store_instance

from .models import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    Triple,
)

logger = logging.getLogger(__name__)


class KnowledgeGraphStore(ThreadSafeConnectionMixin):
    """
    知识图谱存储

    管理实体和关系的持久化存储。

    Example:
        store = get_kg_store()

        # 创建实体
        entity = Entity(entity_type=EntityType.FACTOR, name="动量因子")
        entity = store.create_entity(entity)

        # 创建关系
        relation = Relation(
            relation_type=RelationType.EFFECTIVE_IN,
            source_id=entity1.id,
            target_id=entity2.id
        )
        relation = store.create_relation(relation)

        # 查询
        entities = store.get_entities_by_type(EntityType.FACTOR)
    """

    # 实体表允许的列
    entity_columns: Set[str] = {
        "id", "uuid", "entity_type", "name", "properties",
        "embedding", "source_type", "source_ref",
        "created_at", "updated_at",
    }

    # 关系表允许的列
    relation_columns: Set[str] = {
        "id", "relation_type", "source_id", "target_id",
        "source_uuid", "target_uuid", "properties", "weight",
        "created_at",
    }

    def __init__(self, database_url: Optional[str] = None):
        """
        初始化存储

        Args:
            database_url: PostgreSQL 连接 URL
        """
        self._init_connection(database_url)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== 实体操作 ====================

    def create_entity(self, entity: Entity) -> Entity:
        """
        创建实体

        Args:
            entity: 实体对象

        Returns:
            创建后的实体（包含 id）
        """
        if not entity.uuid:
            entity.uuid = str(uuid.uuid4())

        now = datetime.now()
        entity.created_at = now
        entity.updated_at = now

        with self._cursor() as cursor:
            # 检查是否存在同名同类型实体
            cursor.execute(
                """
                SELECT id FROM kg_entities
                WHERE entity_type = %s AND name = %s
                """,
                (entity.entity_type.value, entity.name)
            )
            existing = cursor.fetchone()
            if existing:
                entity.id = existing["id"]
                return self.get_entity_by_id(entity.id)

            cursor.execute(
                """
                INSERT INTO kg_entities
                (uuid, entity_type, name, properties, source_type, source_ref, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    entity.uuid,
                    entity.entity_type.value if isinstance(entity.entity_type, EntityType) else entity.entity_type,
                    entity.name,
                    json.dumps(entity.properties) if entity.properties else "{}",
                    entity.source_type,
                    entity.source_ref,
                    entity.created_at,
                    entity.updated_at,
                )
            )
            entity.id = cursor.fetchone()["id"]

        return entity

    def create_entities_batch(self, entities: List[Entity]) -> List[Entity]:
        """
        批量创建实体

        Args:
            entities: 实体列表

        Returns:
            创建后的实体列表
        """
        results = []
        for entity in entities:
            created = self.create_entity(entity)
            results.append(created)
        return results

    def get_entity_by_id(self, entity_id: int) -> Optional[Entity]:
        """
        通过 ID 获取实体

        Args:
            entity_id: 实体 ID

        Returns:
            实体对象或 None
        """
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM kg_entities WHERE id = %s",
                (entity_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entity(dict(row))
        return None

    def get_entity_by_uuid(self, entity_uuid: str) -> Optional[Entity]:
        """
        通过 UUID 获取实体

        Args:
            entity_uuid: 实体 UUID

        Returns:
            实体对象或 None
        """
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM kg_entities WHERE uuid = %s",
                (entity_uuid,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entity(dict(row))
        return None

    def get_entity_by_name(
        self,
        name: str,
        entity_type: Optional[EntityType] = None,
    ) -> Optional[Entity]:
        """
        通过名称获取实体

        Args:
            name: 实体名称
            entity_type: 实体类型（可选）

        Returns:
            实体对象或 None
        """
        with self._cursor() as cursor:
            if entity_type:
                cursor.execute(
                    "SELECT * FROM kg_entities WHERE name = %s AND entity_type = %s",
                    (name, entity_type.value)
                )
            else:
                cursor.execute(
                    "SELECT * FROM kg_entities WHERE name = %s",
                    (name,)
                )
            row = cursor.fetchone()
            if row:
                return self._row_to_entity(dict(row))
        return None

    def get_entities_by_type(
        self,
        entity_type: EntityType,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Entity]:
        """
        获取指定类型的所有实体

        Args:
            entity_type: 实体类型
            limit: 限制数量
            offset: 偏移量

        Returns:
            实体列表
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM kg_entities
                WHERE entity_type = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (entity_type.value, limit, offset)
            )
            return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

    def search_entities(
        self,
        query: str,
        entity_types: Optional[List[EntityType]] = None,
        limit: int = 20,
    ) -> List[Entity]:
        """
        搜索实体

        Args:
            query: 搜索关键词
            entity_types: 限制的实体类型
            limit: 限制数量

        Returns:
            实体列表
        """
        with self._cursor() as cursor:
            sql = """
                SELECT * FROM kg_entities
                WHERE name ILIKE %s
            """
            params = [f"%{query}%"]

            if entity_types:
                type_values = [t.value for t in entity_types]
                sql += " AND entity_type = ANY(%s)"
                params.append(type_values)

            sql += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(sql, params)
            return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

    def update_entity(self, entity: Entity) -> bool:
        """
        更新实体

        Args:
            entity: 实体对象

        Returns:
            是否更新成功
        """
        if not entity.id:
            logger.warning("无法更新没有 ID 的实体")
            return False

        entity.updated_at = datetime.now()

        with self._cursor() as cursor:
            cursor.execute(
                """
                UPDATE kg_entities SET
                    name = %s,
                    entity_type = %s,
                    properties = %s,
                    source_type = %s,
                    source_ref = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    entity.name,
                    entity.entity_type.value if isinstance(entity.entity_type, EntityType) else entity.entity_type,
                    json.dumps(entity.properties) if entity.properties else "{}",
                    entity.source_type,
                    entity.source_ref,
                    entity.updated_at,
                    entity.id,
                )
            )
            return cursor.rowcount > 0

    def update_entity_embedding(
        self,
        entity_id: int,
        embedding: List[float],
    ) -> bool:
        """
        更新实体的向量嵌入

        Args:
            entity_id: 实体 ID
            embedding: 向量嵌入

        Returns:
            是否更新成功
        """
        # 将 Python list 转换为 PostgreSQL vector 格式
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        with self._cursor() as cursor:
            cursor.execute(
                """
                UPDATE kg_entities SET
                    embedding = %s::vector,
                    updated_at = %s
                WHERE id = %s
                """,
                (embedding_str, datetime.now(), entity_id)
            )
            return cursor.rowcount > 0

    def delete_entity(self, entity_id: int) -> bool:
        """
        删除实体（同时删除相关关系）

        Args:
            entity_id: 实体 ID

        Returns:
            是否删除成功
        """
        with self._cursor() as cursor:
            # 先删除相关关系
            cursor.execute(
                """
                DELETE FROM kg_relations
                WHERE source_id = %s OR target_id = %s
                """,
                (entity_id, entity_id)
            )

            # 再删除实体
            cursor.execute(
                "DELETE FROM kg_entities WHERE id = %s",
                (entity_id,)
            )
            return cursor.rowcount > 0

    def count_entities(
        self,
        entity_type: Optional[EntityType] = None,
    ) -> int:
        """
        统计实体数量

        Args:
            entity_type: 实体类型（可选）

        Returns:
            数量
        """
        with self._cursor() as cursor:
            if entity_type:
                cursor.execute(
                    "SELECT COUNT(*) as count FROM kg_entities WHERE entity_type = %s",
                    (entity_type.value,)
                )
            else:
                cursor.execute("SELECT COUNT(*) as count FROM kg_entities")
            return cursor.fetchone()["count"]

    # ==================== 关系操作 ====================

    def create_relation(self, relation: Relation) -> Relation:
        """
        创建关系

        Args:
            relation: 关系对象

        Returns:
            创建后的关系（包含 id）
        """
        now = datetime.now()
        relation.created_at = now

        # 获取源和目标实体的 UUID
        source_entity = self.get_entity_by_id(relation.source_id)
        target_entity = self.get_entity_by_id(relation.target_id)
        if source_entity:
            relation.source_uuid = source_entity.uuid
        if target_entity:
            relation.target_uuid = target_entity.uuid

        with self._cursor() as cursor:
            # 检查是否存在相同关系
            cursor.execute(
                """
                SELECT id FROM kg_relations
                WHERE source_id = %s AND target_id = %s AND relation_type = %s
                """,
                (relation.source_id, relation.target_id, relation.relation_type.value)
            )
            existing = cursor.fetchone()
            if existing:
                relation.id = existing["id"]
                return relation

            cursor.execute(
                """
                INSERT INTO kg_relations
                (relation_type, source_id, target_id, source_uuid, target_uuid, properties, weight, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    relation.relation_type.value if isinstance(relation.relation_type, RelationType) else relation.relation_type,
                    relation.source_id,
                    relation.target_id,
                    relation.source_uuid,
                    relation.target_uuid,
                    json.dumps(relation.properties) if relation.properties else "{}",
                    relation.weight,
                    relation.created_at,
                )
            )
            relation.id = cursor.fetchone()["id"]

        return relation

    def create_relations_batch(self, relations: List[Relation]) -> List[Relation]:
        """
        批量创建关系

        Args:
            relations: 关系列表

        Returns:
            创建后的关系列表
        """
        results = []
        for relation in relations:
            created = self.create_relation(relation)
            results.append(created)
        return results

    def get_relation_by_id(self, relation_id: int) -> Optional[Relation]:
        """
        通过 ID 获取关系

        Args:
            relation_id: 关系 ID

        Returns:
            关系对象或 None
        """
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM kg_relations WHERE id = %s",
                (relation_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_relation(dict(row))
        return None

    def get_relations_by_entity(
        self,
        entity_id: int,
        direction: str = "both",  # "outgoing", "incoming", "both"
        relation_types: Optional[List[RelationType]] = None,
    ) -> List[Relation]:
        """
        获取实体的关系

        Args:
            entity_id: 实体 ID
            direction: 方向（outgoing: 出边, incoming: 入边, both: 双向）
            relation_types: 限制的关系类型

        Returns:
            关系列表
        """
        with self._cursor() as cursor:
            conditions = []
            params = []

            if direction == "outgoing":
                conditions.append("source_id = %s")
                params.append(entity_id)
            elif direction == "incoming":
                conditions.append("target_id = %s")
                params.append(entity_id)
            else:  # both
                conditions.append("(source_id = %s OR target_id = %s)")
                params.extend([entity_id, entity_id])

            if relation_types:
                type_values = [t.value for t in relation_types]
                conditions.append("relation_type = ANY(%s)")
                params.append(type_values)

            sql = f"""
                SELECT * FROM kg_relations
                WHERE {' AND '.join(conditions)}
                ORDER BY created_at DESC
            """

            cursor.execute(sql, params)
            return [self._row_to_relation(dict(row)) for row in cursor.fetchall()]

    def get_relations_between(
        self,
        source_id: int,
        target_id: int,
    ) -> List[Relation]:
        """
        获取两个实体之间的所有关系

        Args:
            source_id: 源实体 ID
            target_id: 目标实体 ID

        Returns:
            关系列表
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM kg_relations
                WHERE (source_id = %s AND target_id = %s)
                   OR (source_id = %s AND target_id = %s)
                """,
                (source_id, target_id, target_id, source_id)
            )
            return [self._row_to_relation(dict(row)) for row in cursor.fetchall()]

    def update_relation(self, relation: Relation) -> bool:
        """
        更新关系

        Args:
            relation: 关系对象

        Returns:
            是否更新成功
        """
        if not relation.id:
            logger.warning("无法更新没有 ID 的关系")
            return False

        with self._cursor() as cursor:
            cursor.execute(
                """
                UPDATE kg_relations SET
                    relation_type = %s,
                    properties = %s,
                    weight = %s
                WHERE id = %s
                """,
                (
                    relation.relation_type.value if isinstance(relation.relation_type, RelationType) else relation.relation_type,
                    json.dumps(relation.properties) if relation.properties else "{}",
                    relation.weight,
                    relation.id,
                )
            )
            return cursor.rowcount > 0

    def delete_relation(self, relation_id: int) -> bool:
        """
        删除关系

        Args:
            relation_id: 关系 ID

        Returns:
            是否删除成功
        """
        with self._cursor() as cursor:
            cursor.execute(
                "DELETE FROM kg_relations WHERE id = %s",
                (relation_id,)
            )
            return cursor.rowcount > 0

    def count_relations(
        self,
        relation_type: Optional[RelationType] = None,
    ) -> int:
        """
        统计关系数量

        Args:
            relation_type: 关系类型（可选）

        Returns:
            数量
        """
        with self._cursor() as cursor:
            if relation_type:
                cursor.execute(
                    "SELECT COUNT(*) as count FROM kg_relations WHERE relation_type = %s",
                    (relation_type.value,)
                )
            else:
                cursor.execute("SELECT COUNT(*) as count FROM kg_relations")
            return cursor.fetchone()["count"]

    # ==================== 三元组操作 ====================

    def save_triple(self, triple: Triple) -> Tuple[Entity, Entity, Relation]:
        """
        保存三元组（自动创建实体和关系）

        Args:
            triple: 三元组

        Returns:
            (主语实体, 宾语实体, 关系)
        """
        # 创建或获取主语实体
        subject_entity = self.get_entity_by_name(triple.subject, triple.subject_type)
        if not subject_entity:
            subject_entity = self.create_entity(Entity(
                entity_type=triple.subject_type,
                name=triple.subject,
                source_type="llm_extracted",
            ))

        # 创建或获取宾语实体
        object_entity = self.get_entity_by_name(triple.object, triple.object_type)
        if not object_entity:
            object_entity = self.create_entity(Entity(
                entity_type=triple.object_type,
                name=triple.object,
                source_type="llm_extracted",
            ))

        # 确保实体 ID 有效
        if subject_entity.id is None or object_entity.id is None:
            raise ValueError("无法创建关系: 实体 ID 无效")

        # 创建关系
        relation = self.create_relation(Relation(
            relation_type=triple.predicate,
            source_id=subject_entity.id,
            target_id=object_entity.id,
            properties={
                "confidence": triple.confidence,
                "context": triple.context,
            },
            weight=triple.confidence,
        ))

        return subject_entity, object_entity, relation

    def save_triples_batch(
        self,
        triples: List[Triple],
    ) -> List[Tuple[Entity, Entity, Relation]]:
        """
        批量保存三元组

        Args:
            triples: 三元组列表

        Returns:
            (主语实体, 宾语实体, 关系) 列表
        """
        results = []
        for triple in triples:
            result = self.save_triple(triple)
            results.append(result)
        return results

    # ==================== 辅助方法 ====================

    def _row_to_entity(self, row: Dict[str, Any]) -> Entity:
        """将数据库行转换为实体"""
        entity_type = row.get("entity_type", "concept")
        if isinstance(entity_type, str):
            try:
                entity_type = EntityType(entity_type)
            except ValueError:
                entity_type = EntityType.CONCEPT

        properties = row.get("properties", {})
        if isinstance(properties, str):
            properties = json.loads(properties)

        return Entity(
            id=row.get("id"),
            uuid=row.get("uuid"),
            entity_type=entity_type,
            name=row.get("name", ""),
            properties=properties,
            embedding=row.get("embedding"),
            source_type=row.get("source_type", "manual"),
            source_ref=row.get("source_ref", ""),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _row_to_relation(self, row: Dict[str, Any]) -> Relation:
        """将数据库行转换为关系"""
        relation_type = row.get("relation_type", "related_to")
        if isinstance(relation_type, str):
            try:
                relation_type = RelationType(relation_type)
            except ValueError:
                relation_type = RelationType.RELATED_TO

        properties = row.get("properties", {})
        if isinstance(properties, str):
            properties = json.loads(properties)

        return Relation(
            id=row.get("id"),
            relation_type=relation_type,
            source_id=row.get("source_id", 0),
            target_id=row.get("target_id", 0),
            source_uuid=row.get("source_uuid"),
            target_uuid=row.get("target_uuid"),
            properties=properties,
            weight=row.get("weight", 1.0),
            created_at=row.get("created_at"),
        )


# ==================== 单例访问 ====================

def get_kg_store() -> KnowledgeGraphStore:
    """获取知识图谱存储单例"""
    return get_store_instance(KnowledgeGraphStore, "KnowledgeGraphStore")
