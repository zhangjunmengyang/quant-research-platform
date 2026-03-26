"""Stock Hub REST API 路由。"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.async_utils import run_sync
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.stock import (
    AnalysisResultResponse,
    AvailableBacktestsResponse,
    BacktestSourceInfo,
    CachedFactorInfo,
    DualAnalysisRequest,
    DualAnalysisResultResponse,
    EnhancedAnalysisRequest,
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
    search: Optional[str] = None,
    category: Optional[str] = None,
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
    """因子详情（含源码）。"""
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
    backtest_name: Optional[str] = Query(None, description="回测数据源名称"),
):
    """列出缓存因子。"""
    svc = _get_analysis_service()
    factors = await run_sync(svc.list_cached_factors, backtest_name)
    items = [CachedFactorInfo(**f) for f in factors]
    return ApiResponse(data=items)


@router.post(
    "/analysis/enhanced",
    response_model=ApiResponse[AnalysisResultResponse],
)
async def run_enhanced_analysis(req: EnhancedAnalysisRequest):
    """执行增强单因子分析。"""
    svc = _get_analysis_service()
    result = await run_sync(
        svc.run_enhanced_analysis,
        factor_name=req.factor_name,
        period_offset_list=req.period_offset_list,
        rebalance_time=req.rebalance_time,
        bins=req.bins,
        backtest_name=req.backtest_name,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return ApiResponse(data=AnalysisResultResponse(**result))


@router.post(
    "/analysis/dual",
    response_model=ApiResponse[DualAnalysisResultResponse],
)
async def run_dual_analysis(req: DualAnalysisRequest):
    """执行双因子分析。"""
    svc = _get_analysis_service()
    result = await run_sync(
        svc.run_dual_analysis,
        main_factor=req.main_factor,
        sub_factor=req.sub_factor,
        period_offset_list=req.period_offset_list,
        rebalance_time=req.rebalance_time,
        bins=req.bins,
        backtest_name=req.backtest_name,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return ApiResponse(data=DualAnalysisResultResponse(**result))
