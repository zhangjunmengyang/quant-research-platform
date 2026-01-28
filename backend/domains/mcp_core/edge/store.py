"""
知识边存储层

提供 knowledge_edges 表的 CRUD 操作。
"""

import logging
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras

from domains.mcp_core.base.store import ThreadSafeConnectionMixin

from .models import (
    KnowledgeEdge,
    EdgeEntityType,
    EdgeRelationType,
)

logger = logging.getLogger(__name__)


class EdgeStore(ThreadSafeConnectionMixin):
    """知识边存储层"""

    def __init__(self, connection_string: Optional[str] = None):
        """初始化存储层"""
        self._init_connection(connection_string)

    def create(self, edge: KnowledgeEdge) -> Optional[int]:
        """
        创建关联

        Args:
            edge: 知识边对象

        Returns:
            创建的边 ID，失败返回 None
        """
        try:
            with self._cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO knowledge_edges (
                        source_type, source_id, target_type, target_id,
                        relation, is_bidirectional, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        edge.source_type.value if isinstance(edge.source_type, EdgeEntityType) else edge.source_type,
                        edge.source_id,
                        edge.target_type.value if isinstance(edge.target_type, EdgeEntityType) else edge.target_type,
                        edge.target_id,
                        edge.relation.value if isinstance(edge.relation, EdgeRelationType) else edge.relation,
                        edge.is_bidirectional,
                        psycopg2.extras.Json(edge.metadata),
                    ),
                )
                result = cursor.fetchone()
                if result:
                    logger.info(
                        f"创建关联成功: {edge.source_type}:{edge.source_id} "
                        f"-[{edge.relation}]-> {edge.target_type}:{edge.target_id}"
                    )
                    # 触发同步到文件
                    self._trigger_edge_sync(edge)
                    return result["id"]
                return None
        except psycopg2.IntegrityError as e:
            if "knowledge_edges_unique" in str(e):
                logger.warning(f"关联已存在: {edge.source_id} -> {edge.target_id}")
            else:
                logger.error(f"创建关联失败: {e}")
            return None

    def get(self, edge_id: int) -> Optional[KnowledgeEdge]:
        """
        获取单个关联

        Args:
            edge_id: 边 ID

        Returns:
            知识边对象，不存在返回 None
        """
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM knowledge_edges WHERE id = %s",
                (edge_id,),
            )
            row = cursor.fetchone()
            if row:
                return KnowledgeEdge.from_dict(dict(row))
            return None

    def delete(self, edge_id: int) -> bool:
        """
        删除关联

        Args:
            edge_id: 边 ID

        Returns:
            是否删除成功
        """
        # 先获取 edge 信息，用于删除后触发同步
        edge = self.get(edge_id)

        with self._cursor() as cursor:
            cursor.execute(
                "DELETE FROM knowledge_edges WHERE id = %s",
                (edge_id,),
            )
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"删除关联成功: {edge_id}")
                # 触发同步
                if edge:
                    self._trigger_edge_sync(edge)
            return deleted

    def delete_by_key(
        self,
        source_type: EdgeEntityType,
        source_id: str,
        target_type: EdgeEntityType,
        target_id: str,
        relation: EdgeRelationType,
    ) -> bool:
        """
        按唯一键删除关联

        Args:
            source_type: 源实体类型
            source_id: 源实体 ID
            target_type: 目标实体类型
            target_id: 目标实体 ID
            relation: 关系类型

        Returns:
            是否删除成功
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM knowledge_edges
                WHERE source_type = %s AND source_id = %s
                AND target_type = %s AND target_id = %s
                AND relation = %s
                """,
                (
                    source_type.value if isinstance(source_type, EdgeEntityType) else source_type,
                    source_id,
                    target_type.value if isinstance(target_type, EdgeEntityType) else target_type,
                    target_id,
                    relation.value if isinstance(relation, EdgeRelationType) else relation,
                ),
            )
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(
                    f"删除关联成功: {source_type}:{source_id} "
                    f"-[{relation}]-> {target_type}:{target_id}"
                )
                # 触发同步：构建临时 edge 对象
                edge = KnowledgeEdge(
                    source_type=source_type,
                    source_id=source_id,
                    target_type=target_type,
                    target_id=target_id,
                    relation=relation,
                )
                self._trigger_edge_sync(edge)
            return deleted

    def delete_edges_by_entity(
        self,
        entity_type: EdgeEntityType,
        entity_id: str,
    ) -> int:
        """
        删除与实体相关的所有边（作为 source 或 target）

        用于实体删除时的级联清理。

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID

        Returns:
            删除的边数量
        """
        entity_type_value = entity_type.value if isinstance(entity_type, EdgeEntityType) else entity_type

        # 先获取所有相关边，用于触发同步
        edges_as_source = self.get_edges_by_entity(entity_type, entity_id, include_bidirectional=False)
        edges_as_target = self.get_edges_to_entity(entity_type, entity_id)

        # 收集需要同步的关系类型
        affected_relations = set()
        for edge in edges_as_source + edges_as_target:
            relation = edge.relation.value if hasattr(edge.relation, 'value') else edge.relation
            affected_relations.add(relation)

        # 执行删除
        with self._cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM knowledge_edges
                WHERE (source_type = %s AND source_id = %s)
                   OR (target_type = %s AND target_id = %s)
                """,
                (entity_type_value, entity_id, entity_type_value, entity_id),
            )
            deleted_count = cursor.rowcount

        if deleted_count > 0:
            logger.info(f"级联删除边: {entity_type_value}:{entity_id}, 共 {deleted_count} 条")
            # 触发每种关系类型的同步
            for relation in affected_relations:
                try:
                    from domains.mcp_core.sync.trigger import SyncTrigger
                    trigger = SyncTrigger.get_instance()
                    # 构建临时 edge 触发同步
                    temp_edge = KnowledgeEdge(
                        source_type=entity_type,
                        source_id=entity_id,
                        target_type=entity_type,
                        target_id=entity_id,
                        relation=EdgeRelationType(relation) if isinstance(relation, str) else relation,
                    )
                    trigger.sync_edge(temp_edge)
                except Exception as e:
                    logger.warning(f"边同步触发失败: {relation}, {e}")

        return deleted_count

    def exists(
        self,
        source_type: EdgeEntityType,
        source_id: str,
        target_type: EdgeEntityType,
        target_id: str,
        relation: EdgeRelationType = EdgeRelationType.RELATED,
    ) -> bool:
        """
        检查关联是否存在

        Args:
            source_type: 源实体类型
            source_id: 源实体 ID
            target_type: 目标实体类型
            target_id: 目标实体 ID
            relation: 关系类型

        Returns:
            是否存在
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM knowledge_edges
                WHERE source_type = %s AND source_id = %s
                AND target_type = %s AND target_id = %s
                AND relation = %s
                LIMIT 1
                """,
                (
                    source_type.value if isinstance(source_type, EdgeEntityType) else source_type,
                    source_id,
                    target_type.value if isinstance(target_type, EdgeEntityType) else target_type,
                    target_id,
                    relation.value if isinstance(relation, EdgeRelationType) else relation,
                ),
            )
            return cursor.fetchone() is not None

    def get_edges_by_entity(
        self,
        entity_type: EdgeEntityType,
        entity_id: str,
        include_bidirectional: bool = True,
    ) -> List[KnowledgeEdge]:
        """
        获取实体的所有关联（包括双向）

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            include_bidirectional: 是否包含双向关联

        Returns:
            知识边列表
        """
        with self._cursor() as cursor:
            entity_type_value = entity_type.value if isinstance(entity_type, EdgeEntityType) else entity_type

            if include_bidirectional:
                # 包含双向关联：作为源或作为双向目标
                cursor.execute(
                    """
                    SELECT * FROM knowledge_edges
                    WHERE (source_type = %s AND source_id = %s)
                       OR (is_bidirectional = TRUE AND target_type = %s AND target_id = %s)
                    ORDER BY created_at DESC
                    """,
                    (entity_type_value, entity_id, entity_type_value, entity_id),
                )
            else:
                # 仅作为源
                cursor.execute(
                    """
                    SELECT * FROM knowledge_edges
                    WHERE source_type = %s AND source_id = %s
                    ORDER BY created_at DESC
                    """,
                    (entity_type_value, entity_id),
                )

            return [KnowledgeEdge.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_edges_to_entity(
        self,
        entity_type: EdgeEntityType,
        entity_id: str,
    ) -> List[KnowledgeEdge]:
        """
        获取指向实体的所有关联

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID

        Returns:
            知识边列表
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM knowledge_edges
                WHERE target_type = %s AND target_id = %s
                ORDER BY created_at DESC
                """,
                (
                    entity_type.value if isinstance(entity_type, EdgeEntityType) else entity_type,
                    entity_id,
                ),
            )
            return [KnowledgeEdge.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_edges_by_relation(
        self,
        relation: EdgeRelationType,
        limit: int = 100,
    ) -> List[KnowledgeEdge]:
        """
        按关系类型获取关联

        Args:
            relation: 关系类型
            limit: 返回数量限制

        Returns:
            知识边列表
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM knowledge_edges
                WHERE relation = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (
                    relation.value if isinstance(relation, EdgeRelationType) else relation,
                    limit,
                ),
            )
            return [KnowledgeEdge.from_dict(dict(row)) for row in cursor.fetchall()]

    def trace_lineage(
        self,
        entity_type: EdgeEntityType,
        entity_id: str,
        direction: str = "backward",
        max_depth: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        追溯实体的链路

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            direction: 追溯方向，"backward"（向上追溯源头）或 "forward"（向下追溯应用）
            max_depth: 最大追溯深度

        Returns:
            链路列表，每项包含 depth, edge
        """
        visited = set()
        result = []

        def _trace(etype: str, eid: str, depth: int):
            if depth > max_depth:
                return
            key = f"{etype}:{eid}"
            if key in visited:
                return
            visited.add(key)

            with self._cursor() as cursor:
                if direction == "backward":
                    # 向上追溯：当前实体是 source，找 target
                    cursor.execute(
                        """
                        SELECT * FROM knowledge_edges
                        WHERE source_type = %s AND source_id = %s
                        """,
                        (etype, eid),
                    )
                else:
                    # 向下追溯：当前实体是 target，找 source
                    cursor.execute(
                        """
                        SELECT * FROM knowledge_edges
                        WHERE target_type = %s AND target_id = %s
                        """,
                        (etype, eid),
                    )

                for row in cursor.fetchall():
                    edge = KnowledgeEdge.from_dict(dict(row))
                    result.append({"depth": depth, "edge": edge.to_dict()})

                    # 继续追溯
                    if direction == "backward":
                        _trace(edge.target_type.value, edge.target_id, depth + 1)
                    else:
                        _trace(edge.source_type.value, edge.source_id, depth + 1)

        entity_type_value = entity_type.value if isinstance(entity_type, EdgeEntityType) else entity_type
        _trace(entity_type_value, entity_id, 1)
        return result

    # ==================== 标签管理 ====================

    def add_tag(
        self,
        entity_type: EdgeEntityType,
        entity_id: str,
        tag: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        给实体添加标签

        Args:
            entity_type: 实体类型（如 data, factor, strategy）
            entity_id: 实体 ID（如 BTC-USDT）
            tag: 标签名称（如 妖币、蓝筹）
            metadata: 扩展元数据

        Returns:
            边 ID，失败返回 None
        """
        edge = KnowledgeEdge(
            source_type=entity_type,
            source_id=entity_id,
            target_type=EdgeEntityType.TAG,
            target_id=tag,
            relation=EdgeRelationType.HAS_TAG,
            metadata=metadata or {},
        )
        # create() 内部会触发 _trigger_edge_sync()，对于 has_tag 关系会正确导出标签
        return self.create(edge)

    def remove_tag(
        self,
        entity_type: EdgeEntityType,
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
            是否删除成功
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM knowledge_edges
                WHERE source_type = %s AND source_id = %s
                AND target_type = 'tag' AND target_id = %s
                AND relation = 'has_tag'
                """,
                (
                    entity_type.value if isinstance(entity_type, EdgeEntityType) else entity_type,
                    entity_id,
                    tag,
                ),
            )
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"移除标签成功: {entity_type}:{entity_id} -> {tag}")
                self._trigger_sync(entity_type, entity_id)
            return deleted

    def get_entity_tags(
        self,
        entity_type: EdgeEntityType,
        entity_id: str,
    ) -> List[str]:
        """
        获取实体的所有标签

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID

        Returns:
            标签列表
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT target_id FROM knowledge_edges
                WHERE source_type = %s AND source_id = %s
                AND target_type = 'tag' AND relation = 'has_tag'
                ORDER BY created_at DESC
                """,
                (
                    entity_type.value if isinstance(entity_type, EdgeEntityType) else entity_type,
                    entity_id,
                ),
            )
            return [row["target_id"] for row in cursor.fetchall()]

    def get_entities_by_tag(
        self,
        tag: str,
        entity_type: Optional[EdgeEntityType] = None,
    ) -> List[Dict[str, str]]:
        """
        获取拥有指定标签的所有实体

        Args:
            tag: 标签名称
            entity_type: 可选，筛选特定类型的实体

        Returns:
            实体列表 [{"type": "data", "id": "BTC-USDT"}, ...]
        """
        with self._cursor() as cursor:
            if entity_type:
                cursor.execute(
                    """
                    SELECT source_type, source_id FROM knowledge_edges
                    WHERE target_type = 'tag' AND target_id = %s
                    AND relation = 'has_tag' AND source_type = %s
                    ORDER BY created_at DESC
                    """,
                    (
                        tag,
                        entity_type.value if isinstance(entity_type, EdgeEntityType) else entity_type,
                    ),
                )
            else:
                cursor.execute(
                    """
                    SELECT source_type, source_id FROM knowledge_edges
                    WHERE target_type = 'tag' AND target_id = %s
                    AND relation = 'has_tag'
                    ORDER BY created_at DESC
                    """,
                    (tag,),
                )
            return [{"type": row["source_type"], "id": row["source_id"]} for row in cursor.fetchall()]

    def list_all_tags(self) -> List[Dict[str, Any]]:
        """
        列出所有使用过的标签及其统计

        Returns:
            标签列表 [{"tag": "妖币", "count": 5}, ...]
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT target_id as tag, COUNT(*) as count
                FROM knowledge_edges
                WHERE target_type = 'tag' AND relation = 'has_tag'
                GROUP BY target_id
                ORDER BY count DESC, tag
                """
            )
            return [{"tag": row["tag"], "count": row["count"]} for row in cursor.fetchall()]

    def get_all_entity_tags_by_type(
        self,
        entity_type: EdgeEntityType,
    ) -> Dict[str, List[str]]:
        """
        获取指定类型所有实体的标签映射

        Args:
            entity_type: 实体类型

        Returns:
            实体ID -> 标签列表的映射 {"BTC-USDT": ["妖币", "蓝筹"], ...}
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT source_id, target_id FROM knowledge_edges
                WHERE source_type = %s AND target_type = 'tag' AND relation = 'has_tag'
                ORDER BY source_id, created_at DESC
                """,
                (entity_type.value if isinstance(entity_type, EdgeEntityType) else entity_type,),
            )
            result: Dict[str, List[str]] = {}
            for row in cursor.fetchall():
                entity_id = row["source_id"]
                tag = row["target_id"]
                if entity_id not in result:
                    result[entity_id] = []
                result[entity_id].append(tag)
            return result

    def has_tag(
        self,
        entity_type: EdgeEntityType,
        entity_id: str,
        tag: str,
    ) -> bool:
        """
        检查实体是否拥有指定标签

        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            tag: 标签名称

        Returns:
            是否拥有该标签
        """
        return self.exists(
            source_type=entity_type,
            source_id=entity_id,
            target_type=EdgeEntityType.TAG,
            target_id=tag,
            relation=EdgeRelationType.HAS_TAG,
        )

    def _trigger_sync(self, entity_type: EdgeEntityType, entity_id: str) -> None:
        """触发标签同步到文件（不阻塞主流程）"""
        try:
            from domains.mcp_core.sync.trigger import get_sync_trigger
            etype = entity_type.value if isinstance(entity_type, EdgeEntityType) else entity_type
            get_sync_trigger().sync_tag(etype, entity_id)
        except Exception as e:
            # 同步失败只记录日志，不影响主业务
            logger.debug(f"tag_sync_trigger_skipped: {entity_type}:{entity_id}, {e}")

    def _trigger_edge_sync(self, edge: KnowledgeEdge) -> None:
        """触发边同步到文件（不阻塞主流程）"""
        try:
            from domains.mcp_core.sync.trigger import get_sync_trigger
            get_sync_trigger().sync_edge(edge)
        except Exception as e:
            # 同步失败只记录日志，不影响主业务
            logger.debug(f"edge_sync_trigger_skipped: {edge.source_id} -> {edge.target_id}, {e}")


# 全局实例
_edge_store: Optional[EdgeStore] = None


def get_edge_store() -> EdgeStore:
    """获取全局 EdgeStore 实例"""
    global _edge_store
    if _edge_store is None:
        _edge_store = EdgeStore()
    return _edge_store
