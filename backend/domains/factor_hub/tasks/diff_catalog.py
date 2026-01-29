"""
发现任务 - 检测未入库因子
"""

from dataclasses import dataclass, field
from pathlib import Path

from domains.mcp_core.paths import get_factors_dir, get_sections_dir

from ..core.config import get_config_loader
from ..core.store import FactorStore, get_factor_store


@dataclass
class DiscoverResult:
    """发现结果"""
    cataloged: set[str]      # 已入库
    pending: set[str]        # 待入库（新发现）
    excluded: set[str]       # 已排除
    missing_files: set[str]  # 在 catalog 中但文件已删除
    # 按类型分类的待入库因子
    pending_time_series: set[str] = field(default_factory=set)
    pending_cross_section: set[str] = field(default_factory=set)


def discover_factors(
    factor_dir: str | None = None,
    store: FactorStore | None = None
) -> DiscoverResult:
    """
    发现未入库因子（同时扫描 factors/ 和 sections/ 目录）

    Args:
        factor_dir: 因子目录路径（已废弃，保留兼容）
        store: 因子存储实例

    Returns:
        DiscoverResult 发现结果
    """
    config = get_config_loader()
    store = store or get_factor_store()

    # 扫描 private/factors/ 目录（时序因子）
    factors_dir = get_factors_dir()
    time_series_factors = set()
    if factors_dir.exists():
        for f in factors_dir.glob("*.py"):
            if not f.name.startswith('_'):
                # 使用不带 .py 后缀的文件名
                time_series_factors.add(f.stem)

    # 扫描 private/sections/ 目录（截面因子）
    sections_dir = get_sections_dir()
    cross_section_factors = set()
    if sections_dir.exists():
        for f in sections_dir.glob("*.py"):
            if not f.name.startswith('_'):
                cross_section_factors.add(f.stem)

    # 合并所有目录中的因子
    dir_factors = time_series_factors | cross_section_factors

    # 获取 catalog 中的因子
    catalog_factors = set()
    for factor in store.get_all():
        catalog_factors.add(factor.filename)

    # 获取排除列表（从数据库）
    excluded_dict = store.get_excluded_factors()
    excluded = set(excluded_dict.keys())

    # 计算各状态
    cataloged = dir_factors & catalog_factors
    pending = dir_factors - catalog_factors - excluded
    excluded_in_dir = dir_factors & excluded
    missing_files = catalog_factors - dir_factors

    # 按类型分类待入库因子
    pending_time_series = pending & time_series_factors
    pending_cross_section = pending & cross_section_factors

    return DiscoverResult(
        cataloged=cataloged,
        pending=pending,
        excluded=excluded_in_dir,
        missing_files=missing_files,
        pending_time_series=pending_time_series,
        pending_cross_section=pending_cross_section,
    )


def format_discover_report(result: DiscoverResult, verbose: bool = False) -> str:
    """
    格式化发现报告

    Args:
        result: 发现结果
        verbose: 是否详细输出

    Returns:
        格式化的报告字符串
    """
    lines = [
        "=" * 60,
        "              因子发现状态报告",
        "=" * 60,
        "",
        "状态统计:",
        f"  - 已入库: {len(result.cataloged)}",
        f"  - 待入库: {len(result.pending)} (新发现)",
        f"    - 时序因子: {len(result.pending_time_series)}",
        f"    - 截面因子: {len(result.pending_cross_section)}",
        f"  - 已排除: {len(result.excluded)}",
        f"  - 文件缺失: {len(result.missing_files)}",
        "",
    ]

    if result.pending_time_series:
        lines.append("待入库时序因子 (factors/):")
        for name in sorted(result.pending_time_series):
            lines.append(f"  + {name}")
        lines.append("")

    if result.pending_cross_section:
        lines.append("待入库截面因子 (sections/):")
        for name in sorted(result.pending_cross_section):
            lines.append(f"  + {name}")
        lines.append("")

    if result.missing_files and verbose:
        lines.append("文件缺失 (在 catalog 中但文件已删除):")
        for name in sorted(result.missing_files):
            lines.append(f"  - {name}")
        lines.append("")

    if result.excluded and verbose:
        lines.append("已排除因子:")
        for name in sorted(result.excluded):
            lines.append(f"  × {name}")
        lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)


def save_pending_list(result: DiscoverResult, output_path: str | None = None) -> str:
    """
    保存待入库因子列表到文件

    Args:
        result: 发现结果
        output_path: 输出路径

    Returns:
        保存的文件路径
    """
    if output_path is None:
        # 从 backend/domains/factor_hub/tasks/diff_catalog.py 向上 5 级到项目根目录
        base_path = Path(__file__).parent.parent.parent.parent.parent
        output_path = base_path / ".pipeline" / "pending_factors.txt"
    else:
        output_path = Path(output_path)

    # 确保目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        for name in sorted(result.pending):
            f.write(f"{name}\n")

    return str(output_path)


def run_discover(
    factor_dir: str | None = None,
    verbose: bool = False,
    save: bool = False
) -> DiscoverResult:
    """
    运行发现任务

    Args:
        factor_dir: 因子目录
        verbose: 详细输出
        save: 是否保存待入库列表

    Returns:
        发现结果
    """
    result = discover_factors(factor_dir)

    # 打印报告
    print(format_discover_report(result, verbose))

    # 保存待入库列表
    if save and result.pending:
        path = save_pending_list(result)
        print(f"待入库列表已保存到: {path}")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="发现未入库因子")
    parser.add_argument("--factor-dir", help="因子目录路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--save", "-s", action="store_true", help="保存待入库列表")

    args = parser.parse_args()
    run_discover(args.factor_dir, args.verbose, args.save)
