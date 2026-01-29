"""
数据迁移任务

将 PostgreSQL knowledge_edges 和 experience_links 数据迁移到 Neo4j。
"""
import logging
from typing import Dict

from domains.mcp_core.edge import (
    EdgeRelationType,
    get_edge_store,
)
from domains.graph_hub.core import (
    GraphEdge,
    NodeType,
    RelationType,
    get_graph_store,
)

logger = logging.getLogger(__name__)


class GraphMigration:
    """图谱数据迁移"""

    def __init__(self):
        self._pg_edge_store = None
        self._neo4j_store = None

    @property
    def pg_edge_store(self):
        if self._pg_edge_store is None:
            self._pg_edge_store = get_edge_store()
        return self._pg_edge_store

    @property
    def neo4j_store(self):
        if self._neo4j_store is None:
            self._neo4j_store = get_graph_store()
        return self._neo4j_store

    def migrate_knowledge_edges(self) -> Dict[str, int]:
        """
        迁移 knowledge_edges 表

        Returns:
            {"total": X, "success": Y, "failed": Z, "skipped": W}
        """
        stats = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

        # 获取所有边（按关系类型分批获取）
        all_edges = []
        for relation in EdgeRelationType:
            edges = self.pg_edge_store.get_edges_by_relation(relation, limit=10000)
            all_edges.extend(edges)

        stats["total"] = len(all_edges)
        logger.info(f"开始迁移 {len(all_edges)} 条 knowledge_edges")

        for pg_edge in all_edges:
            try:
                # 转换为 GraphEdge
                neo_edge = GraphEdge(
                    source_type=NodeType(pg_edge.source_type.value),
                    source_id=pg_edge.source_id,
                    target_type=NodeType(pg_edge.target_type.value),
                    target_id=pg_edge.target_id,
                    relation=RelationType(pg_edge.relation.value),
                    is_bidirectional=pg_edge.is_bidirectional,
                    metadata=pg_edge.metadata,
                    created_at=pg_edge.created_at,
                )

                # 检查是否已存在
                if self.neo4j_store.exists(
                    neo_edge.source_type,
                    neo_edge.source_id,
                    neo_edge.target_type,
                    neo_edge.target_id,
                    neo_edge.relation,
                ):
                    stats["skipped"] += 1
                    continue

                # 创建边
                if self.neo4j_store.create_edge(neo_edge):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1

            except Exception as e:
                logger.warning(f"迁移失败: {pg_edge.source_id} -> {pg_edge.target_id}, {e}")
                stats["failed"] += 1

        logger.info(f"knowledge_edges 迁移完成: {stats}")
        return stats

    def migrate_experience_links(self) -> Dict[str, int]:
        """
        迁移 experience_links 表

        注意: experience_links 使用独立表存储，需要单独处理。

        Returns:
            {"total": X, "success": Y, "failed": Z, "skipped": W}
        """
        stats = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

        try:
            from domains.experience_hub.core.store import get_experience_store
            exp_store = get_experience_store()
            links = exp_store.get_all_links()
        except Exception as e:
            logger.warning(f"获取 experience_links 失败: {e}")
            return stats

        stats["total"] = len(links)
        logger.info(f"开始迁移 {len(links)} 条 experience_links")

        for link in links:
            try:
                # 映射关系类型
                relation_map = {
                    "related": RelationType.RELATED,
                    "derived_from": RelationType.DERIVED_FROM,
                    "applied_to": RelationType.APPLIED_TO,
                }
                relation = relation_map.get(link.relation, RelationType.RELATED)

                # 转换为 GraphEdge
                neo_edge = GraphEdge(
                    source_type=NodeType.EXPERIENCE,
                    source_id=str(link.experience_id),
                    target_type=NodeType(link.entity_type),
                    target_id=link.entity_id,
                    relation=relation,
                    created_at=link.created_at,
                )

                # 检查是否已存在
                if self.neo4j_store.exists(
                    neo_edge.source_type,
                    neo_edge.source_id,
                    neo_edge.target_type,
                    neo_edge.target_id,
                    neo_edge.relation,
                ):
                    stats["skipped"] += 1
                    continue

                # 创建边
                if self.neo4j_store.create_edge(neo_edge):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1

            except Exception as e:
                logger.warning(f"迁移失败: exp:{link.experience_id} -> {link.entity_id}, {e}")
                stats["failed"] += 1

        logger.info(f"experience_links 迁移完成: {stats}")
        return stats

    def run_full_migration(self) -> Dict[str, Dict[str, int]]:
        """
        执行完整迁移

        Returns:
            {"knowledge_edges": {...}, "experience_links": {...}}
        """
        logger.info("开始完整迁移")
        results = {
            "knowledge_edges": self.migrate_knowledge_edges(),
            "experience_links": self.migrate_experience_links(),
        }
        logger.info(f"完整迁移完成: {results}")
        return results

    def verify_migration(self) -> Dict[str, int]:
        """
        验证迁移数据一致性

        Returns:
            {"pg_count": X, "neo4j_count": Y, "diff": Z}
        """
        # 统计 PostgreSQL 边数量
        pg_count = 0
        for relation in EdgeRelationType:
            edges = self.pg_edge_store.get_edges_by_relation(relation, limit=100000)
            pg_count += len(edges)

        # 统计 Neo4j 边数量 (需要在 GraphStore 添加 count_edges 方法)
        # 这里简化处理，返回基本统计
        return {
            "pg_knowledge_edges": pg_count,
            "message": "详细验证请使用 Neo4j Browser 查询",
        }


