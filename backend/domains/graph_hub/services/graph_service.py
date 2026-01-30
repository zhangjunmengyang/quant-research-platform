"""
图谱业务服务

提供统一的图谱管理 API，使用 Neo4j 图数据库。
"""
import logging
from typing import Any

from ..core import (
    GraphEdge,
    GraphStore,
    LEGACY_RELATION_MAPPING,
    NodeType,
    RelationType,
    get_graph_store,
)

logger = logging.getLogger(__name__)


class GraphService:
    """图谱业务服务"""

    def __init__(self):
        """初始化服务"""
        self._store: GraphStore | None = None

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
        relation: str = "relates",
        subtype: str = "",
        is_bidirectional: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """
        创建关联

        Args:
            source_type: 源实体类型
            source_id: 源实体 ID
            target_type: 目标实体类型
            target_id: 目标实体 ID
            relation: 关系类型 (derives/relates，兼容旧格式)
            subtype: 关系子类型 (based/uses/refs/validates 等)
            is_bidirectional: 是否双向（None 时使用默认逻辑）
            metadata: 扩展元数据

        Returns:
            (成功, 消息)
        """
        try:
            src_type = NodeType(source_type)
            tgt_type = NodeType(target_type)

            # 兼容旧关系类型
            if relation in LEGACY_RELATION_MAPPING:
                new_rel, default_subtype = LEGACY_RELATION_MAPPING[relation]
                rel_type = RelationType(new_rel)
                if not subtype:
                    subtype = default_subtype
            else:
                rel_type = RelationType(relation)
        except ValueError as e:
            return False, f"无效的类型: {e}"

        # 双向逻辑: 如果未指定，RELATES 默认双向，DERIVES 默认单向
        if is_bidirectional is None:
            is_bidirectional = rel_type == RelationType.RELATES

        edge = GraphEdge(
            source_type=src_type,
            source_id=source_id,
            target_type=tgt_type,
            target_id=target_id,
            relation=rel_type,
            subtype=subtype,
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
        relation: str = "relates",
    ) -> tuple[bool, str]:
        """删除关联"""
        try:
            src_type = NodeType(source_type)
            tgt_type = NodeType(target_type)

            # 兼容旧关系类型
            if relation in LEGACY_RELATION_MAPPING:
                new_rel, _ = LEGACY_RELATION_MAPPING[relation]
                rel_type = RelationType(new_rel)
            else:
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
    ) -> tuple[bool, str, list[dict]]:
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
    ) -> tuple[bool, str, dict | None]:
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
    ) -> tuple[bool, str, dict | None]:
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
    ) -> tuple[bool, str]:
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
    ) -> tuple[bool, str]:
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
    ) -> tuple[bool, str, list[str]]:
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
        entity_type: str | None = None,
    ) -> tuple[bool, str, list[dict]]:
        """按标签获取实体"""
        etype = None
        if entity_type:
            try:
                etype = NodeType(entity_type)
            except ValueError as e:
                return False, f"无效的实体类型: {e}", []

        entities = self.store.get_entities_by_tag(tag, etype)
        return True, f"找到 {len(entities)} 个实体", entities

    def list_all_tags(self) -> tuple[bool, str, list[dict]]:
        """列出所有标签"""
        tags = self.store.list_all_tags()
        return True, f"共 {len(tags)} 个标签", tags

    # ==================== 概览 ====================

    def get_overview(
        self,
        node_limit: int = 500,
        edge_limit: int = 1000,
    ) -> tuple[bool, str, dict | None]:
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

    # ==================== Cypher 查询 ====================

    # 写操作关键字 (禁止)
    FORBIDDEN_KEYWORDS = {
        "CREATE", "MERGE", "DELETE", "DETACH", "SET",
        "REMOVE", "DROP", "LOAD", "FOREACH",
    }

    def execute_cypher(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> tuple[bool, str, dict | None]:
        """
        执行只读 Cypher 查询

        安全措施：
        - 禁止 CREATE/DELETE/SET 等写操作
        - 自动添加 LIMIT 限制
        - 解析结果为节点和边格式

        Returns:
            (成功, 消息, 结果数据)
        """
        # 1. 安全验证 - 检查禁止的写操作关键字
        query_upper = query.upper()
        for forbidden in self.FORBIDDEN_KEYWORDS:
            # 检查是否作为独立关键字出现
            if f" {forbidden} " in f" {query_upper} " or query_upper.startswith(f"{forbidden} "):
                return False, f"不允许执行写操作: {forbidden}", None

        # 2. 执行查询
        try:
            records, exec_time = self.store.execute_readonly_cypher(query, params)
        except Exception as e:
            return False, f"查询执行失败: {str(e)}", None

        # 3. 解析结果为节点和边
        nodes = []
        edges = []
        node_set = set()
        edge_set = set()

        for record in records:
            for value in record.values():
                self._extract_graph_elements(value, nodes, edges, node_set, edge_set)

        return True, f"查询成功，返回 {len(records)} 条记录", {
            "nodes": nodes,
            "edges": edges,
            "raw_records": self._serialize_records(records),
            "execution_time_ms": exec_time,
            "record_count": len(records),
        }

    def _extract_graph_elements(
        self,
        value: Any,
        nodes: list,
        edges: list,
        node_set: set,
        edge_set: set,
    ) -> None:
        """从 Neo4j 结果中提取节点和边"""
        # 处理节点
        if hasattr(value, "labels") and hasattr(value, "id"):
            labels = list(value.labels)
            node_type = labels[0].lower() if labels else "data"
            node_id = value.get("id", str(value.element_id))
            key = (node_type, node_id)
            if key not in node_set:
                node_set.add(key)
                nodes.append({"type": node_type, "id": node_id, "degree": 0})

        # 处理关系
        elif hasattr(value, "type") and hasattr(value, "nodes"):
            try:
                start_node, end_node = value.nodes
                src_labels = list(start_node.labels)
                tgt_labels = list(end_node.labels)

                src_type = src_labels[0].lower() if src_labels else "data"
                tgt_type = tgt_labels[0].lower() if tgt_labels else "data"
                src_id = start_node.get("id", str(start_node.element_id))
                tgt_id = end_node.get("id", str(end_node.element_id))
                rel_type = value.type.lower()

                edge_key = (src_type, src_id, tgt_type, tgt_id, rel_type)
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "source_type": src_type,
                        "source_id": src_id,
                        "target_type": tgt_type,
                        "target_id": tgt_id,
                        "relation": rel_type if rel_type in ("derives", "relates") else "relates",
                        "subtype": "",
                        "is_bidirectional": False,
                    })

                # 同时添加关系两端的节点
                for node, n_type, n_id in [
                    (start_node, src_type, src_id),
                    (end_node, tgt_type, tgt_id),
                ]:
                    key = (n_type, n_id)
                    if key not in node_set:
                        node_set.add(key)
                        nodes.append({"type": n_type, "id": n_id, "degree": 0})
            except Exception:
                pass

        # 处理路径
        elif hasattr(value, "nodes") and hasattr(value, "relationships"):
            for node in value.nodes:
                self._extract_graph_elements(node, nodes, edges, node_set, edge_set)
            for rel in value.relationships:
                self._extract_graph_elements(rel, nodes, edges, node_set, edge_set)

        # 处理列表
        elif isinstance(value, list):
            for item in value:
                self._extract_graph_elements(item, nodes, edges, node_set, edge_set)

    def _serialize_records(self, records: list[dict]) -> list[dict]:
        """序列化记录为 JSON 可序列化格式"""
        result = []
        for record in records:
            serialized = {}
            for key, value in record.items():
                serialized[key] = self._serialize_value(value)
            result.append(serialized)
        return result

    def _serialize_value(self, value: Any) -> Any:
        """序列化单个值"""
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            return [self._serialize_value(v) for v in value]
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        # Neo4j 节点
        if hasattr(value, "labels") and hasattr(value, "id"):
            labels = list(value.labels)
            return {
                "_type": "node",
                "labels": labels,
                "id": value.get("id", str(value.element_id)),
                "properties": dict(value),
            }
        # Neo4j 关系
        if hasattr(value, "type") and hasattr(value, "nodes"):
            return {
                "_type": "relationship",
                "type": value.type,
            }
        # Neo4j 路径
        if hasattr(value, "nodes") and hasattr(value, "relationships"):
            return {
                "_type": "path",
                "length": len(value.relationships),
            }
        # 其他类型转字符串
        return str(value)

    # ==================== 工具方法 ====================

    def health_check(self) -> bool:
        """健康检查"""
        return self.store.health_check()


# 单例
_graph_service: GraphService | None = None


def get_graph_service() -> GraphService:
    """获取全局 GraphService 实例"""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
