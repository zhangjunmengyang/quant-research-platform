# Factor Pipeline Tasks Module
"""
任务模块，包含各阶段的具体任务实现：
- diff_catalog: 发现未入库因子
- review: 代码审核
- ingest: 因子入库

注意：使用延迟导入避免循环依赖和路径问题
"""

__all__ = [
    # diff_catalog
    'discover_factors',
    'run_discover',
    'DiscoverResult',
    # review
    'run_review',
    'ReviewResult',
    'ReviewSummary',
]


def __getattr__(name):
    """延迟导入，避免启动时的循环依赖"""
    if name in ('discover_factors', 'run_discover', 'DiscoverResult'):
        from .diff_catalog import discover_factors, run_discover, DiscoverResult
        return locals()[name]
    elif name in ('run_review', 'ReviewResult', 'ReviewSummary'):
        from .review import run_review, ReviewResult, ReviewSummary
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