def run_migration():
    """运行迁移任务"""
    migration = GraphMigration()
    return migration.run_full_migration()


def verify_migration():
    """验证迁移"""
    migration = GraphMigration()
    return migration.verify_migration()


def cleanup_pg_tables(dry_run: bool = True) -> Dict[str, int]:
    """
    清理 PostgreSQL 旧表数据

    Args:
        dry_run: 如果为 True，只统计不删除

    Returns:
        {"knowledge_edges": X, "experience_links": Y}
    """
    import psycopg2
    from app.core.config import settings

    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()

    # 统计
    cur.execute("SELECT COUNT(*) FROM knowledge_edges")
    ke_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM experience_links")
    el_count = cur.fetchone()[0]

    if not dry_run:
        logger.warning("开始清理 PostgreSQL 旧表数据...")
        cur.execute("DELETE FROM knowledge_edges")
        cur.execute("DELETE FROM experience_links")
        conn.commit()
        logger.info(f"已清理: knowledge_edges={ke_count}, experience_links={el_count}")

    conn.close()

    return {
        "knowledge_edges": ke_count,
        "experience_links": el_count,
        "dry_run": dry_run,
    }


def main():
    """CLI 入口"""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Graph 数据迁移工具")
    parser.add_argument(
        "action",
        choices=["migrate", "verify", "cleanup", "status"],
        help="执行的操作: migrate(迁移), verify(验证), cleanup(清理旧表), status(查看状态)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="cleanup 时实际删除数据（默认只统计）",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if args.action == "migrate":
        result = run_migration()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.action == "verify":
        result = verify_migration()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.action == "cleanup":
        dry_run = not args.no_dry_run
        result = cleanup_pg_tables(dry_run=dry_run)
        if dry_run:
            print("DRY RUN - 以下数据将被清理（使用 --no-dry-run 实际执行）:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.action == "status":
        # 显示当前状态
        import psycopg2
        from app.core.config import settings

        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM knowledge_edges")
        ke_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM experience_links")
        el_count = cur.fetchone()[0]

        conn.close()

        print("PostgreSQL 状态:")
        print(f"  knowledge_edges: {ke_count} 条")
        print(f"  experience_links: {el_count} 条")

        # Neo4j 状态
        try:
            from domains.graph_hub.core import get_graph_store
            store = get_graph_store()
            neo4j_count = store.count_all_edges()
            print(f"\nNeo4j 状态:")
            print(f"  总边数: {neo4j_count} 条")
        except Exception as e:
            print(f"\nNeo4j 状态: 无法连接 ({e})")


if __name__ == "__main__":
    main()
