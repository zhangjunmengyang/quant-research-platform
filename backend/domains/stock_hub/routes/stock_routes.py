"""Stock Hub REST API 路由"""
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse

from pydantic import BaseModel

from domains.stock_hub.services.stock_factor_service import get_stock_factor_service
from domains.stock_hub.services.stock_backtest_service import get_stock_backtest_service
from domains.stock_hub.services.stock_analysis_service import get_stock_analysis_service
from domains.stock_hub.models.backtest_config_model import (
    BacktestRequest,
    StrategyConfig,
    FactorConfig,
    FilterConfig,
)

router = APIRouter()


@router.get("/status")
async def get_stock_hub_status():
    """Check if stock hub is fully configured"""
    from domains.stock_hub.config import (
        is_stock_framework_available,
        STOCK_FRAMEWORK_PATH,
        FUEL_PYTHON_PATH,
        FACTOR_LIB_PATH,
        SECTION_FACTOR_LIB_PATH,
    )
    available = is_stock_framework_available()
    return {
        "data": {
            "available": available,
            "stock_framework_path": str(STOCK_FRAMEWORK_PATH),
            "stock_framework_exists": STOCK_FRAMEWORK_PATH.exists(),
            "fuel_python_exists": FUEL_PYTHON_PATH.exists(),
            "factor_lib_exists": FACTOR_LIB_PATH.exists(),
            "section_factor_lib_exists": SECTION_FACTOR_LIB_PATH.exists(),
        }
    }


@router.get("/factors")
async def list_factors(
    category: Optional[str] = Query(None, description="分类: H财务/技术/截面"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """获取A股因子列表"""
    service = get_stock_factor_service()
    factors, total = await asyncio.to_thread(
        service.list_factors,
        category=category,
        search=search,
        page=page,
        page_size=page_size,
    )
    return {
        "data": {
            "factors": [f.model_dump() for f in factors],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    }


@router.get("/factors/categories")
async def get_categories():
    """获取因子分类统计"""
    service = get_stock_factor_service()
    categories = await asyncio.to_thread(service.get_categories)
    return {"data": categories}


@router.get("/factors/{name}")
async def get_factor(name: str, include_code: bool = Query(False)):
    """获取单个因子详情"""
    service = get_stock_factor_service()
    factor = await asyncio.to_thread(service.get_factor, name)
    if not factor:
        raise HTTPException(status_code=404, detail=f"因子不存在: {name}")
    result = factor.model_dump()
    if include_code:
        code = await asyncio.to_thread(service.get_factor_code, name)
        result["code"] = code
    return {"data": result}


@router.post("/factors/refresh")
async def refresh_factors():
    """刷新因子库缓存"""
    service = get_stock_factor_service()
    await asyncio.to_thread(service.refresh)
    categories = await asyncio.to_thread(service.get_categories)
    total = sum(categories.values())
    return {"data": {"message": f"已刷新，共 {total} 个因子", "categories": categories}}


@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """提交回测任务"""
    service = get_stock_backtest_service()
    task_id = await asyncio.to_thread(service.submit_backtest, request)
    task = service.get_task(task_id)
    return {"data": {"task_id": task_id, "result": task.get("result") if task else None}}


@router.get("/backtest/{task_id}")
async def get_backtest_result(task_id: str):
    """查询回测结果"""
    service = get_stock_backtest_service()
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return {"data": task}


@router.get("/backtest")
async def list_backtests():
    """列出所有回测任务"""
    service = get_stock_backtest_service()
    tasks = service.list_tasks()
    return {"data": {"tasks": tasks}}


# ---- 因子分析 ----

class AnalysisRequest(BaseModel):
    result_path: str
    factor_name: str
    hold_period: str = "W"
    group_num: int = 10


@router.post("/analysis/ic")
async def analyze_factor_ic(request: AnalysisRequest):
    """因子IC/ICIR/分组收益分析"""
    service = get_stock_analysis_service()
    result = await asyncio.to_thread(
        service.analyze_factor,
        result_path=request.result_path,
        factor_name=request.factor_name,
        hold_period=request.hold_period,
        group_num=request.group_num,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "分析失败"))
    return {"data": result.get("data", result)}


# ---- 因子评估 ----

@router.post("/evaluation")
async def evaluate_factor(request_data: dict):
    """触发因子AI评估"""
    from domains.stock_hub.services.stock_eval_service import get_stock_eval_service
    from domains.stock_hub.models.evaluation_model import EvaluationRequest

    try:
        eval_request = EvaluationRequest(**request_data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    service = get_stock_eval_service()
    try:
        result = await service.evaluate_factor(eval_request)
        return {"data": result.model_dump()}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")


@router.get("/evaluations")
async def list_evaluations():
    """列出所有因子评估"""
    from domains.stock_hub.services.stock_eval_service import get_stock_eval_service
    service = get_stock_eval_service()
    items = await asyncio.to_thread(service.list_evaluations)
    return {"data": {"evaluations": [item.model_dump() for item in items]}}


@router.get("/evaluation/{factor_name}")
async def get_evaluation(factor_name: str):
    """获取单个因子评估"""
    from domains.stock_hub.services.stock_eval_service import get_stock_eval_service
    service = get_stock_eval_service()
    evaluation = await asyncio.to_thread(service.get_evaluation, factor_name)
    if not evaluation:
        raise HTTPException(status_code=404, detail=f"No evaluation for: {factor_name}")
    return {"data": evaluation.model_dump()}


# ---- 增强因子分析（早盘换仓 + 全offset） ----

class EnhancedAnalysisRequest(BaseModel):
    factor_name: str
    period_offset_list: List[str] = ["5_0"]
    rebalance_time: str = "0955"
    bins: int = 10
    backtest_name: Optional[str] = None


class BatchAnalysisRequest(BaseModel):
    period_offset_list: List[str] = ["5_0"]
    rebalance_time: str = "0955"
    bins: int = 10
    max_workers: int = 3
    skip_existing: bool = True
    backtest_name: Optional[str] = None


class DualAnalysisRequest(BaseModel):
    main_factor: str
    sub_factor: str
    period_offset_list: List[str] = ["5_0"]
    rebalance_time: str = "0955"
    bins: int = 5
    backtest_name: Optional[str] = None


@router.get("/analysis/available-backtests")
async def list_available_backtests():
    """列出运行缓存中所有可用的回测数据源"""
    service = get_stock_analysis_service()
    result = await asyncio.to_thread(service.list_available_backtests)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "查询失败"))
    return {"data": result.get("data", result)}


@router.post("/analysis/dual")
async def dual_analyze(request: DualAnalysisRequest):
    """双因子分析 — 热力图 + 风格暴露"""
    service = get_stock_analysis_service()
    result = await asyncio.to_thread(
        service.dual_analyze,
        main_factor=request.main_factor,
        sub_factor=request.sub_factor,
        period_offset_list=request.period_offset_list,
        rebalance_time=request.rebalance_time,
        bins=request.bins,
        backtest_name=request.backtest_name,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "双因子分析失败"))
    return {"data": result.get("data", result)}


