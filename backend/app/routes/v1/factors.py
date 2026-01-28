"""Factor API routes.

与 MCP 工具统一使用 FactorService 服务层，遵循分层架构规范。

NOTE: 所有同步服务调用都使用 run_sync 包装，避免阻塞 event loop。
"""

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.common import ApiResponse, PaginatedResponse, model_to_dict
from app.schemas.factor import (
    Factor,
    FactorUpdate,
    FactorStats,
    FactorVerifyRequest,
    FactorCreateRequest,
    FactorCreateResponse,
    FactorCodeUpdate,
    FactorTypeEnum,
    ExcludedFilter,
    ExcludeRequest,
)
from app.core.deps import get_factor_or_404, get_factor_service
from app.core.async_utils import run_sync

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=ApiResponse[PaginatedResponse[Factor]])
async def list_factors(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    search: Optional[str] = None,
    style: Optional[str] = None,
    factor_type: Optional[FactorTypeEnum] = None,
    score_min: Optional[float] = Query(None, ge=0, le=5),
    score_max: Optional[float] = Query(None, ge=0, le=5),
    verification_status: Optional[int] = Query(None, description="验证状态筛选（0=未验证, 1=通过, 2=废弃）"),
    excluded: ExcludedFilter = Query(ExcludedFilter.ACTIVE, description="排除状态筛选"),
    order_by: str = "created_at",
    order_desc: bool = True,
    service=Depends(get_factor_service),
):
    """
    获取因子列表

    支持分页、搜索、筛选和排序。
    """
    # Build filter conditions
    filter_condition = {}

    if search:
        filter_condition["filename"] = f"contains:{search}"

    if style and style != "全部":
        filter_condition["style"] = f"contains:{style}"

    if factor_type:
        filter_condition["factor_type"] = factor_type.value

    # 支持范围过滤：同时指定 min 和 max 时使用列表形式
    score_filters = []
    if score_min is not None:
        score_filters.append(f">={score_min}")
    if score_max is not None:
        score_filters.append(f"<={score_max}")
    if score_filters:
        filter_condition["llm_score"] = score_filters if len(score_filters) > 1 else score_filters[0]

    if verification_status is not None:
        filter_condition["verification_status"] = verification_status

    # 处理排除状态筛选
    include_excluded = False
    if excluded == ExcludedFilter.ALL:
        include_excluded = True
    elif excluded == ExcludedFilter.EXCLUDED:
        include_excluded = True
        filter_condition["excluded"] = True

    # Query factors through service layer (run_sync to avoid blocking event loop)
    sort_direction = "DESC" if order_desc else "ASC"
    order_by_str = f"{order_by} {sort_direction}" if order_by else None

    page_factors, total = await run_sync(
        service.query_factors,
        filter_condition=filter_condition if filter_condition else None,
        order_by=order_by_str,
        include_excluded=include_excluded,
        page=page,
        page_size=page_size,
    )

    # Convert to response model
    items = [Factor(**model_to_dict(f)) for f in page_factors]

    return ApiResponse(
        data=PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/stats", response_model=ApiResponse[FactorStats])
async def get_stats(service=Depends(get_factor_service)):
    """获取因子库统计信息"""
    stats = await run_sync(service.get_stats)

    # score_stats 包含 avg, min, max
    score_stats = stats.get("score_stats", {})

    # 计算因子类型分布
    factor_type_dist = stats.get("factor_type_distribution", {})
    if not factor_type_dist:
        # 如果 service 没有返回，手动计算
        all_factors = await run_sync(service.query)
        factor_type_dist = {}
        for f in all_factors:
            ft = getattr(f, 'factor_type', 'time_series') or 'time_series'
            factor_type_dist[ft] = factor_type_dist.get(ft, 0) + 1

    return ApiResponse(
        data=FactorStats(
            total=stats.get("total", 0),
            excluded=stats.get("excluded", 0),
            scored=stats.get("scored", 0),
            passed=stats.get("passed", 0),
            failed=stats.get("failed", 0),
            avg_score=score_stats.get("avg"),
            style_distribution=stats.get("style_distribution", {}),
            score_distribution=stats.get("score_distribution", {}),
            factor_type_distribution=factor_type_dist,
        )
    )


@router.get("/styles", response_model=ApiResponse[List[str]])
async def get_styles(service=Depends(get_factor_service)):
    """获取所有因子风格列表"""
    styles = await run_sync(service.get_styles)
    return ApiResponse(data=styles)


@router.get("/{filename}", response_model=ApiResponse[Factor])
async def get_factor(factor=Depends(get_factor_or_404)):
    """获取因子详情"""
    factor_dict = model_to_dict(factor)

    # 如果 code_content 为空，从 code_path 读取代码内容
    if not factor_dict.get("code_content") and factor_dict.get("code_path"):
        code_path = Path(factor_dict["code_path"])
        if code_path.exists():
            try:
                factor_dict["code_content"] = code_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("读取因子代码文件失败 %s: %s", code_path, e)

    return ApiResponse(data=Factor(**factor_dict))


@router.patch("/{filename}", response_model=ApiResponse[Factor])
async def update_factor(
    update: FactorUpdate,
    factor=Depends(get_factor_or_404),
    service=Depends(get_factor_service),
):
    """更新因子字段"""
    # Get non-None fields to update
    update_fields = update.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    # Update factor (run_sync to avoid blocking event loop)
    filename = factor.filename
    success = await run_sync(service.update_factor, filename, **update_fields)
    if not success:
        raise HTTPException(status_code=500, detail="更新失败")

    # Return updated factor
    updated = await run_sync(service.get_factor, filename)
    return ApiResponse(data=Factor(**model_to_dict(updated)), message="更新成功")


@router.delete("/{filename}", response_model=ApiResponse[None])
async def delete_factor(
    factor=Depends(get_factor_or_404),
    service=Depends(get_factor_service),
):
    """删除因子"""
    success = await run_sync(service.delete_factor, factor.filename)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")

    return ApiResponse(message="删除成功")


@router.post("/{filename}/pass", response_model=ApiResponse[Factor])
async def mark_factor_passed(
    request: FactorVerifyRequest = None,
    factor=Depends(get_factor_or_404),
    service=Depends(get_factor_service),
):
    """标记因子为验证通过"""
    note = request.note if request else None
    filename = factor.filename
    success = await run_sync(service.mark_factor_as_passed, filename, note or "")
    if not success:
        raise HTTPException(status_code=500, detail="标记失败")

    updated = await run_sync(service.get_factor, filename)
    return ApiResponse(data=Factor(**model_to_dict(updated)), message="已标记为通过")


@router.post("/{filename}/fail", response_model=ApiResponse[Factor])
async def mark_factor_failed(
    request: FactorVerifyRequest = None,
    factor=Depends(get_factor_or_404),
    service=Depends(get_factor_service),
):
    """标记因子为废弃（失败研究）"""
    note = request.note if request else None
    filename = factor.filename
    success = await run_sync(service.mark_factor_as_failed, filename, note or "")
    if not success:
        raise HTTPException(status_code=500, detail="标记失败")

    updated = await run_sync(service.get_factor, filename)
    return ApiResponse(data=Factor(**model_to_dict(updated)), message="已标记为废弃")


@router.post("/{filename}/reset-verification", response_model=ApiResponse[Factor])
async def reset_factor_verification(
    factor=Depends(get_factor_or_404),
    service=Depends(get_factor_service),
):
    """重置因子验证状态为未验证"""
    filename = factor.filename
    success = await run_sync(service.reset_factor_verification, filename)
    if not success:
        raise HTTPException(status_code=500, detail="重置失败")

    updated = await run_sync(service.get_factor, filename)
    return ApiResponse(data=Factor(**model_to_dict(updated)), message="已重置验证状态")


@router.post("/", response_model=ApiResponse[FactorCreateResponse])
async def create_factor(
    request: FactorCreateRequest,
    service=Depends(get_factor_service),
):
    """
    创建新因子

    将因子代码保存到文件系统和数据库。
    如果没有指定 filename，会自动从代码中提取因子名或使用时间戳生成。
    """
    # 如果没有提供 filename，使用自动入库方法
    if not request.filename:
        success, message, factor_name = await run_sync(
            service.ingest_factor_from_code,
            code_content=request.code_content,
            auto_name=True,
        )
        if success and factor_name:
            # 如果有额外字段，更新因子
            if request.style or request.formula or request.description:
                await run_sync(
                    service.update_factor,
                    factor_name,
                    style=request.style or "",
                    formula=request.formula or "",
                    description=request.description or "",
                )
            return ApiResponse(
                data=FactorCreateResponse(
                    filename=factor_name,
                    message=message,
                    auto_named=True,
                )
            )
        else:
            raise HTTPException(status_code=400, detail=message)

    # 使用提供的 filename 创建
    success, message = await run_sync(
        service.create_factor,
        filename=request.filename,
        code_content=request.code_content,
        style=request.style or "",
        formula=request.formula or "",
        description=request.description or "",
        save_to_file=True,
    )

    if success:
        return ApiResponse(
            data=FactorCreateResponse(
                filename=request.filename,
                message=message,
                auto_named=False,
            )
        )
    else:
        raise HTTPException(status_code=400, detail=message)


@router.patch("/{filename}/code", response_model=ApiResponse[Factor])
async def update_factor_code(
    request: FactorCodeUpdate,
    factor=Depends(get_factor_or_404),
    service=Depends(get_factor_service),
):
    """
    更新因子代码

    同时更新数据库中的代码记录和文件系统中的代码文件。
    """
    filename = factor.filename
    success, message = await run_sync(
        service.update_factor_code,
        filename=filename,
        code_content=request.code_content,
        sync_to_file=True,
    )

    if not success:
        raise HTTPException(status_code=500, detail=message)

    updated = await run_sync(service.get_factor, filename)
    return ApiResponse(data=Factor(**model_to_dict(updated)), message="代码更新成功")


@router.post("/{filename}/exclude", response_model=ApiResponse[Factor])
async def exclude_factor(
    request: ExcludeRequest = None,
    factor=Depends(get_factor_or_404),
    service=Depends(get_factor_service),
):
    """排除因子（标记为已排除，不删除数据）"""
    reason = request.reason if request else ""
    filename = factor.filename
    success = await run_sync(service.exclude_factor, filename, reason or "")
    if not success:
        raise HTTPException(status_code=500, detail="排除失败")

    # 需要用 include_excluded=True 才能获取已排除的因子
    updated = await run_sync(service.get_factor_with_excluded, filename)
    return ApiResponse(data=Factor(**model_to_dict(updated)), message="已排除")


@router.post("/{filename}/unexclude", response_model=ApiResponse[Factor])
async def unexclude_factor(
    factor=Depends(get_factor_or_404),
    service=Depends(get_factor_service),
):
    """取消排除因子"""
    filename = factor.filename
    success = await run_sync(service.unexclude_factor, filename)
    if not success:
        raise HTTPException(status_code=500, detail="取消排除失败")

    updated = await run_sync(service.get_factor, filename)
    return ApiResponse(data=Factor(**model_to_dict(updated)), message="已取消排除")


# ===== 一致性检测和清理 =====


@router.get("/consistency/check", response_model=ApiResponse)
async def check_consistency(service=Depends(get_factor_service)):
    """
    检测因子库一致性

    对比代码文件、数据库记录、元数据YAML三者是否同步。

    返回：
    - is_consistent: 是否一致
    - orphan_db_records: 数据库中存在但代码文件已删除的因子
    - orphan_metadata: 元数据存在但代码文件已删除的因子
    """
    result = await run_sync(service.check_consistency)
    return ApiResponse(data=result)


@router.post("/consistency/cleanup", response_model=ApiResponse)
async def cleanup_orphans(
    dry_run: bool = Query(True, description="是否仅预览（不实际删除）"),
    service=Depends(get_factor_service),
):
    """
    清理孤立数据

    删除代码文件已不存在但数据库/元数据仍残留的记录。

    参数：
    - dry_run: 是否仅预览（默认 true，不实际删除）

    设置 dry_run=false 才会实际执行删除操作。
    """
    result = await run_sync(service.cleanup_orphans, dry_run=dry_run)
    return ApiResponse(data=result, message="预览完成" if dry_run else "清理完成")
