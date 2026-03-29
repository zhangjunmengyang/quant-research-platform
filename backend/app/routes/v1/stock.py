"""Stock Hub REST API 路由。"""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.core.async_utils import run_sync
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.stocks import (
    AnalysisTaskResultResponse,
    AnalysisTaskStatusResponse,
    AnalysisTaskSubmitResponse,
    AvailableBacktestsResponse,
    BacktestSourceInfo,
    CachedFactorInfo,
    DualAnalysisRequest,
    EnhancedAnalysisRequest,
    FactorBacktestRequest,
    StockFactorDetail,
    StockFactorSummary,
    StockStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_factor_service():
    from domains.stock_hub.services.stock_factor_service import (
        get_stock_factor_service,
    )
    return get_stock_factor_service()


def _get_analysis_service():
    from domains.stock_hub.services.stock_analysis_service import (
        get_stock_analysis_service,
    )
    return get_stock_analysis_service()


def _get_analysis_runner():
    from domains.stock_hub.services.stock_analysis_runner import (
        get_stock_analysis_runner,
    )

    return get_stock_analysis_runner()


# ---- 状态 ----


@router.get("/status", response_model=ApiResponse[StockStatusResponse])
async def get_status():
    """检查 Stock Hub 配置状态。"""
    svc = _get_analysis_service()
    data = await run_sync(svc.get_status)
    return ApiResponse(data=StockStatusResponse(**data))


# ---- 因子库 ----


@router.get(
    "/factors",
    response_model=ApiResponse[PaginatedResponse[StockFactorSummary]],
)
async def list_factors(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = None,
    category: str | None = None,
):
    """因子列表（分页+搜索+分类）。"""
    svc = _get_factor_service()
    items, total = await run_sync(
        svc.list_factors,
        page=page,
        page_size=page_size,
        search=search or "",
        category=category or "",
    )
    summaries = [
        StockFactorSummary(
            name=f["name"],
            category=f.get("category", ""),
            description=f.get("description", ""),
            has_add_factor=f.get("has_add_factor", False),
        )
        for f in items
    ]
    return ApiResponse(
        data=PaginatedResponse.create(
            items=summaries, total=total, page=page, page_size=page_size
        )
    )


@router.get(
    "/factors/categories",
    response_model=ApiResponse[dict[str, int]],
)
async def get_categories():
    """因子分类统计。"""
    svc = _get_factor_service()
    data = await run_sync(svc.get_categories)
    return ApiResponse(data=data)


@router.get(
    "/factors/{name}",
    response_model=ApiResponse[StockFactorDetail],
)
async def get_factor_detail(name: str):
    """因子详情。"""
    svc = _get_factor_service()
    detail = await run_sync(svc.get_factor_detail, name)
    if not detail:
        raise HTTPException(status_code=404, detail=f"因子不存在: {name}")
    return ApiResponse(data=StockFactorDetail(**detail))


@router.post("/factors/refresh", response_model=ApiResponse[dict])
async def refresh_factors():
    """刷新因子缓存。"""
    svc = _get_factor_service()
    count = await run_sync(svc.refresh_cache)
    return ApiResponse(data={"total": count}, message=f"已刷新 {count} 个因子")


# ---- 分析 ----


@router.get(
    "/analysis/available-backtests",
    response_model=ApiResponse[AvailableBacktestsResponse],
)
async def list_available_backtests():
    """列出可用回测数据源。"""
    svc = _get_analysis_service()
    backtests = await run_sync(svc.list_available_backtests)
    items = [BacktestSourceInfo(**b) for b in backtests]
    return ApiResponse(
        data=AvailableBacktestsResponse(backtests=items, total=len(items))
    )


@router.get(
    "/analysis/cached-factors",
    response_model=ApiResponse[list[CachedFactorInfo]],
)
async def list_cached_factors(
    backtest_name: str | None = Query(None, description="回测数据源名称"),
):
    """列出缓存因子。"""
    svc = _get_analysis_service()
    factors = await run_sync(svc.list_cached_factors, backtest_name)
    items = [CachedFactorInfo(**f) for f in factors]
    return ApiResponse(data=items)


@router.post(
    "/analysis/enhanced",
    response_model=ApiResponse[AnalysisTaskSubmitResponse],
)
async def run_enhanced_analysis(req: EnhancedAnalysisRequest):
    """提交增强单因子分析任务。"""
    runner = _get_analysis_runner()
    task_id = await run_sync(
        runner.submit_enhanced,
        factor_name=req.factor_name,
        period_offset_list=req.period_offset_list,
        rebalance_time=req.rebalance_time,
        bins=req.bins,
        backtest_name=req.backtest_name,
    )
    return ApiResponse(
        data=AnalysisTaskSubmitResponse(
            task_id=task_id,
            status="pending",
            task_type="enhanced",
            message="增强分析任务已提交",
        )
    )


@router.post(
    "/analysis/dual",
    response_model=ApiResponse[AnalysisTaskSubmitResponse],
)
async def run_dual_analysis(req: DualAnalysisRequest):
    """提交双因子分析任务。"""
    runner = _get_analysis_runner()
    task_id = await run_sync(
        runner.submit_dual,
        main_factor=req.main_factor,
        sub_factor=req.sub_factor,
        period_offset_list=req.period_offset_list,
        rebalance_time=req.rebalance_time,
        bins=req.bins,
        backtest_name=req.backtest_name,
    )
    return ApiResponse(
        data=AnalysisTaskSubmitResponse(
            task_id=task_id,
            status="pending",
            task_type="dual",
            message="双因子分析任务已提交",
        )
    )


@router.get(
    "/analysis/tasks/{task_id}/status",
    response_model=ApiResponse[AnalysisTaskStatusResponse],
)
async def get_analysis_task_status(task_id: str):
    """查询分析任务状态。"""
    runner = _get_analysis_runner()
    task = await run_sync(runner.get_status, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return ApiResponse(
        data=AnalysisTaskStatusResponse(
            task_id=task.task_id,
            status=task.status,
            task_type=task.task_type,
            message=task.message,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            error_message=task.error_message,
        )
    )


@router.get(
    "/analysis/tasks/{task_id}/result",
    response_model=ApiResponse[AnalysisTaskResultResponse],
)
async def get_analysis_task_result(task_id: str):
    """获取分析任务结果。"""
    runner = _get_analysis_runner()
    task = await run_sync(runner.get_status, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    if task.status in {"pending", "running"}:
        raise HTTPException(status_code=409, detail=f"任务尚未完成: {task_id}")

    return ApiResponse(
        data=AnalysisTaskResultResponse(
            task_id=task.task_id,
            status=task.status,
            task_type=task.task_type,
            result=await run_sync(runner.get_result, task_id),
            error_message=task.error_message,
        )
    )


# ---- 因子回测 ----


@router.post(
    "/analysis/factor-backtest",
    response_model=ApiResponse[AnalysisTaskSubmitResponse],
)
async def run_factor_backtest(req: FactorBacktestRequest):
    """提交因子回测任务（生成 factor_*.pkl）。"""
    runner = _get_analysis_runner()
    task_id = await run_sync(
        runner.submit_factor_backtest,
        factor_name=req.factor_name,
        start_date=req.start_date,
        end_date=req.end_date,
        factor_config=req.factor_config,
        backtest_name=req.backtest_name,
    )
    return ApiResponse(
        data=AnalysisTaskSubmitResponse(
            task_id=task_id,
            status="pending",
            task_type="factor_backtest",
            message="因子回测任务已提交",
        )
    )
