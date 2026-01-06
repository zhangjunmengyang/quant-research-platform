"""Strategy API routes.

与 MCP 工具统一使用 StrategyService 服务层，遵循分层架构规范。

NOTE: 所有同步服务调用都使用 run_sync 包装，避免阻塞 event loop。
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.common import ApiResponse, PaginatedResponse, model_to_dict
from app.schemas.strategy import Strategy, StrategyStats, StrategyCreate, StrategyUpdate
from app.core.deps import get_strategy_service
from app.core.async_utils import run_sync

router = APIRouter()


@router.get("/", response_model=ApiResponse[PaginatedResponse[Strategy]])
async def list_strategies(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    verified: Optional[bool] = None,
    order_by: str = "created_at",
    service=Depends(get_strategy_service),
):
    """获取策略列表"""
    try:
        filters = {}
        if verified is not None:
            filters["verified"] = verified

        strategies, total = await run_sync(
            service.list_strategies,
            filters=filters if filters else None,
            order_by=order_by,
            page=page,
            page_size=page_size,
        )

        items = [Strategy(**model_to_dict(s)) for s in strategies]

        return ApiResponse(
            data=PaginatedResponse.create(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ApiResponse[StrategyStats])
async def get_stats(service=Depends(get_strategy_service)):
    """获取策略统计信息"""
    try:
        stats = await run_sync(service.get_stats)
        return ApiResponse(
            data=StrategyStats(
                total=stats.get("total", 0),
                verified=stats.get("verified", 0),
                avg_sharpe=stats.get("avg_sharpe_ratio"),
                avg_return=stats.get("avg_annual_return"),
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}", response_model=ApiResponse[Strategy])
async def get_strategy(strategy_id: str, service=Depends(get_strategy_service)):
    """获取策略详情"""
    strategy = await run_sync(service.get_strategy, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"策略不存在: {strategy_id}")

    return ApiResponse(data=Strategy(**model_to_dict(strategy)))


@router.post("/", response_model=ApiResponse[Strategy])
async def create_strategy(request: StrategyCreate, service=Depends(get_strategy_service)):
    """创建策略"""
    try:
        strategy = await run_sync(
            service.create_strategy_from_dict, **request.model_dump()
        )
        return ApiResponse(
            data=Strategy(**model_to_dict(strategy)), message="创建成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{strategy_id}", response_model=ApiResponse[Strategy])
async def update_strategy(
    strategy_id: str,
    update: StrategyUpdate,
    service=Depends(get_strategy_service),
):
    """更新策略"""
    strategy = await run_sync(service.get_strategy, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"策略不存在: {strategy_id}")

    update_fields = update.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    success = await run_sync(service.update_strategy_fields, strategy_id, **update_fields)
    if not success:
        raise HTTPException(status_code=500, detail="更新失败")

    updated = await run_sync(service.get_strategy, strategy_id)
    return ApiResponse(data=Strategy(**model_to_dict(updated)), message="更新成功")


@router.delete("/{strategy_id}", response_model=ApiResponse[None])
async def delete_strategy(strategy_id: str, service=Depends(get_strategy_service)):
    """删除策略"""
    strategy = await run_sync(service.get_strategy, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"策略不存在: {strategy_id}")

    success = await run_sync(service.delete_strategy, strategy_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")

    return ApiResponse(message="删除成功")
