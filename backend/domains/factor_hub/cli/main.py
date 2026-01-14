#!/usr/bin/env python3
"""
Factor Pipeline CLI - 统一的因子库管理入口

命令:
  discover      检测未入库因子
  ingest        入库新因子并填充所有字段
  fill          填充/重新生成指定字段（通用能力）
  review        反思审核（可配置审核范围）
  verify        标记因子为已验证
  unverify      取消因子验证状态
  status        查看 pipeline 状态
  mcp           启动 MCP 服务（供 LLM 访问）
  export-md     导出 Markdown 视图
"""

import argparse
import sys
from pathlib import Path

from domains.mcp_core.paths import get_project_root
from dotenv import load_dotenv


# 加载项目根目录的 .env 文件
load_dotenv(get_project_root() / '.env')


def cmd_discover(args):
    """执行 discover 命令"""
    from ..tasks.diff_catalog import run_discover
    run_discover(
        factor_dir=args.factor_dir,
        verbose=args.verbose,
        save=args.save
    )


def cmd_ingest(args):
    """执行 ingest 命令 - 入库新因子并填充所有字段"""
    from ..tasks.ingest import run_ingest

    factor_files = None
    if args.factors:
        with open(args.factors, 'r', encoding='utf-8') as f:
            factor_files = [line.strip() for line in f if line.strip()]

    fields = None
    if args.fields:
        fields = [f.strip() for f in args.fields.split(',')]

    result = run_ingest(
        factor_dir=args.factor_dir,
        factor_files=factor_files,
        fields=fields,
        concurrency=args.concurrency,
        delay=args.delay,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        print(f"\n入库完成: 添加 {result.get('added', 0)} 个因子")


def cmd_fill(args):
    """执行 fill 命令 - 填充/重新生成指定字段"""
    from ..services.field_filler import get_field_filler

    filler = get_field_filler()

    if args.field == 'all':
        fields = filler.get_fillable_fields()
    else:
        fields = [f.strip() for f in args.field.split(',')]

    filter_condition = None
    if args.filter:
        filter_condition = {}
        for part in args.filter.split(','):
            if '=' in part:
                key, value = part.split('=', 1)
                filter_condition[key.strip()] = value.strip()

    print(f"将填充字段: {', '.join(fields)}")
    print(f"模式: {args.mode}")
    if filter_condition:
        print(f"筛选条件: {filter_condition}")

    if args.dry_run:
        print("[DRY RUN] 预览模式，不执行实际操作")
        return

    if len(fields) == 1:
        filler.fill_field(
            field=fields[0],
            mode=args.mode,
            filter_condition=filter_condition,
            concurrency=args.concurrency,
            delay=args.delay,
        )
    else:
        filler.fill_fields(
            fields=fields,
            mode=args.mode,
            filter_condition=filter_condition,
            concurrency=args.concurrency,
            delay=args.delay,
        )

    print("\n填充完成")


def cmd_review(args):
    """执行 review 命令 - 反思审核"""
    from ..tasks.review import run_review

    filter_condition = None
    if args.filter:
        filter_condition = {}
        for part in args.filter.split(','):
            if '=' in part:
                key, value = part.split('=', 1)
                filter_condition[key.strip()] = value.strip()

    review_fields = None
    if args.fields:
        review_fields = [f.strip() for f in args.fields.split(',')]

    summary = run_review(
        concurrency=args.concurrency,
        output_dir=args.output,
        dry_run=args.dry_run,
        apply_revisions=args.apply_revisions,
        delay=args.delay,
        filter_condition=filter_condition,
        review_fields=review_fields,
    )

    if not args.dry_run and summary:
        print(f"\n审核完成: {summary.success_count} 成功, {summary.fail_count} 失败, {summary.revision_count} 条修订")


def cmd_verify(args):
    """执行 verify 命令"""
    from ..core.store import get_factor_store

    store = get_factor_store()

    if args.factors:
        with open(args.factors, 'r', encoding='utf-8') as f:
            filenames = [line.strip() for line in f if line.strip()]
    else:
        filenames = [args.filename]

    for filename in filenames:
        if store.verify(filename, args.note or ""):
            print(f"v 已验证: {filename}")
        else:
            print(f"x 验证失败: {filename} (因子不存在)")


def cmd_unverify(args):
    """执行 unverify 命令"""
    from ..core.store import get_factor_store

    store = get_factor_store()

    if store.unverify(args.filename):
        print(f"v 已取消验证: {args.filename}")
    else:
        print(f"x 取消验证失败: {args.filename} (因子不存在)")


def cmd_status(args):
    """执行 status 命令"""
    from ..core.store import get_factor_store

    store = get_factor_store()

    all_factors = store.get_all()
    unscored = store.get_unscored()
    verified = store.get_verified()
    low_score = store.get_low_score(2.5)

    no_analysis = [f for f in all_factors if not f.analysis or f.analysis.strip() == '']

    print("=" * 60)
    print("              Factor Pipeline Status")
    print("=" * 60)
    print()
    print("因子统计:")
    print(f"  总因子数:      {len(all_factors)}")
    print(f"  未评分:        {len(unscored)}")
    print(f"  缺少分析:      {len(no_analysis)}")
    print(f"  低分(<2.5):    {len(low_score)}")
    print(f"  已验证:        {len(verified)}")
    print()

    score_dist = {'4.5+': 0, '4.0-4.5': 0, '3.0-4.0': 0, '2.5-3.0': 0, '<2.5': 0, '无评分': 0}
    for f in all_factors:
        if f.llm_score is None:
            score_dist['无评分'] += 1
        elif f.llm_score >= 4.5:
            score_dist['4.5+'] += 1
        elif f.llm_score >= 4.0:
            score_dist['4.0-4.5'] += 1
        elif f.llm_score >= 3.0:
            score_dist['3.0-4.0'] += 1
        elif f.llm_score >= 2.5:
            score_dist['2.5-3.0'] += 1
        else:
            score_dist['<2.5'] += 1

    print("评分分布:")
    for label, count in score_dist.items():
        pct = count / len(all_factors) * 100 if all_factors else 0
        bar = '#' * int(pct / 5)
        print(f"  {label:10s} {count:4d} ({pct:5.1f}%) {bar}")

    print()
    print("=" * 60)


def cmd_export_md(args):
    """导出 Markdown"""
    from ..core.store import get_factor_store
    from domains.mcp_core.paths import get_project_root as get_root

    store = get_factor_store()
    output_path = args.output or str(get_root() / "output" / "factor_catalog_export.md")
    store.export_to_markdown(output_path)
    print(f"v 已导出到 {output_path}")


def cmd_mcp(args):
    """启动 MCP 服务器"""
    from ..api.mcp.server import run_server

    print("=" * 60)
    print("        Factor Knowledge Base MCP Server")
    print("=" * 60)
    print()
    print(f"  地址:      http://{args.host}:{args.port}")
    print(f"  MCP 端点:  http://{args.host}:{args.port}/mcp")
    print(f"  健康检查:  http://{args.host}:{args.port}/health")
    print()
    print("  可用工具:")
    print("    - list_factors    获取因子列表")
    print("    - get_factor      获取因子详情")
    print("    - get_stats       获取统计信息")
    print("    - search_by_code  按代码搜索")
    print("    - update_factor   更新因子")
    print("    - verify_factor   验证因子")
    print("    - ...更多")
    print()
    print("=" * 60)
    print()

    run_server(
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=args.reload,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Factor Pipeline - 统一的因子库管理入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  discover      检测未入库因子
  ingest        入库新因子并填充所有字段
  fill          填充/重新生成指定字段（通用能力）
  review        反思审核（可配置审核范围）
  verify        标记因子为已验证
  unverify      取消因子验证状态
  status        查看 pipeline 状态
  mcp           启动 MCP 服务（供 LLM 访问）
  export-md     导出 Markdown 视图

Examples:
  factor-kb ingest
  factor-kb fill analysis --mode full
  factor-kb fill analysis --filter style=动量
  factor-kb review --fields style,formula
  factor-kb mcp
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # discover
    p_discover = subparsers.add_parser('discover', help='检测未入库因子')
    p_discover.add_argument('--factor-dir', help='因子目录路径')
    p_discover.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    p_discover.add_argument('--save', '-s', action='store_true', help='保存待入库列表')
    p_discover.set_defaults(func=cmd_discover)

    # ingest
    p_ingest = subparsers.add_parser('ingest', help='入库新因子并填充所有字段')
    p_ingest.add_argument('--factor-dir', help='因子目录')
    p_ingest.add_argument('--factors', help='因子列表文件')
    p_ingest.add_argument('--fields', help='要填充的字段（逗号分隔），默认全部')
    p_ingest.add_argument('--concurrency', type=int, default=1, help='并发数')
    p_ingest.add_argument('--delay', type=float, default=15.0, help='请求间隔秒数')
    p_ingest.add_argument('--dry-run', action='store_true', help='预览模式')
    p_ingest.set_defaults(func=cmd_ingest)

    # fill
    p_fill = subparsers.add_parser('fill', help='填充/重新生成指定字段')
    p_fill.add_argument('field', help='要填充的字段（或 all）')
    p_fill.add_argument('--mode', choices=['full', 'incremental'], default='incremental',
                        help='full=全量重新生成, incremental=只填充空值')
    p_fill.add_argument('--filter', help='筛选条件（如 style=动量）')
    p_fill.add_argument('--concurrency', type=int, default=1, help='并发数')
    p_fill.add_argument('--delay', type=float, default=15.0, help='请求间隔秒数')
    p_fill.add_argument('--dry-run', action='store_true', help='预览模式')
    p_fill.set_defaults(func=cmd_fill)

    # review
    p_review = subparsers.add_parser('review', help='反思审核（可配置审核范围）')
    p_review.add_argument('--fields', help='要审核的字段（逗号分隔）')
    p_review.add_argument('--filter', help='筛选条件（如 style=动量）')
    p_review.add_argument('--concurrency', type=int, default=1, help='并发数')
    p_review.add_argument('--output', default='output/review', help='输出目录')
    p_review.add_argument('--delay', type=float, default=15.0, help='请求间隔秒数')
    p_review.add_argument('--apply-revisions', action='store_true', help='自动应用修订')
    p_review.add_argument('--dry-run', action='store_true', help='预览模式')
    p_review.set_defaults(func=cmd_review)

    # verify
    p_verify = subparsers.add_parser('verify', help='标记因子为已验证')
    p_verify.add_argument('filename', nargs='?', help='因子文件名')
    p_verify.add_argument('--factors', help='因子列表文件')
    p_verify.add_argument('--note', help='验证备注')
    p_verify.set_defaults(func=cmd_verify)

    # unverify
    p_unverify = subparsers.add_parser('unverify', help='取消因子验证状态')
    p_unverify.add_argument('filename', help='因子文件名')
    p_unverify.set_defaults(func=cmd_unverify)

    # status
    p_status = subparsers.add_parser('status', help='查看 pipeline 状态')
    p_status.set_defaults(func=cmd_status)

    # export-md
    p_export = subparsers.add_parser('export-md', help='导出 Markdown 视图')
    p_export.add_argument('--output', '-o', help='输出文件路径')
    p_export.set_defaults(func=cmd_export_md)

    # mcp
    p_mcp = subparsers.add_parser('mcp', help='启动 MCP 服务（供 LLM 访问）')
    p_mcp.add_argument('--host', default='0.0.0.0', help='监听地址 (默认: 0.0.0.0)')
    p_mcp.add_argument('--port', type=int, default=6789, help='监听端口 (默认: 6789)')
    p_mcp.add_argument('--log-level', default='info', help='日志级别 (默认: info)')
    p_mcp.add_argument('--reload', action='store_true', help='热重载模式（开发用）')
    p_mcp.set_defaults(func=cmd_mcp)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
