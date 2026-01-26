#!/usr/bin/env python3
"""
私有数据同步 CLI

用于在数据库和文件系统之间同步私有数据。

用法：
    python scripts/data_sync.py export --all              # 导出所有数据
    python scripts/data_sync.py export --factors --notes  # 导出指定类型
    python scripts/data_sync.py import --all              # 导入所有数据
    python scripts/data_sync.py import --factors          # 导入指定类型
    python scripts/data_sync.py status                    # 查看同步状态
"""

import argparse
import sys
from pathlib import Path

# 添加 backend 到 Python 路径
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))


def cmd_export(args):
    """导出数据"""
    from domains.mcp_core.sync import SyncManager

    manager = SyncManager()

    print("正在导出数据...")
    print(f"目标目录: {manager.data_dir}")
    print()

    if args.all:
        results = manager.export_all(overwrite=args.overwrite)
    else:
        types = []
        if args.factors:
            types.append("factors")
        if args.notes:
            types.append("notes")
        if args.strategies:
            types.append("strategies")
        if args.experiences:
            types.append("experiences")

        if not types:
            print("错误: 请指定要导出的数据类型 (--all, --factors, --notes, --strategies, --experiences)")
            return 1

        results = manager.export(*types, overwrite=args.overwrite)

    # 打印结果
    print("导出结果:")
    print("-" * 50)
    for data_type, stats in results.items():
        exported = stats.get("exported", 0)
        skipped = stats.get("skipped", 0)
        errors = stats.get("errors", 0)
        print(f"  {data_type}: 导出 {exported}, 跳过 {skipped}, 错误 {errors}")

    print()
    print("导出完成")
    return 0


def cmd_import(args):
    """导入数据"""
    from domains.mcp_core.sync import SyncManager

    manager = SyncManager()

    print("正在导入数据...")
    print(f"源目录: {manager.data_dir}")
    print()

    if not manager.data_dir.exists():
        print(f"错误: 私有数据目录不存在: {manager.data_dir}")
        return 1

    if args.all:
        results = manager.import_all()
    else:
        types = []
        if args.factors:
            types.append("factors")
        if args.notes:
            types.append("notes")
        if args.strategies:
            types.append("strategies")
        if args.experiences:
            types.append("experiences")

        if not types:
            print("错误: 请指定要导入的数据类型 (--all, --factors, --notes, --strategies, --experiences)")
            return 1

        results = manager.import_(*types)

    # 打印结果
    print("导入结果:")
    print("-" * 50)
    for data_type, stats in results.items():
        created = stats.get("created", 0)
        updated = stats.get("updated", 0)
        unchanged = stats.get("unchanged", 0)
        errors = stats.get("errors", 0)
        print(f"  {data_type}: 新增 {created}, 更新 {updated}, 未变 {unchanged}, 错误 {errors}")

    print()
    print("导入完成")
    return 0


def cmd_status(args):
    """查看同步状态"""
    from domains.mcp_core.sync import SyncManager

    manager = SyncManager()
    status = manager.get_status()

    print("同步状态")
    print("=" * 60)
    print(f"私有数据目录: {status['data_dir']}")
    print(f"目录存在: {'是' if status['exists'] else '否'}")
    print()

    if not status['exists']:
        print("提示: 私有数据目录不存在，请先运行 export 命令导出数据")
        return 0

    # 因子
    if "factors" in status:
        fs = status["factors"]
        print("因子 (factors):")
        if "error" in fs:
            print(f"  错误: {fs['error']}")
        else:
            print(f"  数据库: {fs.get('db_count', 0)} 条")
            print(f"  文件: {fs.get('file_count', 0)} 个")
            print(f"  已同步: {fs.get('synced', 0)}")
            print(f"  待导出: {fs.get('pending_export', 0)}")
            print(f"  待导入: {fs.get('pending_import', 0)}")
        print()

    # 笔记
    if "notes" in status:
        ns = status["notes"]
        print("笔记 (notes):")
        if "error" in ns:
            print(f"  错误: {ns['error']}")
        else:
            print(f"  数据库: {ns.get('db_count', 0)} 条")
            print(f"  文件: {ns.get('file_count', 0)} 个")
            if ns.get('by_type'):
                for t, c in ns['by_type'].items():
                    print(f"    - {t}: {c}")
        print()

    # 策略
    if "strategies" in status:
        ss = status["strategies"]
        print("策略 (strategies):")
        if "error" in ss:
            print(f"  错误: {ss['error']}")
        else:
            print(f"  数据库: {ss.get('db_count', 0)} 条")
            print(f"  配置文件: {ss.get('file_count', 0)} 个")
            print(f"  资金曲线: {ss.get('equity_file_count', 0)} 个")
        print()

    # 经验
    if "experiences" in status:
        es = status["experiences"]
        print("经验 (experiences):")
        if "error" in es:
            print(f"  错误: {es['error']}")
        else:
            print(f"  数据库: {es.get('db_count', 0)} 条")
            print(f"  文件: {es.get('file_count', 0)} 个")
            print(f"  关联关系: {es.get('links_count', 0)} 条")
        print()

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="私有数据同步工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    %(prog)s export --all              # 导出所有数据
    %(prog)s export --factors --notes  # 导出因子和笔记
    %(prog)s import --all              # 导入所有数据
    %(prog)s status                    # 查看同步状态
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # export 命令
    export_parser = subparsers.add_parser("export", help="导出数据到文件")
    export_parser.add_argument("--all", action="store_true", help="导出所有数据类型")
    export_parser.add_argument("--factors", action="store_true", help="导出因子元数据")
    export_parser.add_argument("--notes", action="store_true", help="导出笔记")
    export_parser.add_argument("--strategies", action="store_true", help="导出策略")
    export_parser.add_argument("--experiences", action="store_true", help="导出经验")
    export_parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的文件")

    # import 命令
    import_parser = subparsers.add_parser("import", help="从文件导入数据")
    import_parser.add_argument("--all", action="store_true", help="导入所有数据类型")
    import_parser.add_argument("--factors", action="store_true", help="导入因子元数据")
    import_parser.add_argument("--notes", action="store_true", help="导入笔记")
    import_parser.add_argument("--strategies", action="store_true", help="导入策略")
    import_parser.add_argument("--experiences", action="store_true", help="导入经验")

    # status 命令
    status_parser = subparsers.add_parser("status", help="查看同步状态")

    args = parser.parse_args()

    if args.command == "export":
        return cmd_export(args)
    elif args.command == "import":
        return cmd_import(args)
    elif args.command == "status":
        return cmd_status(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
