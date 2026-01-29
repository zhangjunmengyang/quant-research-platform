"""
清理脚本 - 迁移完成后删除 PostgreSQL 旧表

使用方法:
    # 预览将要删除的内容
    python -m domains.graph_hub.tasks.cleanup --dry-run

    # 实际执行删除
    python -m domains.graph_hub.tasks.cleanup --execute
"""
import logging
import argparse

logger = logging.getLogger(__name__)


def drop_old_tables(dry_run: bool = True) -> dict:
    """
    删除旧的边表

    Args:
        dry_run: 如果为 True，只预览不执行

    Returns:
        {"tables_dropped": [...], "dry_run": bool}
    """
    import psycopg2
    from app.core.config import settings

    tables_to_drop = ["knowledge_edges", "experience_links"]
    result = {"tables_dropped": [], "dry_run": dry_run}

    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()

    for table in tables_to_drop:
        # 检查表是否存在
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = %s
            )
        """, (table,))
        exists = cur.fetchone()[0]

        if not exists:
            logger.info(f"表 {table} 不存在，跳过")
            continue

        # 检查记录数
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]

        if count > 0 and dry_run:
            logger.warning(f"表 {table} 还有 {count} 条记录，建议先迁移")

        if dry_run:
            logger.info(f"[DRY RUN] 将删除表: {table} ({count} 条记录)")
        else:
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            logger.info(f"已删除表: {table}")

        result["tables_dropped"].append({"table": table, "count": count})

    if not dry_run:
        conn.commit()

    conn.close()
    return result


def cleanup_code_references() -> dict:
    """
    列出需要清理的代码引用

    Returns:
        需要手动清理的文件列表
    """
    files_to_cleanup = [
        {
            "path": "backend/domains/mcp_core/edge/",
            "action": "删除整个目录",
            "reason": "PostgreSQL 边存储已被 Neo4j 替代",
        },
        {
            "path": "backend/domains/graph_hub/core/pg_compat.py",
            "action": "删除文件",
            "reason": "双写兼容层不再需要",
        },
        {
            "path": "backend/domains/experience_hub/core/schema.sql",
            "action": "删除文件",
            "reason": "experience_links 表定义不再需要",
        },
        {
            "path": "docker/compose/init.sql",
            "action": "删除 knowledge_edges 表定义（第 534-577 行）",
            "reason": "表结构已迁移到 Neo4j",
        },
        {
            "path": "backend/domains/mcp_core/__init__.py",
            "action": "移除 edge 相关导出",
            "reason": "edge 模块将被删除",
        },
        {
            "path": "backend/domains/graph_hub/core/store.py",
            "action": "移除 pg_compat 相关调用",
            "reason": "不再需要双写",
        },
    ]

    return {"files_to_cleanup": files_to_cleanup}


def main():
    """CLI 入口"""
    import json

    parser = argparse.ArgumentParser(description="清理 PostgreSQL 旧表")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览将要删除的内容（默认）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="实际执行删除",
    )
    parser.add_argument(
        "--list-code",
        action="store_true",
        help="列出需要清理的代码引用",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    if args.list_code:
        result = cleanup_code_references()
        print("\n需要手动清理的代码引用:")
        print("-" * 60)
        for item in result["files_to_cleanup"]:
            print(f"\n文件: {item['path']}")
            print(f"  操作: {item['action']}")
            print(f"  原因: {item['reason']}")
        return

    dry_run = not args.execute
    if args.execute:
        confirm = input("确定要删除旧表吗？此操作不可逆！(yes/no): ")
        if confirm.lower() != "yes":
            print("已取消")
            return

    result = drop_old_tables(dry_run=dry_run)

    if dry_run:
        print("\n[DRY RUN] 以下操作将被执行（使用 --execute 实际执行）:")
    else:
        print("\n执行结果:")

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