@router.post("/analysis/enhanced")
async def enhanced_analyze(request: EnhancedAnalysisRequest):
    """增强单因子分析 — 支持早盘换仓时间 + 全offset周期"""
    service = get_stock_analysis_service()
    result = await asyncio.to_thread(
        service.enhanced_analyze,
        factor_name=request.factor_name,
        period_offset_list=request.period_offset_list,
        rebalance_time=request.rebalance_time,
        bins=request.bins,
        backtest_name=request.backtest_name,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "分析失败"))
    return {"data": result.get("data", result)}


@router.get("/analysis/cached-factors")
async def list_cached_factors(backtest_name: Optional[str] = Query(None)):
    """列出运行缓存中可用于分析的因子"""
    service = get_stock_analysis_service()
    result = await asyncio.to_thread(service.list_cached_factors, backtest_name=backtest_name)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "查询失败"))
    return {"data": result.get("data", result)}


@router.post("/analysis/batch")
async def batch_analyze(request: BatchAnalysisRequest):
    """批量分析所有缓存因子"""
    service = get_stock_analysis_service()
    result = await asyncio.to_thread(
        service.batch_analyze,
        period_offset_list=request.period_offset_list,
        rebalance_time=request.rebalance_time,
        bins=request.bins,
        max_workers=request.max_workers,
        skip_existing=request.skip_existing,
        backtest_name=request.backtest_name,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "批量分析失败"))
    return {"data": result.get("data", result)}


@router.get("/analysis/results")
async def list_analysis_results(cfg_str: Optional[str] = Query(None)):
    """列出已有的分析结果摘要"""
    service = get_stock_analysis_service()
    results = await asyncio.to_thread(service.list_analysis_results, cfg_str)
    return {"data": {"results": results, "total": len(results)}}


@router.get("/analysis/report/{factor_name}")
async def get_analysis_report(
    factor_name: str,
    cfg_str: Optional[str] = Query(None),
):
    """获取因子分析HTML报告"""
    service = get_stock_analysis_service()
    report_path = service.get_analysis_report_path(factor_name, cfg_str)
    if not report_path or not report_path.exists():
        raise HTTPException(status_code=404, detail=f"报告不存在: {factor_name}")
    html_content = report_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html_content)
