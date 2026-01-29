"""
图谱业务服务

提供统一的图谱管理 API，使用 Neo4j 图数据库。
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from ..core import (
    GraphEdge,
    GraphStore,
    NodeType,
    RelationType,
    get_graph_store,
)

logger = logging.getLogger(__name__)


class GraphService:
    """图谱业务服务"""

    def __init__(self):
        """初始化服务"""
        self._store: Optional[GraphStore] = None

    @property
    def store(self) -> GraphStore:
        """延迟获取 GraphStore 实例"""
        if self._store is None:
            self._store = get_graph_store()
        return self._store

    # ==================== 关联管理 ====================

    def create_link(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relation: str = "related",
        is_bidirectional: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """
        创建关联

        Args:
            source_type: 源实体类型
            source_id: 源实体 ID
            target_type: 目标实体类型
            target_id: 目标实体 ID
            relation: 关系类型
            is_bidirectional: 是否双向
            metadata: 扩展元数据

        Returns:
            (成功, 消息)
        """
        try:
            src_type = NodeType(source_type)
            tgt_type = NodeType(target_type)
            rel_type = RelationType(relation)
        except ValueError as e:
            return False, f"无效的类型: {e}"

        edge = GraphEdge(
            source_type=src_type,
            source_id=source_id,
            target_type=tgt_type,
            target_id=target_id,
            relation=rel_type,
            is_bidirectional=is_bidirectional,
            metadata=metadata or {},
        )

        success = self.store.create_edge(edge)
        if success:
            return True, "关联创建成功"
        return False, "关联创建失败"

    def delete_link(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relation: str = "related",
    ) -> Tuple[bool, str]:
        """删除关联"""
        try:
            src_type = NodeType(source_type)
            tgt_type = NodeType(target_type)
            rel_type = RelationType(relation)
        except ValueError as e:
            return False, f"无效的类型: {e}"

        success = self.store.delete_edge(src_type, source_id, tgt_type, target_id, rel_type)
        if success:
            return True, "关联删除成功"
        return False, "关联不存在或删除失败"

    def get_edges(
        self,
        entity_type: str,
        entity_id: str,
        include_bidirectional: bool = True,
    ) -> Tuple[bool, str, List[Dict]]:
        """
        获取实体的所有关联

        Returns:
            (成功, 消息, 边列表)
        """
        try:
            etype = NodeType(entity_type)
        except ValueError as e:
            return False, f"无效的实体类型: {e}", []

        edges = self.store.get_edges_by_entity(etype, entity_id, include_bidirectional)
        return True, f"找到 {len(edges)} 条关联", [e.to_dict() for e in edges]

    # ==================== 图查询 ====================

    def trace_lineage(
        self,
        entity_type: str,
        entity_id: str,
        direction: str = "backward",
        max_depth: int = 5,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        追溯知识链路

        Returns:
            (成功, 消息, 链路结果)
        """
        try:
            etype = NodeType(entity_type)
        except ValueError as e:
            return False, f"无效的实体类型: {e}", None

        if direction not in ("backward", "forward"):
            return False, "方向必须是 backward 或 forward", None

        if max_depth < 1 or max_depth > 10:
            return False, "深度必须在 1-10 之间", None

        result = self.store.trace_lineage(etype, entity_id, direction, max_depth)
        return True, f"追溯到 {result.count} 个节点", result.to_dict()

    def find_path(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        max_depth: int = 5,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        查找两实体间路径

        Returns:
            (成功, 消息, 路径结果)
        """
        try:
            src_type = NodeType(source_type)
            tgt_type = NodeType(target_type)
        except ValueError as e:
            return False, f"无效的类型: {e}", None

        result = self.store.find_path(src_type, source_id, tgt_type, target_id, max_depth)
        return True, f"找到 {result.count} 条路径", result.to_dict()

    # ==================== 标签管理 ====================

    def add_tag(
        self,
        entity_type: str,
        entity_id: str,
        tag: str,
    ) -> Tuple[bool, str]:
        """添加标签"""
        try:
            etype = NodeType(entity_type)
        except ValueError as e:
            return False, f"无效的实体类型: {e}"

        success = self.store.add_tag(etype, entity_id, tag)
        if success:
            return True, "标签添加成功"
        return False, "标签添加失败"

    def remove_tag(
        self,
        entity_type: str,
        entity_id: str,
        tag: str,
    ) -> Tuple[bool, str]:
        """移除标签"""
        try:
            etype = NodeType(entity_type)
        except ValueError as e:
            return False, f"无效的实体类型: {e}"

        success = self.store.remove_tag(etype, entity_id, tag)
        if success:
            return True, "标签移除成功"
        return False, "标签不存在或移除失败"

    def get_entity_tags(
        self,
        entity_type: str,
        entity_id: str,
    ) -> Tuple[bool, str, List[str]]:
        """获取实体标签"""
        try:
            etype = NodeType(entity_type)
        except ValueError as e:
            return False, f"无效的实体类型: {e}", []

        tags = self.store.get_entity_tags(etype, entity_id)
        return True, f"找到 {len(tags)} 个标签", tags

    def get_entities_by_tag(
        self,
        tag: str,
        entity_type: Optional[str] = None,
    ) -> Tuple[bool, str, List[Dict]]:
        """按标签获取实体"""
        etype = None
        if entity_type:
            try:
                etype = NodeType(entity_type)
            except ValueError as e:
                return False, f"无效的实体类型: {e}", []

        entities = self.store.get_entities_by_tag(tag, etype)
        return True, f"找到 {len(entities)} 个实体", entities

    def list_all_tags(self) -> Tuple[bool, str, List[Dict]]:
        """列出所有标签"""
        tags = self.store.list_all_tags()
        return True, f"共 {len(tags)} 个标签", tags

    # ==================== 概览 ====================

    def get_overview(
        self,
        node_limit: int = 500,
        edge_limit: int = 1000,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取图谱概览 (全量数据带限制)

        Args:
            node_limit: 节点数量限制
            edge_limit: 边数量限制

        Returns:
            (成功, 消息, 图谱数据)
        """
        result = self.store.get_all_graph(node_limit, edge_limit)
        stats = result.get("stats", {})
        return (
            True,
            f"返回 {stats.get('returned_nodes', 0)} 节点, {stats.get('returned_edges', 0)} 边",
            result,
        )

    # ==================== 工具方法 ====================

    def health_check(self) -> bool:
        """健康检查"""
        return self.store.health_check()


# 单例
_graph_service: Optional[GraphService] = None


def get_graph_service() -> GraphService:
    """获取全局 GraphService 实例"""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
