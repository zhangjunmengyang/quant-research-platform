"""
知识边同步服务

将 Neo4j 图数据库中的关系数据导出到文件系统。

同步策略：
1. 标签关系 (has_tag): 存储在 private/tags/{entity_type}/{entity_id}.yaml
2. 其他关系: 存储在 private/edges/{relation}.yaml

文件结构示例：
    private/
      tags/                    # 标签关系
        data/BTC-USDT.yaml     # 币种标签
        factor/Mtm_5d.yaml     # 因子标签
      edges/                   # 其他关系
        verifies.yaml          # 验证关系
        derived_from.yaml      # 派生关系
        references.yaml        # 引用关系
        summarizes.yaml        # 总结关系
        applied_to.yaml        # 应用关系
        related.yaml           # 通用关联

关系文件格式 (YAML)：
    # private/edges/verifies.yaml
    # 验证关系：检验笔记 verifies 假设笔记
    edges:
      - source_type: note
        source_id: "180"
        target_type: note
        target_id: "168"
        is_bidirectional: false
        metadata: {}
        created_at: "2026-01-27T10:00:00"
"""

import logging
from pathlib import Path
from typing import Any

from .base import BaseSyncService

logger = logging.getLogger(__name__)


class EdgeSyncService(BaseSyncService):
    """
    知识边同步服务

    从 Neo4j 图数据库读取数据，导出到文件系统。
    支持两种同步模式：
    1. 标签同步: has_tag 关系，按实体组织存储在 private/tags/
    2. 关系同步: 其他关系，按关系类型组织存储在 private/edges/
    """

    # 支持同步的实体类型（用于标签同步）
    SUPPORTED_ENTITY_TYPES = [
        "data",      # 币种
        "factor",    # 因子
        "strategy",  # 策略
        "note",      # 笔记
        "experience",  # 经验
    ]

    # 支持同步的关系类型（排除 has_tag，has_tag 单独处理）
    SUPPORTED_RELATION_TYPES = [
        "derived_from",  # 派生关系
        "applied_to",    # 应用关系
        "verifies",      # 验证关系
        "references",    # 引用关系
        "summarizes",    # 总结关系
        "related",       # 通用关联
    ]

    def __init__(self, data_dir: Path, store: Any = None):
        """
        初始化知识边同步服务

        Args:
            data_dir: 私有数据目录 (private/)
            store: GraphStore 实例 (Neo4j)
        """
        super().__init__(data_dir, store)
        self.tags_dir = data_dir / "tags"
        self.edges_dir = data_dir / "edges"
        self._graph_store = None

    @property
    def graph_store(self):
        """延迟获取 GraphStore 实例"""
        if self._graph_store is None:
            try:
                from domains.graph_hub.core import get_graph_store
                self._graph_store = get_graph_store()
            except Exception as e:
                logger.warning(f"graph_store_init_failed: {e}")
        return self._graph_store

    # ==================== 标签同步 (has_tag) ====================

    def _get_tag_entity_dir(self, entity_type: str) -> Path:
        """获取实体类型对应的标签目录"""
        return self.tags_dir / entity_type

    def _get_tag_entity_file(self, entity_type: str, entity_id: str) -> Path:
        """获取实体对应的标签文件路径"""
        safe_id = entity_id.replace("/", "_").replace("\\", "_")
        return self._get_tag_entity_dir(entity_type) / f"{safe_id}.yaml"

    # ==================== 关系同步 (其他关系) ====================

    def _get_relation_file(self, relation: str) -> Path:
        """获取关系类型对应的文件路径"""
        return self.edges_dir / f"{relation}.yaml"

    # ==================== 导出功能 ====================

    def export_all(self, overwrite: bool = False) -> dict[str, int]:
        """
        导出所有知识边数据（标签 + 关系）

        Args:
            overwrite: 是否覆盖已存在的文件

        Returns:
            {"exported": N, "skipped": M, "errors": K}
        """
        stats = {"exported": 0, "skipped": 0, "errors": 0}

        if self.graph_store is None:
            logger.warning("edge_sync_export_skipped: graph_store is None")
            return stats

        # 1. 导出标签
        tag_stats = self._export_all_tags(overwrite)
        stats["exported"] += tag_stats.get("exported", 0)
        stats["skipped"] += tag_stats.get("skipped", 0)
        stats["errors"] += tag_stats.get("errors", 0)

        # 2. 导出关系
        relation_stats = self._export_all_relations(overwrite)
        stats["exported"] += relation_stats.get("exported", 0)
        stats["skipped"] += relation_stats.get("skipped", 0)
        stats["errors"] += relation_stats.get("errors", 0)

        logger.info(f"edges_exported: {stats}")
        return stats

    def _export_all_tags(self, overwrite: bool) -> dict[str, int]:
        """导出所有标签"""
        stats = {"exported": 0, "skipped": 0, "errors": 0}

        for entity_type in self.SUPPORTED_ENTITY_TYPES:
            try:
                result = self._export_entity_type_tags(entity_type, overwrite)
                stats["exported"] += result.get("exported", 0)
                stats["skipped"] += result.get("skipped", 0)
                stats["errors"] += result.get("errors", 0)
            except Exception as e:
                logger.error(f"tag_export_error: {entity_type}, {e}")
                stats["errors"] += 1

        return stats

    def _export_entity_type_tags(self, entity_type: str, overwrite: bool) -> dict[str, int]:
        """导出某个实体类型的所有标签"""
        stats = {"exported": 0, "skipped": 0, "errors": 0}

        try:
            from domains.graph_hub.core import NodeType
            etype = NodeType(entity_type)
            # 从 Neo4j 获取所有该类型实体的标签
            tags_map = self._get_all_entity_tags_by_type(etype)
        except Exception as e:
            logger.error(f"tag_export_get_error: {entity_type}, {e}")
            stats["errors"] = 1
            return stats

        if not tags_map:
            return stats

        entity_dir = self._get_tag_entity_dir(entity_type)
        self.ensure_dir(entity_dir)

        for entity_id, tags in tags_map.items():
            try:
                result = self._export_single_entity_tags(entity_type, entity_id, tags, overwrite)
                if result == "exported":
                    stats["exported"] += 1
                elif result == "skipped":
                    stats["skipped"] += 1
                else:
                    stats["errors"] += 1
            except Exception as e:
                logger.error(f"tag_export_entity_error: {entity_type}:{entity_id}, {e}")
                stats["errors"] += 1

        return stats

    def _get_all_entity_tags_by_type(self, entity_type) -> dict[str, list[str]]:
        """从 Neo4j 获取指定类型所有实体的标签映射"""
        result = {}
        if self.graph_store is None:
            return result

        try:
            # 查询所有 has_tag 关系
            from domains.graph_hub.core import RelationType
            edges = self.graph_store.get_edges_by_relation(RelationType.HAS_TAG, limit=10000)

            entity_type_value = entity_type.value if hasattr(entity_type, 'value') else entity_type

            for edge in edges:
                src_type = edge.source_type.value if hasattr(edge.source_type, 'value') else edge.source_type
                if src_type == entity_type_value:
                    entity_id = edge.source_id
                    tag = edge.target_id
                    if entity_id not in result:
                        result[entity_id] = []
                    result[entity_id].append(tag)
        except Exception as e:
            logger.error(f"get_all_entity_tags_error: {entity_type}, {e}")

        return result

    def _export_single_entity_tags(
        self,
        entity_type: str,
        entity_id: str,
        tags: list[str],
        overwrite: bool
    ) -> str:
        """导出单个实体的标签到文件"""
        filepath = self._get_tag_entity_file(entity_type, entity_id)
        data = {"tags": tags}

        if filepath.exists() and not overwrite:
            existing = self.read_yaml(filepath)
            if existing == data:
                return "skipped"

        self.ensure_dir(filepath.parent)
        self.write_yaml_atomic(filepath, data)
        return "exported"

    def _export_all_relations(self, overwrite: bool) -> dict[str, int]:
        """导出所有关系（非标签）"""
        stats = {"exported": 0, "skipped": 0, "errors": 0}

        self.ensure_dir(self.edges_dir)

        for relation in self.SUPPORTED_RELATION_TYPES:
            try:
                result = self._export_relation_type(relation, overwrite)
                if result == "exported":
                    stats["exported"] += 1
                elif result == "skipped":
                    stats["skipped"] += 1
                else:
                    stats["errors"] += 1
            except Exception as e:
                logger.error(f"relation_export_error: {relation}, {e}")
                stats["errors"] += 1

        return stats

    def _export_relation_type(self, relation: str, overwrite: bool) -> str:
        """导出某种关系类型的所有边"""
        try:
            from domains.graph_hub.core import RelationType
            rtype = RelationType(relation)
            edges = self.graph_store.get_edges_by_relation(rtype, limit=10000)
        except Exception as e:
            logger.error(f"relation_export_get_error: {relation}, {e}")
            return "error"

        filepath = self._get_relation_file(relation)

        if not edges:
            # 没有边，删除文件（如果存在）
            if filepath.exists():
                filepath.unlink()
                logger.debug(f"relation_file_removed: {relation}")
            return "skipped"

        # 转换为可序列化格式
        edges_data = []
        for edge in edges:
            edge_dict = edge.to_dict()
            edges_data.append(edge_dict)

        data = {"edges": edges_data}

        # 检查是否需要更新
        if filepath.exists() and not overwrite:
            existing = self.read_yaml(filepath)
            if existing == data:
                return "skipped"

        self.write_yaml_atomic(filepath, data)
        logger.debug(f"relation_exported: {relation}, {len(edges)} edges")
        return "exported"

    # ==================== 导入功能 ====================

    def import_all(self, full_sync: bool = False) -> dict[str, int]:
        """
        从文件导入所有知识边数据到 Neo4j

        Args:
            full_sync: 是否完全同步（删除文件中不存在的边）

        Returns:
            {"created": N, "updated": M, "deleted": D, "unchanged": K, "errors": L}
        """
        stats = {"created": 0, "updated": 0, "deleted": 0, "unchanged": 0, "errors": 0}

        if self.graph_store is None:
            logger.warning("edge_sync_import_skipped: graph_store is None")
            return stats

        # 1. 导入标签
        tag_stats = self._import_all_tags(full_sync=full_sync)
        stats["created"] += tag_stats.get("created", 0)
        stats["updated"] += tag_stats.get("updated", 0)
        stats["deleted"] += tag_stats.get("deleted", 0)
        stats["unchanged"] += tag_stats.get("unchanged", 0)
        stats["errors"] += tag_stats.get("errors", 0)

        # 2. 导入关系
        relation_stats = self._import_all_relations(full_sync=full_sync)
        stats["created"] += relation_stats.get("created", 0)
        stats["updated"] += relation_stats.get("updated", 0)
        stats["deleted"] += relation_stats.get("deleted", 0)
        stats["unchanged"] += relation_stats.get("unchanged", 0)
        stats["errors"] += relation_stats.get("errors", 0)

        logger.info(f"edges_imported: {stats}")
        return stats

    def _import_all_tags(self, full_sync: bool = False) -> dict[str, int]:
        """导入所有标签"""
        stats = {"created": 0, "updated": 0, "deleted": 0, "unchanged": 0, "errors": 0}

        if not self.tags_dir.exists():
            return stats

        for entity_type in self.SUPPORTED_ENTITY_TYPES:
            entity_dir = self._get_tag_entity_dir(entity_type)
            if not entity_dir.exists():
                continue

            try:
                result = self._import_entity_type_tags(entity_type, full_sync=full_sync)
                stats["created"] += result.get("created", 0)
                stats["updated"] += result.get("updated", 0)
                stats["deleted"] += result.get("deleted", 0)
                stats["unchanged"] += result.get("unchanged", 0)
                stats["errors"] += result.get("errors", 0)
            except Exception as e:
                logger.error(f"tag_import_error: {entity_type}, {e}")
                stats["errors"] += 1

        return stats

    def _import_entity_type_tags(self, entity_type: str, full_sync: bool = False) -> dict[str, int]:
        """导入某个实体类型的所有标签"""
        stats = {"created": 0, "updated": 0, "deleted": 0, "unchanged": 0, "errors": 0}

        entity_dir = self._get_tag_entity_dir(entity_type)
        if not entity_dir.exists():
            return stats

        from domains.graph_hub.core import NodeType
        etype = NodeType(entity_type)

        db_tags_map = self._get_all_entity_tags_by_type(etype)
        file_entities = set()

        for yaml_file in entity_dir.glob("*.yaml"):
            entity_id = yaml_file.stem
            file_entities.add(entity_id)

            try:
                data = self.read_yaml(yaml_file)
                if not data:
                    continue

                file_tags = data.get("tags", [])
                if not isinstance(file_tags, list):
                    stats["errors"] += 1
                    continue

                db_tags = set(db_tags_map.get(entity_id, []))
                file_tags_set = set(file_tags)

                tags_to_add = file_tags_set - db_tags
                tags_to_remove = (db_tags - file_tags_set) if full_sync else set()

                if not tags_to_add and not tags_to_remove:
                    stats["unchanged"] += 1
                    continue

                for tag in tags_to_add:
                    try:
                        self.graph_store.add_tag(etype, entity_id, tag)
                        stats["created"] += 1
                    except Exception as e:
                        logger.error(f"tag_import_add_error: {entity_id}, {tag}, {e}")
                        stats["errors"] += 1

                for tag in tags_to_remove:
                    try:
                        self.graph_store.remove_tag(etype, entity_id, tag)
                        stats["deleted"] += 1
                    except Exception as e:
                        logger.error(f"tag_import_remove_error: {entity_id}, {tag}, {e}")
                        stats["errors"] += 1

            except Exception as e:
                logger.error(f"tag_import_file_error: {yaml_file}, {e}")
                stats["errors"] += 1

        # 仅在 full_sync 模式下处理文件中不存在但数据库中存在的实体
        if full_sync:
            for entity_id in db_tags_map:
                if entity_id not in file_entities:
                    for tag in db_tags_map[entity_id]:
                        try:
                            self.graph_store.remove_tag(etype, entity_id, tag)
                            stats["deleted"] += 1
                        except Exception as e:
                            logger.error(f"tag_import_cleanup_error: {entity_id}, {e}")
                            stats["errors"] += 1

        return stats

    def _import_all_relations(self, full_sync: bool = False) -> dict[str, int]:
        """导入所有关系（非标签）"""
        stats = {"created": 0, "updated": 0, "deleted": 0, "unchanged": 0, "errors": 0}

        if not self.edges_dir.exists():
            return stats

        for relation in self.SUPPORTED_RELATION_TYPES:
            try:
                result = self._import_relation_type(relation, full_sync=full_sync)
                stats["created"] += result.get("created", 0)
                stats["updated"] += result.get("updated", 0)
                stats["deleted"] += result.get("deleted", 0)
                stats["unchanged"] += result.get("unchanged", 0)
                stats["errors"] += result.get("errors", 0)
            except Exception as e:
                logger.error(f"relation_import_error: {relation}, {e}")
                stats["errors"] += 1

        return stats

    def _import_relation_type(self, relation: str, full_sync: bool = False) -> dict[str, int]:
        """导入某种关系类型的所有边"""
        stats = {"created": 0, "updated": 0, "deleted": 0, "unchanged": 0, "errors": 0}

        filepath = self._get_relation_file(relation)

        from domains.graph_hub.core import GraphEdge, RelationType
        rtype = RelationType(relation)
        db_edges = self.graph_store.get_edges_by_relation(rtype, limit=10000)

        db_edge_keys = set()
        db_edge_map = {}
        for edge in db_edges:
            key = self._edge_key(edge)
            db_edge_keys.add(key)
            db_edge_map[key] = edge

        if not filepath.exists():
            if full_sync and db_edge_keys:
                for key in db_edge_keys:
                    edge = db_edge_map[key]
                    try:
                        self.graph_store.delete_edge(
                            edge.source_type,
                            edge.source_id,
                            edge.target_type,
                            edge.target_id,
                            edge.relation,
                        )
                        stats["deleted"] += 1
                    except Exception as e:
                        logger.error(f"relation_import_delete_error: {relation}, {key}, {e}")
                        stats["errors"] += 1
            return stats

        try:
            data = self.read_yaml(filepath)
            if not data:
                if full_sync:
                    for key in db_edge_keys:
                        edge = db_edge_map[key]
                        try:
                            self.graph_store.delete_edge(
                                edge.source_type,
                                edge.source_id,
                                edge.target_type,
                                edge.target_id,
                                edge.relation,
                            )
                            stats["deleted"] += 1
                        except Exception as e:
                            logger.error(f"relation_import_delete_error: {relation}, {key}, {e}")
                            stats["errors"] += 1
                return stats

            file_edges = data.get("edges", [])
            if not isinstance(file_edges, list):
                stats["errors"] = 1
                return stats

        except Exception as e:
            logger.error(f"relation_import_read_error: {relation}, {e}")
            stats["errors"] = 1
            return stats

        file_edge_keys = set()
        file_edge_map = {}
        for edge_data in file_edges:
            try:
                edge = GraphEdge.from_dict(edge_data)
                key = self._edge_key(edge)
                file_edge_keys.add(key)
                file_edge_map[key] = edge
            except Exception as e:
                logger.error(f"relation_import_parse_error: {relation}, {e}")
                stats["errors"] += 1

        edges_to_add = file_edge_keys - db_edge_keys
        edges_to_remove = db_edge_keys - file_edge_keys if full_sync else set()

        unchanged_keys = file_edge_keys & db_edge_keys
        stats["unchanged"] = len(unchanged_keys)

        for key in edges_to_add:
            edge = file_edge_map[key]
            try:
                result = self.graph_store.create_edge(edge)
                if result:
                    stats["created"] += 1
                else:
                    stats["unchanged"] += 1
            except Exception as e:
                logger.error(f"relation_import_create_error: {relation}, {key}, {e}")
                stats["errors"] += 1

        for key in edges_to_remove:
            edge = db_edge_map[key]
            try:
                self.graph_store.delete_edge(
                    edge.source_type,
                    edge.source_id,
                    edge.target_type,
                    edge.target_id,
                    edge.relation,
                )
                stats["deleted"] += 1
            except Exception as e:
                logger.error(f"relation_import_delete_error: {relation}, {key}, {e}")
                stats["errors"] += 1

        return stats

    def _edge_key(self, edge) -> str:
        """生成边的唯一键（用于比较）"""
        source_type = edge.source_type.value if hasattr(edge.source_type, 'value') else edge.source_type
        target_type = edge.target_type.value if hasattr(edge.target_type, 'value') else edge.target_type
        relation = edge.relation.value if hasattr(edge.relation, 'value') else edge.relation
        return f"{source_type}:{edge.source_id}-[{relation}]->{target_type}:{edge.target_id}"

    # ==================== 单个实体同步 ====================

    def export_single(self, entity_type: str, entity_id: str) -> bool:
        """导出单个实体的标签"""
        if self.graph_store is None:
            return False

        try:
            from domains.graph_hub.core import NodeType
            etype = NodeType(entity_type)
            tags = self.graph_store.get_entity_tags(etype, entity_id)

            filepath = self._get_tag_entity_file(entity_type, entity_id)

            if not tags:
                if filepath.exists():
                    filepath.unlink()
                    logger.debug(f"tag_file_removed: {entity_type}:{entity_id}")
                return True

            self.ensure_dir(filepath.parent)
            data = {"tags": tags}
            self.write_yaml_atomic(filepath, data)
            logger.debug(f"tag_exported: {entity_type}:{entity_id}, {len(tags)} tags")
            return True

        except Exception as e:
            logger.error(f"tag_export_single_error: {entity_type}:{entity_id}, {e}")
            return False

    def export_relation(self, relation: str) -> bool:
        """导出某种关系类型的所有边"""
        if self.graph_store is None:
            return False

        try:
            result = self._export_relation_type(relation, overwrite=True)
            return result in ("exported", "skipped")
        except Exception as e:
            logger.error(f"relation_export_error: {relation}, {e}")
            return False

    def export_edge(self, edge) -> bool:
        """导出单条边（触发该关系类型的完整导出）"""
        relation = edge.relation.value if hasattr(edge.relation, 'value') else edge.relation

        if relation == "has_tag":
            source_type = edge.source_type.value if hasattr(edge.source_type, 'value') else edge.source_type
            return self.export_single(source_type, edge.source_id)
        else:
            return self.export_relation(relation)

    # ==================== 状态查询 ====================

    def get_status(self) -> dict[str, Any]:
        """获取同步状态"""
        status = {
            "tags": {
                "db_counts": {},
                "file_counts": {},
            },
            "relations": {
                "db_counts": {},
                "file_counts": {},
            },
        }

        if self.graph_store is None:
            return status

        # 标签统计
        for entity_type in self.SUPPORTED_ENTITY_TYPES:
            try:
                from domains.graph_hub.core import NodeType
                etype = NodeType(entity_type)
                tags_map = self._get_all_entity_tags_by_type(etype)
                status["tags"]["db_counts"][entity_type] = len(tags_map)
            except Exception:
                status["tags"]["db_counts"][entity_type] = 0

            entity_dir = self._get_tag_entity_dir(entity_type)
            if entity_dir.exists():
                status["tags"]["file_counts"][entity_type] = len(list(entity_dir.glob("*.yaml")))
            else:
                status["tags"]["file_counts"][entity_type] = 0

        # 关系统计
        for relation in self.SUPPORTED_RELATION_TYPES:
            try:
                from domains.graph_hub.core import RelationType
                rtype = RelationType(relation)
                edges = self.graph_store.get_edges_by_relation(rtype, limit=10000)
                status["relations"]["db_counts"][relation] = len(edges)
            except Exception:
                status["relations"]["db_counts"][relation] = 0

            filepath = self._get_relation_file(relation)
            if filepath.exists():
                try:
                    data = self.read_yaml(filepath)
                    status["relations"]["file_counts"][relation] = len(data.get("edges", []))
                except Exception:
                    status["relations"]["file_counts"][relation] = 0
            else:
                status["relations"]["file_counts"][relation] = 0

        return status

    def restore_from_file(self) -> dict[str, int]:
        """从文件完全恢复数据到 Neo4j"""
        return self.import_all(full_sync=True)
