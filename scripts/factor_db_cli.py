#!/usr/bin/env python3
"""
因子数据库 CLI - SQL 执行入口

配合 .claude/skills/factor-select/SKILL.md 使用。

使用方式:
    python scripts/factor_db_cli.py "<SQL>"
    python scripts/factor_db_cli.py "<SQL>" --format json
    python scripts/factor_db_cli.py --file query.sql
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def get_connection():
    """获取数据库连接"""
    import psycopg2
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://quant:quant123@localhost:5432/quant"
    )
    return psycopg2.connect(database_url)


def format_value(value):
    """格式化值用于显示"""
    if value is None:
        return "(null)"
    if isinstance(value, str) and value == "":
        return "(空)"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def execute_sql(sql: str, output_format: str = "table"):
    """执行 SQL 并输出结果"""
    from psycopg2.extras import RealDictCursor

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql)

            # 判断是否为写操作
            if sql.strip().upper().startswith(("UPDATE", "INSERT", "DELETE")):
                conn.commit()
                print(f"影响 {cursor.rowcount} 行")
                return

            rows = cursor.fetchall()
            if not rows:
                print("(无结果)")
                return

            # 输出
            if output_format == "json":
                result = []
                for row in rows:
                    item = {}
                    for k, v in dict(row).items():
                        if isinstance(v, datetime):
                            item[k] = v.isoformat()
                        else:
                            item[k] = v
                    result.append(item)
                print(json.dumps(result, ensure_ascii=False, indent=2))

            elif output_format == "csv":
                import csv
                import io
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                for row in rows:
                    writer.writerow({k: format_value(v) for k, v in dict(row).items()})
                print(output.getvalue())

            elif output_format == "line":
                # 每行一个值（适合只查一列时复制）
                for row in rows:
                    values = list(row.values())
                    print("\t".join(str(v) if v is not None else "" for v in values))

            else:
                # table 格式
                columns = list(rows[0].keys())
                widths = {col: len(col) for col in columns}
                for row in rows:
                    for col in columns:
                        widths[col] = max(widths[col], len(format_value(row[col])))

                max_width = 50
                for col in columns:
                    widths[col] = min(widths[col], max_width)

                header = " | ".join(col.ljust(widths[col])[:widths[col]] for col in columns)
                print(header)
                print("-" * len(header))

                for row in rows:
                    line = " | ".join(
                        format_value(row[col]).ljust(widths[col])[:widths[col]]
                        for col in columns
                    )
                    print(line)

                print(f"\n({len(rows)} 行)")

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="因子数据库 CLI - SQL 执行入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查询
  python factor_db_cli.py "SELECT filename FROM factors WHERE style='' LIMIT 10"

  # JSON 输出
  python factor_db_cli.py "SELECT filename, style FROM factors LIMIT 5" --format json

  # 纯文本输出（适合复制因子名）
  python factor_db_cli.py "SELECT filename FROM factors WHERE excluded=false" --format line

  # 更新（自动 commit）
  python factor_db_cli.py "UPDATE factors SET style='动量' WHERE filename='Momentum_5d'"

  # 从文件读取 SQL
  python factor_db_cli.py --file query.sql

常用 SQL 见: .claude/skills/factor-select/SKILL.md
"""
    )

    parser.add_argument('sql', nargs='?', help='SQL 语句')
    parser.add_argument('--file', '-f', help='从文件读取 SQL')
    parser.add_argument('--format', choices=['table', 'json', 'csv', 'line'],
                        default='table', help='输出格式')

    args = parser.parse_args()

    # 获取 SQL
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            sql = f.read()
    elif args.sql:
        sql = args.sql
    else:
        parser.print_help()
        return

    execute_sql(sql.strip(), args.format)


if __name__ == "__main__":
    main()
