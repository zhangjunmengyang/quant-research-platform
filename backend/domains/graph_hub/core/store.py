"""
Neo4j 图存储层

提供图数据库的边、节点、链路追溯等操作。
使用单例模式管理 Neo4j 连接。
"""

import contextlib
import json
import logging
import os
import threading
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import (
    AuthError,
    Neo4jError,
    ServiceUnavailable,
)

from .models import (
    GraphEdge,
    LEGACY_RELATION_MAPPING,
    LineageNode,
    LineageResult,
    NodeType,
    PathResult,
    RelationType,
)

logger = logging.getLogger(__name__)


class GraphStore:
    """
    Neo4j 图存储层

    提供图数据库操作，包括边管理、链路追溯、标签操作等。
    使用单例模式，通过 get_graph_store() 获取实例。

    环境变量配置:
        NEO4J_URI: Neo4j 连接地址，默认 bolt://localhost:7687
        NEO4J_USER: 用户名，默认 neo4j
        NEO4J_PASSWORD: 密码，默认 quant123
    """

    _instance: "GraphStore | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "GraphStore":
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        """初始化 Neo4j 连接"""
        if self._initialized:
            return

        self._uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._user = os.getenv("NEO4J_USER", "neo4j")
        self._password = os.getenv("NEO4J_PASSWORD", "quant123")
        self._driver = None

        self._initialized = True
        logger.info(f"GraphStore 初始化完成: {self._uri}")

    def _get_driver(self):
        """获取 Neo4j 驱动（懒加载）"""
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    self._uri,
                    auth=(self._user, self._password),
                    max_connection_lifetime=3600,
                    max_connection_pool_size=50,
                )
            except Exception as e:
                logger.error(f"Neo4j 驱动创建失败: {e}")
                return None
        return self._driver

    @contextmanager
    def _session(self) -> Generator:
        """
        获取 Neo4j session 的上下文管理器

        Yields:
            Neo4j session，连接失败时 yield None
        """
        driver = self._get_driver()
        if driver is None:
            yield None
            return

        session = None
        try:
            session = driver.session()
            yield session
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Neo4j 连接失败: {e}")
            yield None
        except Exception as e:
            logger.error(f"Neo4j session 异常: {e}")
            yield None
        finally:
            if session is not None:
                with contextlib.suppress(Exception):
                    session.close()

    def close(self) -> None:
        """关闭 Neo4j 连接"""
        if self._driver is not None:
            try:
                self._driver.close()
                self._driver = None
                logger.info("Neo4j 连接已关闭")
            except Exception as e:
                logger.warning(f"关闭 Neo4j 连接时出错: {e}")

    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            True 表示连接正常，False 表示连接失败
        """
        with self._session() as session:
            if session is None:
                return False
            try:
                result = session.run("RETURN 1 as n")
                record = result.single()
                return record is not None and record["n"] == 1
            except Exception as e:
                logger.error(f"健康检查失败: {e}")
                return False

    # ==================== 边操作 ====================

    def create_edge(self, edge: GraphEdge) -> bool:
        """
        创建边

        使用 MERGE 语义，如果边已存在则更新属性。
        subtype 存储为关系属性。

        Args:
            edge: GraphEdge 对象

        Returns:
            是否创建/更新成功
        """
        with self._session() as session:
            if session is None:
                logger.warning("Neo4j 不可用，跳过创建边")
                return False

            try:
                # 获取标签和关系类型
                source_label = self._get_label(edge.source_type)
                target_label = self._get_label(edge.target_type)
                relation_type = self._get_relation_type(edge.relation)

                # 序列化 metadata
                metadata_json = json.dumps(edge.metadata) if edge.metadata else "{}"

                cypher = f"""
                MERGE (s:{source_label} {{id: $source_id}})
                MERGE (t:{target_label} {{id: $target_id}})
                MERGE (s)-[r:{relation_type}]->(t)
                SET r.created_at = datetime(),
                    r.subtype = $subtype,
                    r.is_bidirectional = $is_bidirectional,
                    r.metadata = $metadata
                RETURN r
                """

                result = session.run(
                    cypher,
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    subtype=edge.subtype,
                    is_bidirectional=edge.is_bidirectional,
                    metadata=metadata_json,
                )

                record = result.single()
                if record is not None:
                    subtype_str = f":{edge.subtype}" if edge.subtype else ""
                    logger.info(
                        f"创建边成功: {source_label}:{edge.source_id} "
                        f"-[{relation_type}{subtype_str}]-> {target_label}:{edge.target_id}"
                    )
                    return True
                return False

            except Neo4jError as e:
                logger.error(f"创建边失败: {e}")
                return False

    def delete_edge(
        self,
        source_type: NodeType,
        source_id: str,
        target_type: NodeType,
        target_id: str,
        relation: RelationType,
    ) -> bool:
        """
        删除边

        Args:
            source_type: 源节点类型
            source_id: 源节点 ID
            target_type: 目标节点类型
            target_id: 目标节点 ID
            relation: 关系类型

        Returns:
            是否删除成功
        """
        with self._session() as session:
            if session is None:
                logger.warning("Neo4j 不可用，跳过删除边")
                return False

            try:
                source_label = self._get_label(source_type)
                target_label = self._get_label(target_type)
                relation_type = self._get_relation_type(relation)

                cypher = f"""
                MATCH (s:{source_label} {{id: $source_id}})
                      -[r:{relation_type}]->
                      (t:{target_label} {{id: $target_id}})
                DELETE r
                RETURN count(r) as deleted
                """

                result = session.run(
                    cypher,
                    source_id=source_id,
                    target_id=target_id,
                )

                record = result.single()
                deleted = record["deleted"] if record else 0
                if deleted > 0:
                    logger.info(
                        f"删除边成功: {source_label}:{source_id} "
                        f"-[{relation_type}]-> {target_label}:{target_id}"
                    )
                    return True
                return False

            except Neo4jError as e:
                logger.error(f"删除边失败: {e}")
                return False

    def get_edges_by_entity(
        self,
        entity_type: NodeType,
        entity_id: str,
        include_bidirectional: bool = True,
    ) -> list[GraphEdge]:
        """
        获取实体的所有关联边（出边 + 入边）

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            include_bidirectional: 是否包含入边（实体作为目标的边）

        Returns:
            GraphEdge 列表
        """
        with self._session() as session:
            if session is None:
                return []

            try:
                label = self._get_label(entity_type)
                edges = []

                # 获取出边（实体作为源）
                cypher_out = f"""
                MATCH (s:{label} {{id: $entity_id}})-[r]->(t)
                RETURN labels(s)[0] as source_type,
                       s.id as source_id,
                       labels(t)[0] as target_type,
                       t.id as target_id,
                       type(r) as relation,
                       r.subtype as subtype,
                       r.is_bidirectional as is_bidirectional,
                       r.metadata as metadata,
                       r.created_at as created_at
                """

                result = session.run(cypher_out, entity_id=entity_id)
                for record in result:
                    edge = self._record_to_edge(record)
                    if edge:
                        edges.append(edge)

                # 获取入边（实体作为目标）
                if include_bidirectional:
                    cypher_in = f"""
                    MATCH (s)-[r]->(t:{label} {{id: $entity_id}})
                    RETURN labels(s)[0] as source_type,
                           s.id as source_id,
                           labels(t)[0] as target_type,
                           t.id as target_id,
                           type(r) as relation,
                           r.subtype as subtype,
                           r.is_bidirectional as is_bidirectional,
                           r.metadata as metadata,
                           r.created_at as created_at
                    """

                    result = session.run(cypher_in, entity_id=entity_id)
                    for record in result:
                        edge = self._record_to_edge(record)
                        if edge:
                            edges.append(edge)

                return edges

            except Neo4jError as e:
                logger.error(f"获取实体边失败: {e}")
                return []

    def get_edges_to_entity(
        self,
        entity_type: NodeType,
        entity_id: str,
    ) -> list[GraphEdge]:
        """
        获取指向实体的所有边（作为目标的边）

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID

        Returns:
            GraphEdge 列表
        """
        with self._session() as session:
            if session is None:
                return []

            try:
                label = self._get_label(entity_type)

                cypher = f"""
                MATCH (s)-[r]->(t:{label} {{id: $entity_id}})
                RETURN labels(s)[0] as source_type,
                       s.id as source_id,
                       labels(t)[0] as target_type,
                       t.id as target_id,
                       type(r) as relation,
                       r.subtype as subtype,
                       r.is_bidirectional as is_bidirectional,
                       r.metadata as metadata,
                       r.created_at as created_at
                """

                result = session.run(cypher, entity_id=entity_id)
                edges = []
                for record in result:
                    edge = self._record_to_edge(record)
                    if edge:
                        edges.append(edge)
                return edges

            except Neo4jError as e:
                logger.error(f"获取指向实体的边失败: {e}")
                return []

    def exists(
        self,
        source_type: NodeType,
        source_id: str,
        target_type: NodeType,
        target_id: str,
        relation: RelationType,
    ) -> bool:
        """
        检查边是否存在

        Args:
            source_type: 源节点类型
            source_id: 源节点 ID
            target_type: 目标节点类型
            target_id: 目标节点 ID
            relation: 关系类型

        Returns:
            是否存在
        """
        with self._session() as session:
            if session is None:
                return False

            try:
                source_label = self._get_label(source_type)
                target_label = self._get_label(target_type)
                relation_type = self._get_relation_type(relation)

                cypher = f"""
                MATCH (s:{source_label} {{id: $source_id}})
                      -[r:{relation_type}]->
                      (t:{target_label} {{id: $target_id}})
                RETURN count(r) as cnt
                """

                result = session.run(
                    cypher,
                    source_id=source_id,
                    target_id=target_id,
                )

                record = result.single()
                return record is not None and record["cnt"] > 0

            except Neo4jError as e:
                logger.error(f"检查边存在失败: {e}")
                return False

    def delete_edges_by_entity(
        self,
        entity_type: NodeType,
        entity_id: str,
    ) -> int:
        """
        删除与实体相关的所有边（级联删除）

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID

        Returns:
            删除的边数量
        """
        with self._session() as session:
            if session is None:
                return 0

            try:
                label = self._get_label(entity_type)

                # 删除所有出边和入边
                cypher = f"""
                MATCH (n:{label} {{id: $entity_id}})
                OPTIONAL MATCH (n)-[r1]->()
                OPTIONAL MATCH ()-[r2]->(n)
                WITH n, collect(r1) + collect(r2) as rels
                UNWIND rels as r
                DELETE r
                RETURN count(r) as deleted
                """

                result = session.run(cypher, entity_id=entity_id)
                record = result.single()
                deleted = record["deleted"] if record else 0

                if deleted > 0:
                    logger.info(
                        f"级联删除边: {label}:{entity_id}, 共 {deleted} 条"
                    )
                return deleted

            except Neo4jError as e:
                logger.error(f"级联删除边失败: {e}")
                return 0

    # ==================== 图查询 ====================

    def trace_lineage(
        self,
        entity_type: NodeType,
        entity_id: str,
        direction: str = "backward",
        max_depth: int = 5,
    ) -> LineageResult:
        """
        链路追溯

        Args:
            entity_type: 起始实体类型
            entity_id: 起始实体 ID
            direction: 追溯方向
                - "backward": 向上追溯（查找该实体依赖的上游实体）
                - "forward": 向下追溯（查找依赖该实体的下游实体）
            max_depth: 最大追溯深度

        Returns:
            LineageResult 链路追溯结果
        """
        result = LineageResult(
            start_type=entity_type,
            start_id=entity_id,
            direction=direction,
            max_depth=max_depth,
            nodes=[],
        )

        with self._session() as session:
            if session is None:
                return result

            try:
                label = self._get_label(entity_type)

                if direction == "backward":
                    # 向上追溯: 从当前节点出发，沿出边方向
                    cypher = f"""
                    MATCH path = (start:{label} {{id: $entity_id}})-[*1..{max_depth}]->(end)
                    UNWIND range(1, length(path)) as idx
                    WITH path, idx,
                         nodes(path)[idx] as node,
                         relationships(path)[idx-1] as rel
                    RETURN idx as depth,
                           labels(node)[0] as node_type,
                           node.id as node_id,
                           type(rel) as relation,
                           rel.subtype as subtype
                    ORDER BY depth
                    """
                else:
                    # 向下追溯: 从当前节点出发，沿入边方向（反向）
                    cypher = f"""
                    MATCH path = (end)-[*1..{max_depth}]->(start:{label} {{id: $entity_id}})
                    UNWIND range(0, length(path)-1) as idx
                    WITH path, length(path) - idx as depth,
                         nodes(path)[idx] as node,
                         relationships(path)[idx] as rel
                    RETURN depth,
                           labels(node)[0] as node_type,
                           node.id as node_id,
                           type(rel) as relation,
                           rel.subtype as subtype
                    ORDER BY depth
                    """

                query_result = session.run(cypher, entity_id=entity_id)

                # 去重（同一节点可能通过多条路径到达）
                seen = set()
                for record in query_result:
                    node_key = (record["node_type"], record["node_id"])
                    if node_key in seen:
                        continue
                    seen.add(node_key)

                    relation, subtype = self._parse_relation_with_subtype(
                        record["relation"], record.get("subtype")
                    )
                    node = LineageNode(
                        depth=record["depth"],
                        node_type=self._parse_node_type(record["node_type"]),
                        node_id=record["node_id"],
                        relation=relation,
                        subtype=subtype,
                        direction=direction,
                    )
                    result.nodes.append(node)

                return result

            except Neo4jError as e:
                logger.error(f"链路追溯失败: {e}")
                return result

    def find_path(
        self,
        source_type: NodeType,
        source_id: str,
        target_type: NodeType,
        target_id: str,
        max_depth: int = 5,
    ) -> PathResult:
        """
        查找两个实体之间的最短路径

        Args:
            source_type: 起始实体类型
            source_id: 起始实体 ID
            target_type: 目标实体类型
            target_id: 目标实体 ID
            max_depth: 最大搜索深度

        Returns:
            PathResult 路径查找结果
        """
        result = PathResult(
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            paths=[],
        )

        with self._session() as session:
            if session is None:
                return result

            try:
                source_label = self._get_label(source_type)
                target_label = self._get_label(target_type)

                # 使用 shortestPath 查找最短路径（无向）
                cypher = f"""
                MATCH path = shortestPath(
                    (s:{source_label} {{id: $source_id}})-[*..{max_depth}]-(t:{target_label} {{id: $target_id}})
                )
                RETURN path
                """

                query_result = session.run(
                    cypher,
                    source_id=source_id,
                    target_id=target_id,
                )

                record = query_result.single()
                if record is not None:
                    path = record["path"]
                    path_data = []

                    # 解析路径中的节点和关系
                    nodes = list(path.nodes)
                    rels = list(path.relationships)

                    for i, node in enumerate(nodes):
                        labels = list(node.labels)
                        node_label = labels[0] if labels else "Unknown"
                        path_data.append({
                            "type": "node",
                            "label": node_label.lower(),
                            "id": node.get("id", ""),
                            "position": i,
                        })

                        if i < len(rels):
                            rel = rels[i]
                            path_data.append({
                                "type": "relationship",
                                "relation": rel.type.lower(),
                                "position": i,
                            })

                    result.paths.append(path_data)

                return result

            except Neo4jError as e:
                logger.error(f"路径查找失败: {e}")
                return result

    # ==================== 标签操作 ====================
    # 标签作为节点属性 (tags: list[str]) 存储，不再使用关系

    def add_tag(
        self,
        entity_type: NodeType,
        entity_id: str,
        tag: str,
    ) -> bool:
        """
        给实体添加标签

        将标签添加到节点的 tags 属性数组中。

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            tag: 标签名称

        Returns:
            是否添加成功
        """
        with self._session() as session:
            if session is None:
                logger.warning("Neo4j 不可用，跳过添加标签")
                return False

            try:
                label = self._get_label(entity_type)

                # 使用 COALESCE 处理 tags 不存在的情况
                # 使用集合操作确保不重复
                cypher = f"""
                MATCH (e:{label} {{id: $entity_id}})
                SET e.tags = CASE
                    WHEN e.tags IS NULL THEN [$tag]
                    WHEN NOT $tag IN e.tags THEN e.tags + $tag
                    ELSE e.tags
                END
                RETURN e.tags as tags
                """

                result = session.run(cypher, entity_id=entity_id, tag=tag)
                record = result.single()
                if record is not None:
                    logger.info(f"添加标签成功: {label}:{entity_id} <- {tag}")
                    return True
                return False

            except Neo4jError as e:
                logger.error(f"添加标签失败: {e}")
                return False

    def remove_tag(
        self,
        entity_type: NodeType,
        entity_id: str,
        tag: str,
    ) -> bool:
        """
        移除实体的标签

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            tag: 标签名称

        Returns:
            是否移除成功
        """
        with self._session() as session:
            if session is None:
                logger.warning("Neo4j 不可用，跳过移除标签")
                return False

            try:
                label = self._get_label(entity_type)

                cypher = f"""
                MATCH (e:{label} {{id: $entity_id}})
                SET e.tags = CASE
                    WHEN e.tags IS NULL THEN []
                    ELSE [t IN e.tags WHERE t <> $tag]
                END
                RETURN e.tags as tags
                """

                result = session.run(cypher, entity_id=entity_id, tag=tag)
                record = result.single()
                if record is not None:
                    logger.info(f"移除标签成功: {label}:{entity_id} -x- {tag}")
                    return True
                return False

            except Neo4jError as e:
                logger.error(f"移除标签失败: {e}")
                return False

    def get_entity_tags(
        self,
        entity_type: NodeType,
        entity_id: str,
    ) -> list[str]:
        """
        获取实体的所有标签

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID

        Returns:
            标签列表
        """
        with self._session() as session:
            if session is None:
                return []

            try:
                label = self._get_label(entity_type)

                cypher = f"""
                MATCH (e:{label} {{id: $entity_id}})
                RETURN COALESCE(e.tags, []) as tags
                """

                result = session.run(cypher, entity_id=entity_id)
                record = result.single()
                if record:
                    tags = record["tags"]
                    return sorted(tags) if tags else []
                return []

            except Neo4jError as e:
                logger.error(f"获取实体标签失败: {e}")
                return []

    def get_all_tags_by_type(
        self,
        entity_type: NodeType,
    ) -> dict[str, list[str]]:
        """
        获取指定类型所有实体的标签映射

        Args:
            entity_type: 实体类型

        Returns:
            {entity_id: [tags]} 映射
        """
        with self._session() as session:
            if session is None:
                return {}

            try:
                label = self._get_label(entity_type)

                cypher = f"""
                MATCH (e:{label})
                WHERE e.tags IS NOT NULL AND size(e.tags) > 0
                RETURN e.id as entity_id, e.tags as tags
                """

                result = session.run(cypher)
                return {
                    record["entity_id"]: sorted(record["tags"])
                    for record in result
                }

            except Neo4jError as e:
                logger.error(f"获取所有实体标签失败: {e}")
                return {}

    def get_entities_by_tag(
        self,
        tag: str,
        entity_type: NodeType | None = None,
    ) -> list[dict[str, str]]:
        """
        获取拥有指定标签的所有实体

        Args:
            tag: 标签名称
            entity_type: 可选，筛选特定类型的实体

        Returns:
            实体列表 [{"type": "factor", "id": "xxx"}, ...]
        """
        with self._session() as session:
            if session is None:
                return []

            try:
                if entity_type:
                    label = self._get_label(entity_type)
                    cypher = f"""
                    MATCH (e:{label})
                    WHERE $tag IN COALESCE(e.tags, [])
                    RETURN labels(e)[0] as type, e.id as id
                    ORDER BY e.id
                    """
                else:
                    cypher = """
                    MATCH (e)
                    WHERE $tag IN COALESCE(e.tags, []) AND NOT 'Tag' IN labels(e)
                    RETURN labels(e)[0] as type, e.id as id
                    ORDER BY type, e.id
                    """

                result = session.run(cypher, tag=tag)
                return [
                    {"type": record["type"].lower(), "id": record["id"]}
                    for record in result
                ]

            except Neo4jError as e:
                logger.error(f"按标签获取实体失败: {e}")
                return []

    def list_all_tags(self) -> list[dict[str, Any]]:
        """
        列出所有使用过的标签及其统计

        Returns:
            标签列表 [{"tag": "xxx", "count": 5}, ...]
        """
        with self._session() as session:
            if session is None:
                return []

            try:
                cypher = """
                MATCH (e)
                WHERE e.tags IS NOT NULL AND size(e.tags) > 0
                UNWIND e.tags as tag
                RETURN tag, count(e) as count
                ORDER BY count DESC, tag
                """

                result = session.run(cypher)
                return [
                    {"tag": record["tag"], "count": record["count"]}
                    for record in result
                ]

            except Neo4jError as e:
                logger.error(f"列出标签失败: {e}")
                return []

    def get_edges_by_relation(
        self,
        relation: RelationType,
        limit: int = 1000,
    ) -> list[GraphEdge]:
        """
        按关系类型获取所有边

        Args:
            relation: 关系类型
            limit: 返回数量限制

        Returns:
            GraphEdge 列表
        """
        with self._session() as session:
            if session is None:
                return []

            try:
                relation_type = self._get_relation_type(relation)

                cypher = f"""
                MATCH (s)-[r:{relation_type}]->(t)
                RETURN labels(s)[0] as source_type,
                       s.id as source_id,
                       labels(t)[0] as target_type,
                       t.id as target_id,
                       type(r) as relation,
                       r.subtype as subtype,
                       r.is_bidirectional as is_bidirectional,
                       r.metadata as metadata,
                       r.created_at as created_at
                LIMIT $limit
                """

                result = session.run(cypher, limit=limit)
                edges = []
                for record in result:
                    edge = self._record_to_edge(record)
                    if edge:
                        edges.append(edge)
                return edges

            except Neo4jError as e:
                logger.error(f"按关系类型获取边失败: {e}")
                return []

    def get_all_graph(
        self,
        node_limit: int = 500,
        edge_limit: int = 1000,
    ) -> dict[str, Any]:
        """
        获取全量图谱数据 (带数量限制)

        Args:
            node_limit: 节点数量限制
            edge_limit: 边数量限制

        Returns:
            {"nodes": [...], "edges": [...], "stats": {...}}
        """
        with self._session() as session:
            if session is None:
                return {"nodes": [], "edges": [], "stats": {}}

            try:
                # 获取所有节点 (按连接度排序，优先返回关联多的节点)
                nodes_cypher = """
                MATCH (n)
                WHERE NOT 'Tag' IN labels(n)
                OPTIONAL MATCH (n)-[r]-()
                WITH n, count(r) as degree
                ORDER BY degree DESC
                LIMIT $limit
                RETURN labels(n)[0] as type, n.id as id, degree
                """

                nodes_result = session.run(nodes_cypher, limit=node_limit)
                nodes = [
                    {
                        "type": record["type"].lower() if record["type"] else "data",
                        "id": record["id"],
                        "degree": record["degree"],
                    }
                    for record in nodes_result
                ]

                # 获取节点 ID 集合用于过滤边
                node_ids = {(n["type"], n["id"]) for n in nodes}

                # 获取所有边 (不含 Tag 节点)
                edges_cypher = """
                MATCH (s)-[r]->(t)
                WHERE NOT 'Tag' IN labels(t) AND NOT 'Tag' IN labels(s)
                RETURN labels(s)[0] as source_type,
                       s.id as source_id,
                       labels(t)[0] as target_type,
                       t.id as target_id,
                       type(r) as relation,
                       r.subtype as subtype,
                       r.is_bidirectional as is_bidirectional
                LIMIT $limit
                """

                edges_result = session.run(edges_cypher, limit=edge_limit)
                edges = []
                for record in edges_result:
                    src_type = record["source_type"].lower() if record["source_type"] else "data"
                    tgt_type = record["target_type"].lower() if record["target_type"] else "data"
                    # 只保留两端节点都在结果中的边
                    if (src_type, record["source_id"]) in node_ids and (tgt_type, record["target_id"]) in node_ids:
                        edges.append({
                            "source_type": src_type,
                            "source_id": record["source_id"],
                            "target_type": tgt_type,
                            "target_id": record["target_id"],
                            "relation": record["relation"].lower() if record["relation"] else "relates",
                            "subtype": record["subtype"] or "",
                            "is_bidirectional": record["is_bidirectional"] or False,
                        })

                # 统计信息
                stats_cypher = """
                MATCH (n)
                WHERE NOT 'Tag' IN labels(n)
                RETURN labels(n)[0] as type, count(n) as count
                ORDER BY count DESC
                """
                stats_result = session.run(stats_cypher)
                node_stats = {
                    record["type"].lower(): record["count"]
                    for record in stats_result
                    if record["type"]
                }

                edge_count = self.count_all_edges()

                return {
                    "nodes": nodes,
                    "edges": edges,
                    "stats": {
                        "total_nodes": sum(node_stats.values()),
                        "total_edges": edge_count,
                        "node_counts": node_stats,
                        "returned_nodes": len(nodes),
                        "returned_edges": len(edges),
                    },
                }

            except Neo4jError as e:
                logger.error(f"获取全量图谱失败: {e}")
                return {"nodes": [], "edges": [], "stats": {}}

    def count_all_edges(self) -> int:
        """
        统计所有边的数量

        Returns:
            边数量
        """
        with self._session() as session:
            if session is None:
                return 0

            try:
                cypher = "MATCH ()-[r]->() RETURN count(r) as count"
                result = session.run(cypher)
                record = result.single()
                return record["count"] if record else 0

            except Neo4jError as e:
                logger.error(f"统计边数量失败: {e}")
                return 0

    def get_edge_stats(self) -> list[dict[str, Any]]:
        """
        获取边的统计信息，按关系类型分组

        Returns:
            [{"relation": "derives", "count": 10}, ...]
        """
        with self._session() as session:
            if session is None:
                return []

            try:
                cypher = """
                MATCH ()-[r]->()
                RETURN type(r) as relation, count(r) as count
                ORDER BY count DESC
                """
                result = session.run(cypher)
                return [
                    {"relation": record["relation"].lower(), "count": record["count"]}
                    for record in result
                ]

            except Neo4jError as e:
                logger.error(f"获取边统计失败: {e}")
                return []

    # ==================== 工具方法 ====================

    def _get_label(self, node_type: NodeType) -> str:
        """
        获取 Neo4j 节点标签

        Args:
            node_type: 节点类型枚举

        Returns:
            标签名（首字母大写）
        """
        if isinstance(node_type, NodeType):
            return node_type.value.capitalize()
        return str(node_type).capitalize()

    def _get_relation_type(self, relation: RelationType) -> str:
        """
        获取 Neo4j 关系类型

        Args:
            relation: 关系类型枚举

        Returns:
            关系类型名（大写下划线）
        """
        if isinstance(relation, RelationType):
            return relation.value.upper()
        return str(relation).upper()

    def _parse_node_type(self, label: str) -> NodeType:
        """
        解析 Neo4j 标签为节点类型枚举

        Args:
            label: Neo4j 节点标签

        Returns:
            NodeType 枚举值
        """
        if label is None:
            return NodeType.DATA

        try:
            return NodeType(label.lower())
        except ValueError:
            return NodeType.DATA

    def _parse_relation_type(self, rel_type: str) -> RelationType:
        """
        解析 Neo4j 关系类型为枚举

        支持旧格式自动映射到新格式。

        Args:
            rel_type: Neo4j 关系类型

        Returns:
            RelationType 枚举值
        """
        if rel_type is None:
            return RelationType.RELATES

        rel_lower = rel_type.lower()

        # 先尝试直接解析新格式
        try:
            return RelationType(rel_lower)
        except ValueError:
            pass

        # 尝试旧格式映射
        if rel_lower in LEGACY_RELATION_MAPPING:
            new_rel, _ = LEGACY_RELATION_MAPPING[rel_lower]
            return RelationType(new_rel)

        # 默认返回 RELATES
        return RelationType.RELATES

    def _parse_relation_with_subtype(
        self, rel_type: str, subtype: str | None
    ) -> tuple[RelationType, str]:
        """
        解析 Neo4j 关系类型和子类型

        支持旧格式自动映射。

        Args:
            rel_type: Neo4j 关系类型
            subtype: 子类型（可能为 None）

        Returns:
            (RelationType, subtype) 元组
        """
        if rel_type is None:
            return RelationType.RELATES, subtype or ""

        rel_lower = rel_type.lower()

        # 先尝试直接解析新格式
        try:
            relation = RelationType(rel_lower)
            return relation, subtype or ""
        except ValueError:
            pass

        # 尝试旧格式映射
        if rel_lower in LEGACY_RELATION_MAPPING:
            new_rel, default_subtype = LEGACY_RELATION_MAPPING[rel_lower]
            return RelationType(new_rel), subtype or default_subtype

        # 默认返回 RELATES
        return RelationType.RELATES, subtype or ""

    def _record_to_edge(self, record) -> GraphEdge | None:
        """
        将查询记录转换为 GraphEdge

        Args:
            record: Neo4j 查询结果记录

        Returns:
            GraphEdge 对象，解析失败返回 None
        """
        try:
            # 解析 metadata
            metadata = {}
            if record["metadata"]:
                try:
                    metadata = json.loads(record["metadata"])
                except (json.JSONDecodeError, TypeError):
                    metadata = {}

            # 解析 created_at
            created_at = None
            if record["created_at"]:
                try:
                    # Neo4j datetime 转 Python datetime
                    neo4j_dt = record["created_at"]
                    if hasattr(neo4j_dt, "to_native"):
                        created_at = neo4j_dt.to_native()
                    elif isinstance(neo4j_dt, datetime):
                        created_at = neo4j_dt
                except Exception:
                    pass

            # 解析 relation 和 subtype（支持旧格式迁移）
            relation, subtype = self._parse_relation_with_subtype(
                record["relation"], record.get("subtype")
            )

            return GraphEdge(
                source_type=self._parse_node_type(record["source_type"]),
                source_id=record["source_id"],
                target_type=self._parse_node_type(record["target_type"]),
                target_id=record["target_id"],
                relation=relation,
                subtype=subtype,
                is_bidirectional=record.get("is_bidirectional", False) or False,
                metadata=metadata,
                created_at=created_at,
            )
        except Exception as e:
            logger.warning(f"解析边记录失败: {e}")
            return None


# ==================== 单例访问 ====================

_graph_store: GraphStore | None = None


def get_graph_store() -> GraphStore:
    """
    获取全局 GraphStore 实例

    Returns:
        GraphStore 单例实例
    """
    global _graph_store
    if _graph_store is None:
        _graph_store = GraphStore()
    return _graph_store
