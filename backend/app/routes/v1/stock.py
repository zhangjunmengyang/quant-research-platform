"""Stock Hub REST API 路由。"""

import json
import logging

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import StreamingResponse

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
    EvaluationRequest,
    FactorEvaluationCreate,
    FactorEvaluationListResponse,
    FactorEvaluationResponse,
    FactorEvaluationUpdate,
    PromptReadResponse,
    PromptUpdateRequest,
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


def _get_evaluate_service():
    from domains.stock_hub.services.stock_evaluate_service import (
        get_stock_evaluate_service,
    )

    return get_stock_evaluate_service()


def _get_evaluation_library_service():
    from domains.stock_hub.services.factor_evaluation_library_service import (
        get_factor_evaluation_library_service,
    )
    return get_factor_evaluation_library_service()


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


# ---- AI 评估 ----


@router.post("/analysis/evaluate")
async def evaluate_analysis(req: EvaluationRequest):
    """AI 评估因子分析结果（SSE 流式返回）。"""
    svc = _get_evaluate_service()

    async def event_generator():
        try:
            async for chunk in svc.evaluate_stream(
                eval_type=req.evaluation_type,
                analysis_result=req.analysis_result,
                model_key=req.model_key,
            ):
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("evaluate_stream_error")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---- 提示词管理 ----


@router.get(
    "/prompts/{eval_type}",
    response_model=ApiResponse[PromptReadResponse],
)
async def get_prompt(eval_type: str):
    """获取评估提示词配置。"""
    svc = _get_evaluate_service()
    try:
        data = await run_sync(svc.get_prompt_config, eval_type)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ApiResponse(data=PromptReadResponse(**data))


@router.put(
    "/prompts/{eval_type}",
    response_model=ApiResponse[dict],
)
async def update_prompt(eval_type: str, req: PromptUpdateRequest):
    """更新评估提示词配置。"""
    svc = _get_evaluate_service()
    try:
        await run_sync(svc.update_prompt_config, eval_type, req.system, req.user)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ApiResponse(data={"updated": True}, message="提示词已更新")


# ---- 因子评估库 ----


@router.post(
    "/evaluations",
    response_model=ApiResponse[FactorEvaluationResponse],
)
async def save_evaluation(req: FactorEvaluationCreate):
    """保存因子评估到库。"""
    svc = _get_evaluation_library_service()
    ev = await run_sync(
        svc.save,
        factor_name=req.factor_name,
        title=req.title,
        evaluations=req.evaluations,
        analysis_snapshot=req.analysis_snapshot,
        tags=req.tags,
    )
    return ApiResponse(
        data=FactorEvaluationResponse(
            id=ev.id,
            uuid=ev.uuid,
            factor_name=ev.factor_name,
            title=ev.title,
            evaluations=ev.content.evaluations,
            analysis_snapshot=ev.content.analysis_snapshot,
            tags=ev.tags,
            created_at=ev.created_at,
            updated_at=ev.updated_at,
        ),
        message="因子评估已保存",
    )


@router.get(
    "/evaluations",
    response_model=ApiResponse[FactorEvaluationListResponse],
)
async def list_evaluations(
    factor_name: str | None = Query(None),
    tags: str | None = Query(None, description="逗号分隔的标签"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """查询因子评估列表。"""
    svc = _get_evaluation_library_service()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    items, total = await run_sync(
        svc.list,
        factor_name=factor_name,
        tags=tag_list,
        search=search,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=FactorEvaluationListResponse(
            items=[
                FactorEvaluationResponse(
                    id=ev.id,
                    uuid=ev.uuid,
                    factor_name=ev.factor_name,
                    title=ev.title,
                    evaluations=ev.content.evaluations,
                    analysis_snapshot=ev.content.analysis_snapshot,
                    tags=ev.tags,
                    created_at=ev.created_at,
                    updated_at=ev.updated_at,
                )
                for ev in items
            ],
            total=total,
        )
    )


@router.get(
    "/evaluations/tags",
    response_model=ApiResponse[list[str]],
)
async def get_evaluation_tags():
    """获取所有评估标签。"""
    svc = _get_evaluation_library_service()
    tags = await run_sync(svc.get_all_tags)
    return ApiResponse(data=tags)


@router.get(
    "/evaluations/{uuid}",
    response_model=ApiResponse[FactorEvaluationResponse],
)
async def get_evaluation(uuid: str):
    """获取单条因子评估详情。"""
    svc = _get_evaluation_library_service()
    ev = await run_sync(svc.get, uuid)
    if not ev:
        raise HTTPException(status_code=404, detail=f"评估记录不存在: {uuid}")
    return ApiResponse(
        data=FactorEvaluationResponse(
            id=ev.id,
            uuid=ev.uuid,
            factor_name=ev.factor_name,
            title=ev.title,
            evaluations=ev.content.evaluations,
            analysis_snapshot=ev.content.analysis_snapshot,
            tags=ev.tags,
            created_at=ev.created_at,
            updated_at=ev.updated_at,
        )
    )


@router.put(
    "/evaluations/{uuid}",
    response_model=ApiResponse[dict],
)
async def update_evaluation(uuid: str, req: FactorEvaluationUpdate):
    """更新因子评估记录。"""
    svc = _get_evaluation_library_service()
    fields = req.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="无更新字段")
    ok = await run_sync(svc.update, uuid, **fields)
    if not ok:
        raise HTTPException(status_code=404, detail=f"评估记录不存在: {uuid}")
    return ApiResponse(data={"updated": True}, message="评估记录已更新")


@router.delete(
    "/evaluations/{uuid}",
    response_model=ApiResponse[dict],
)
async def delete_evaluation(uuid: str):
    """删除因子评估记录。"""
    svc = _get_evaluation_library_service()
    ok = await run_sync(svc.delete, uuid)
    if not ok:
        raise HTTPException(status_code=404, detail=f"评估记录不存在: {uuid}")
    return ApiResponse(data={"deleted": True}, message="评估记录已删除")
