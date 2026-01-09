"""
知识图谱查询层

提供图谱查询能力:
- get_related_entities: 获取相关实体
- get_entity_context: 获取实体上下文（邻居）
- find_path: 查找两个实体间的路径
- semantic_search: 语义搜索实体

继承 KnowledgeGraphStore 的存储能力，增加图遍历查询。
"""

import logging
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from ..base.store import get_store_instance
from .models import (
    Entity,
    EntityType,
    EntityWithNeighbors,
    GraphPath,
    Relation,
    RelationType,
)
from .store import KnowledgeGraphStore, get_kg_store

logger = logging.getLogger(__name__)


class KnowledgeGraphQuery:
    """
    知识图谱查询

    提供图遍历和语义搜索能力。

    Example:
        query = get_kg_query()

        # 获取相关实体
        entities = query.get_related_entities(entity_id=1, depth=2)

        # 获取实体上下文
        context = query.get_entity_context(entity_id=1)

        # 查找路径
        path = query.find_path(source_id=1, target_id=2)

        # 语义搜索
        results = query.semantic_search("动量因子", limit=10)
    """

    def __init__(self, store: Optional[KnowledgeGraphStore] = None):
        """
        初始化查询器

        Args:
            store: 图谱存储实例，None 则使用全局单例
        """
        self.store = store or get_kg_store()

    # ==================== 图遍历查询 ====================

    def get_related_entities(
        self,
        entity_id: int,
        depth: int = 1,
        relation_types: Optional[List[RelationType]] = None,
        entity_types: Optional[List[EntityType]] = None,
        direction: str = "both",
        limit: int = 100,
    ) -> List[Entity]:
        """
        获取与指定实体相关的实体

        通过 BFS 遍历图谱，获取指定深度内的所有相关实体。

        Args:
            entity_id: 起始实体 ID
            depth: 遍历深度（1 表示直接邻居，2 表示邻居的邻居...）
            relation_types: 限制的关系类型
            entity_types: 限制的实体类型
            direction: 遍历方向（outgoing: 出边, incoming: 入边, both: 双向）
            limit: 最大返回数量

        Returns:
            相关实体列表
        """
        if depth < 1:
            return []

        visited: Set[int] = {entity_id}
        result: List[Entity] = []
        queue: deque[Tuple[int, int]] = deque([(entity_id, 0)])  # (entity_id, current_depth)

        while queue and len(result) < limit:
            current_id, current_depth = queue.popleft()

            if current_depth >= depth:
                continue

            # 获取当前实体的关系
            relations = self.store.get_relations_by_entity(
                entity_id=current_id,
                direction=direction,
                relation_types=relation_types,
            )

            for relation in relations:
                # 确定邻居实体 ID
                neighbor_id = (
                    relation.target_id
                    if relation.source_id == current_id
                    else relation.source_id
                )

                if neighbor_id in visited:
                    continue

                visited.add(neighbor_id)

                # 获取邻居实体
                neighbor = self.store.get_entity_by_id(neighbor_id)
                if not neighbor:
                    continue

                # 类型过滤
                if entity_types and neighbor.entity_type not in entity_types:
                    continue

                result.append(neighbor)

                # 继续遍历
                if current_depth + 1 < depth:
                    queue.append((neighbor_id, current_depth + 1))

        return result[:limit]

    def get_entity_context(
        self,
        entity_id: int,
        include_properties: bool = True,
    ) -> Optional[EntityWithNeighbors]:
        """
        获取实体的上下文（包含邻居信息）

        Args:
            entity_id: 实体 ID
            include_properties: 是否包含详细属性

        Returns:
            带邻居的实体对象
        """
        entity = self.store.get_entity_by_id(entity_id)
        if not entity:
            return None

        # 获取入边（指向此实体的关系）
        incoming_relations = self.store.get_relations_by_entity(
            entity_id=entity_id,
            direction="incoming",
        )
        incoming: List[Tuple[Relation, Entity]] = []
        for relation in incoming_relations:
            source = self.store.get_entity_by_id(relation.source_id)
            if source:
                incoming.append((relation, source))

        # 获取出边（从此实体出发的关系）
        outgoing_relations = self.store.get_relations_by_entity(
            entity_id=entity_id,
            direction="outgoing",
        )
        outgoing: List[Tuple[Relation, Entity]] = []
        for relation in outgoing_relations:
            target = self.store.get_entity_by_id(relation.target_id)
            if target:
                outgoing.append((relation, target))

        return EntityWithNeighbors(
            entity=entity,
            incoming=incoming,
            outgoing=outgoing,
        )

    def find_path(
        self,
        source_id: int,
        target_id: int,
        max_depth: int = 5,
        relation_types: Optional[List[RelationType]] = None,
    ) -> Optional[GraphPath]:
        """
        查找两个实体之间的最短路径

        使用 BFS 查找最短路径。

        Args:
            source_id: 起始实体 ID
            target_id: 目标实体 ID
            max_depth: 最大搜索深度
            relation_types: 限制的关系类型

        Returns:
            路径对象，未找到返回 None
        """
        if source_id == target_id:
            entity = self.store.get_entity_by_id(source_id)
            if entity:
                return GraphPath(entities=[entity], relations=[])
            return None

        # BFS 查找路径
        visited: Set[int] = {source_id}
        # 队列元素: (current_id, path_entities, path_relations)
        queue: deque[Tuple[int, List[Entity], List[Relation]]] = deque()

        source_entity = self.store.get_entity_by_id(source_id)
        if not source_entity:
            return None

        queue.append((source_id, [source_entity], []))

        while queue:
            current_id, path_entities, path_relations = queue.popleft()

            if len(path_relations) >= max_depth:
                continue

            # 获取当前实体的所有关系
            relations = self.store.get_relations_by_entity(
                entity_id=current_id,
                direction="both",
                relation_types=relation_types,
            )

            for relation in relations:
                # 确定邻居实体 ID
                neighbor_id = (
                    relation.target_id
                    if relation.source_id == current_id
                    else relation.source_id
                )

                if neighbor_id in visited:
                    continue

                visited.add(neighbor_id)

                neighbor = self.store.get_entity_by_id(neighbor_id)
                if not neighbor:
                    continue

                new_entities = path_entities + [neighbor]
                new_relations = path_relations + [relation]

                # 找到目标
                if neighbor_id == target_id:
                    return GraphPath(
                        entities=new_entities,
                        relations=new_relations,
                    )

                # 继续搜索
                queue.append((neighbor_id, new_entities, new_relations))

        return None

    def find_all_paths(
        self,
        source_id: int,
        target_id: int,
        max_depth: int = 3,
        max_paths: int = 10,
        relation_types: Optional[List[RelationType]] = None,
    ) -> List[GraphPath]:
        """
        查找两个实体之间的所有路径

        使用 DFS 查找所有路径（限制最大深度和路径数量）。

        Args:
            source_id: 起始实体 ID
            target_id: 目标实体 ID
            max_depth: 最大搜索深度
            max_paths: 最大路径数量
            relation_types: 限制的关系类型

        Returns:
            路径列表
        """
        paths: List[GraphPath] = []
        source_entity = self.store.get_entity_by_id(source_id)
        if not source_entity:
            return paths

        def dfs(
            current_id: int,
            visited: Set[int],
            path_entities: List[Entity],
            path_relations: List[Relation],
        ):
            if len(paths) >= max_paths:
                return

            if current_id == target_id:
                paths.append(GraphPath(
                    entities=list(path_entities),
                    relations=list(path_relations),
                ))
                return

            if len(path_relations) >= max_depth:
                return

            relations = self.store.get_relations_by_entity(
                entity_id=current_id,
                direction="both",
                relation_types=relation_types,
            )

            for relation in relations:
                neighbor_id = (
                    relation.target_id
                    if relation.source_id == current_id
                    else relation.source_id
                )

                if neighbor_id in visited:
                    continue

                neighbor = self.store.get_entity_by_id(neighbor_id)
                if not neighbor:
                    continue

                visited.add(neighbor_id)
                path_entities.append(neighbor)
                path_relations.append(relation)

                dfs(neighbor_id, visited, path_entities, path_relations)

                path_entities.pop()
                path_relations.pop()
                visited.remove(neighbor_id)

        visited = {source_id}
        dfs(source_id, visited, [source_entity], [])

        return paths

    # ==================== 语义搜索 ====================

    def semantic_search(
        self,
        query: str,
        entity_types: Optional[List[EntityType]] = None,
        limit: int = 20,
    ) -> List[Entity]:
        """
        语义搜索实体

        目前使用文本匹配，后续可扩展为向量搜索。

        Args:
            query: 搜索查询
            entity_types: 限制的实体类型
            limit: 最大返回数量

        Returns:
            匹配的实体列表
        """
        return self.store.search_entities(
            query=query,
            entity_types=entity_types,
            limit=limit,
        )

    def semantic_search_by_embedding(
        self,
        embedding: List[float],
        entity_types: Optional[List[EntityType]] = None,
        limit: int = 20,
        threshold: float = 0.7,
    ) -> List[Tuple[Entity, float]]:
        """
        基于向量嵌入的语义搜索

        使用 pgvector 进行近似最近邻搜索。

        Args:
            embedding: 查询向量
            entity_types: 限制的实体类型
            limit: 最大返回数量
            threshold: 相似度阈值

        Returns:
            (实体, 相似度) 元组列表
        """
        # 将 Python list 转换为 PostgreSQL vector 格式
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        with self.store._cursor() as cursor:
            # 构建查询 - 使用子查询来支持 HAVING
            sql = """
                SELECT * FROM (
                    SELECT *,
                           1 - (embedding <=> %s::vector) as similarity
                    FROM kg_entities
                    WHERE embedding IS NOT NULL
            """
            params: List[Any] = [embedding_str]

            if entity_types:
                type_values = [t.value for t in entity_types]
                sql += " AND entity_type = ANY(%s)"
                params.append(type_values)

            sql += """
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                ) sub
                WHERE similarity >= %s
            """
            params.extend([embedding_str, limit, threshold])

            try:
                cursor.execute(sql, params)
                results = []
                for row in cursor.fetchall():
                    entity = self.store._row_to_entity(dict(row))
                    similarity = row.get("similarity", 0.0)
                    results.append((entity, similarity))
                return results
            except Exception as e:
                logger.warning(f"向量搜索失败: {e}")
                return []

    # ==================== 聚合查询 ====================

    def get_entity_degree(
        self,
        entity_id: int,
        direction: str = "both",
    ) -> int:
        """
        获取实体的度数（连接数）

        Args:
            entity_id: 实体 ID
            direction: 方向（outgoing, incoming, both）

        Returns:
            度数
        """
        relations = self.store.get_relations_by_entity(
            entity_id=entity_id,
            direction=direction,
        )
        return len(relations)

    def get_common_neighbors(
        self,
        entity_id_1: int,
        entity_id_2: int,
    ) -> List[Entity]:
        """
        获取两个实体的共同邻居

        Args:
            entity_id_1: 第一个实体 ID
            entity_id_2: 第二个实体 ID

        Returns:
            共同邻居实体列表
        """
        neighbors_1 = set()
        neighbors_2 = set()

        # 获取实体1的邻居
        for relation in self.store.get_relations_by_entity(entity_id_1, "both"):
            neighbor_id = (
                relation.target_id
                if relation.source_id == entity_id_1
                else relation.source_id
            )
            neighbors_1.add(neighbor_id)

        # 获取实体2的邻居
        for relation in self.store.get_relations_by_entity(entity_id_2, "both"):
            neighbor_id = (
                relation.target_id
                if relation.source_id == entity_id_2
                else relation.source_id
            )
            neighbors_2.add(neighbor_id)

        # 找交集
        common_ids = neighbors_1 & neighbors_2
        common_entities = []
        for entity_id in common_ids:
            entity = self.store.get_entity_by_id(entity_id)
            if entity:
                common_entities.append(entity)

        return common_entities

    def get_entities_by_relation_pattern(
        self,
        source_type: Optional[EntityType] = None,
        relation_type: Optional[RelationType] = None,
        target_type: Optional[EntityType] = None,
        limit: int = 100,
    ) -> List[Tuple[Entity, Relation, Entity]]:
        """
        按关系模式查询三元组

        查找符合 (source_type) -[relation_type]-> (target_type) 模式的三元组。

        Args:
            source_type: 源实体类型（可选）
            relation_type: 关系类型（可选）
            target_type: 目标实体类型（可选）
            limit: 最大返回数量

        Returns:
            (源实体, 关系, 目标实体) 三元组列表
        """
        with self.store._cursor() as cursor:
            sql = """
                SELECT r.*,
                       s.id as s_id, s.uuid as s_uuid, s.entity_type as s_entity_type,
                       s.name as s_name, s.properties as s_properties,
                       s.source_type as s_source_type, s.source_ref as s_source_ref,
                       s.created_at as s_created_at, s.updated_at as s_updated_at,
                       t.id as t_id, t.uuid as t_uuid, t.entity_type as t_entity_type,
                       t.name as t_name, t.properties as t_properties,
                       t.source_type as t_source_type, t.source_ref as t_source_ref,
                       t.created_at as t_created_at, t.updated_at as t_updated_at
                FROM kg_relations r
                JOIN kg_entities s ON r.source_id = s.id
                JOIN kg_entities t ON r.target_id = t.id
                WHERE 1=1
            """
            params: List[Any] = []

            if source_type:
                sql += " AND s.entity_type = %s"
                params.append(source_type.value)

            if relation_type:
                sql += " AND r.relation_type = %s"
                params.append(relation_type.value)

            if target_type:
                sql += " AND t.entity_type = %s"
                params.append(target_type.value)

            sql += " ORDER BY r.created_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                # 构建源实体
                source = self.store._row_to_entity({
                    "id": row_dict["s_id"],
                    "uuid": row_dict["s_uuid"],
                    "entity_type": row_dict["s_entity_type"],
                    "name": row_dict["s_name"],
                    "properties": row_dict["s_properties"],
                    "source_type": row_dict["s_source_type"],
                    "source_ref": row_dict["s_source_ref"],
                    "created_at": row_dict["s_created_at"],
                    "updated_at": row_dict["s_updated_at"],
                })
                # 构建目标实体
                target = self.store._row_to_entity({
                    "id": row_dict["t_id"],
                    "uuid": row_dict["t_uuid"],
                    "entity_type": row_dict["t_entity_type"],
                    "name": row_dict["t_name"],
                    "properties": row_dict["t_properties"],
                    "source_type": row_dict["t_source_type"],
                    "source_ref": row_dict["t_source_ref"],
                    "created_at": row_dict["t_created_at"],
                    "updated_at": row_dict["t_updated_at"],
                })
                # 构建关系
                relation = self.store._row_to_relation(row_dict)
                results.append((source, relation, target))

            return results

    # ==================== 统计查询 ====================

    def get_graph_stats(self) -> Dict[str, Any]:
        """
        获取图谱统计信息

        Returns:
            统计信息字典
        """
        entity_count = self.store.count_entities()
        relation_count = self.store.count_relations()

        # 各类型实体数量
        entity_type_counts = {}
        for entity_type in EntityType:
            count = self.store.count_entities(entity_type)
            if count > 0:
                entity_type_counts[entity_type.value] = count

        # 各类型关系数量
        relation_type_counts = {}
        for relation_type in RelationType:
            count = self.store.count_relations(relation_type)
            if count > 0:
                relation_type_counts[relation_type.value] = count

        return {
            "total_entities": entity_count,
            "total_relations": relation_count,
            "entity_types": entity_type_counts,
            "relation_types": relation_type_counts,
        }

    def get_most_connected_entities(
        self,
        entity_type: Optional[EntityType] = None,
        limit: int = 10,
    ) -> List[Tuple[Entity, int]]:
        """
        获取连接最多的实体

        Args:
            entity_type: 限制的实体类型
            limit: 最大返回数量

        Returns:
            (实体, 度数) 元组列表
        """
        with self.store._cursor() as cursor:
            sql = """
                SELECT e.*,
                       (SELECT COUNT(*) FROM kg_relations r
                        WHERE r.source_id = e.id OR r.target_id = e.id) as degree
                FROM kg_entities e
            """
            params: List[Any] = []

            if entity_type:
                sql += " WHERE e.entity_type = %s"
                params.append(entity_type.value)

            sql += " ORDER BY degree DESC LIMIT %s"
            params.append(limit)

            cursor.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                degree = row_dict.pop("degree", 0)
                entity = self.store._row_to_entity(row_dict)
                results.append((entity, degree))

            return results


# ==================== 单例访问 ====================

def get_kg_query() -> KnowledgeGraphQuery:
    """获取知识图谱查询单例"""
    return get_store_instance(KnowledgeGraphQuery, "KnowledgeGraphQuery")
