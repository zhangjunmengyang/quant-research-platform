"""
入库任务 - 发现新因子并填充所有字段

入库流程：
1. 发现未入库的因子文件
2. 创建因子记录（filename, code_path）
3. 使用通用字段填充器填充所有元信息字段
"""

from pathlib import Path
from typing import Any

from domains.mcp_core.logging import setup_task_logger
from domains.mcp_core.paths import get_factors_dir

from ..core.store import Factor, get_factor_store
from ..services.field_filler import get_field_filler
from .diff_catalog import discover_factors

logger = setup_task_logger("ingest")


def run_ingest(
    factor_dir: str | None = None,
    factor_files: list[str] | None = None,
    fields: list[str] | None = None,
    concurrency: int = 1,
    delay: float = 15.0,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    执行入库任务

    Args:
        factor_dir: 因子目录
        factor_files: 指定的因子文件列表
        fields: 要填充的字段列表（默认全部）
        concurrency: 并发数
        delay: 请求间隔
        dry_run: 预览模式

    Returns:
        入库结果统计
    """
    store = get_factor_store()

    # Step 1: 发现待入库因子
    if factor_files:
        pending_files = [Path(f) for f in factor_files if Path(f).exists()]
        logger.info(f"指定处理 {len(pending_files)} 个因子文件")
    else:
        result = discover_factors(factor_dir)
        if not result.pending:
            logger.info("没有待入库的因子")
            return {'added': 0, 'filled': {}}

        # 获取因子目录 (private/factors)
        if factor_dir:
            base_dir = Path(factor_dir)
        else:
            base_dir = get_factors_dir()

        pending_files = [base_dir / filename for filename in result.pending]
        pending_files = [f for f in pending_files if f.exists()]
        logger.info(f"发现 {len(result.pending)} 个待入库因子，实际存在 {len(pending_files)} 个文件")

    if not pending_files:
        logger.info("没有找到要处理的因子文件")
        return {'added': 0, 'filled': {}}

    if dry_run:
        logger.info(f"[DRY RUN] 将入库 {len(pending_files)} 个因子")
        for f in pending_files[:5]:
            logger.info(f"  - {f.name}")
        if len(pending_files) > 5:
            logger.info(f"  ... 还有 {len(pending_files) - 5} 个")
        return {'added': 0, 'filled': {}}

    # Step 2: 创建因子记录
    logger.info("\n创建因子记录...")
    added_count = 0
    for file_path in pending_files:
        factor = Factor(
            filename=file_path.name,
            code_path=str(file_path),
        )
        if store.add(factor):
            added_count += 1
            logger.info(f"  + {file_path.name}")

    logger.info(f"已添加 {added_count} 个因子记录")

    # Step 3: 使用通用字段填充器填充所有字段
    if added_count == 0:
        return {'added': 0, 'filled': {}}

    # 确定要填充的字段
    filler = get_field_filler()
    if fields is None:
        fields = filler.get_fillable_fields()
    else:
        # 过滤有效字段
        fields = [f for f in fields if f in filler.get_fillable_fields()]

    if not fields:
        logger.info("没有要填充的字段")
        return {'added': added_count, 'filled': {}}

    logger.info(f"\n开始填充字段: {', '.join(fields)}")

    # 获取刚添加的因子
    new_factors = [store.get(f.name) for f in pending_files if store.get(f.name)]

    # 填充所有字段
    fill_results = filler.fill_fields(
        factors=new_factors,
        fields=fields,
        mode='incremental',
        concurrency=concurrency,
        delay=delay,
    )

    # 统计
    filled_stats = {}
    for field, field_result in fill_results.items():
        filled_stats[field] = field_result.success_count

    logger.info("\n入库完成:")
    logger.info(f"  添加因子: {added_count}")
    for field, count in filled_stats.items():
        logger.info(f"  填充 {field}: {count}")

    return {'added': added_count, 'filled': filled_stats}
