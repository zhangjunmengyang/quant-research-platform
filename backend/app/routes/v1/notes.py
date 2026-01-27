"""Note API routes.

提供笔记的 CRUD 接口和研究记录功能。

支持:
- 基本 CRUD 操作
- 记录观察/假设/检验
- 归档管理
- 提炼为经验

NOTE: 所有同步服务调用都使用 run_sync 包装，避免阻塞 event loop。
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Path

from app.schemas.common import ApiResponse, PaginatedResponse, model_to_dict
from app.schemas.note import (
    Note,
    NoteCreate,
    NoteUpdate,
    NoteStats,
    NoteType,
    ObservationCreate,
    HypothesisCreate,
    VerificationCreate,
    PromoteRequest,
)
from app.core.deps import get_note_or_404, get_note_service
from app.core.async_utils import run_sync

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=ApiResponse[PaginatedResponse[Note]])
async def list_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tags: Optional[str] = None,
    note_type: Optional[NoteType] = None,
    is_archived: Optional[bool] = None,
    order_by: str = "updated_at",
    order_desc: bool = True,
    service=Depends(get_note_service),
):
    """
    获取笔记列表

    支持分页、搜索和筛选。
    """
    # 解析标签
    tags_list = None
    if tags:
        tags_list = [t.strip() for t in tags.split(',') if t.strip()]

    notes, total = await run_sync(
        service.list_notes,
        search=search or "",
        tags=tags_list,
        note_type=note_type.value if note_type else "",
        is_archived=is_archived,
        order_by=order_by,
        order_desc=order_desc,
        page=page,
        page_size=page_size,
    )

    items = [Note(**model_to_dict(n)) for n in notes]

    return ApiResponse(
        data=PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/stats", response_model=ApiResponse[NoteStats])
async def get_stats(service=Depends(get_note_service)):
    """获取笔记统计信息"""
    stats = await run_sync(service.get_stats)

    return ApiResponse(
        data=NoteStats(
            total=stats.get("total", 0),
            tags_count=stats.get("tags_count", 0),
            tags=stats.get("tags", []),
            active_count=stats.get("active_count", 0),
            archived_count=stats.get("archived_count", 0),
            promoted_count=stats.get("promoted_count", 0),
            by_type=stats.get("by_type", {}),
        )
    )


@router.get("/tags", response_model=ApiResponse[List[str]])
async def get_tags(service=Depends(get_note_service)):
    """获取所有标签列表"""
    tags = await run_sync(service.get_tags)
    return ApiResponse(data=tags)


@router.get("/{note_id}", response_model=ApiResponse[Note])
async def get_note(note=Depends(get_note_or_404)):
    """获取笔记详情"""
    return ApiResponse(data=Note(**model_to_dict(note)))


@router.get("/{note_id}/verifications", response_model=ApiResponse[List[Note]])
async def get_verifications(
    note_id: int = Path(..., description="假设笔记 ID"),
    include_archived: bool = Query(False, description="是否包含已归档的笔记"),
    service=Depends(get_note_service),
):
    """
    获取假设的所有验证笔记

    通过 Edge 系统查找关联到指定假设的验证笔记。
    """
    notes = await run_sync(
        service.get_verifications_for_hypothesis,
        hypothesis_id=note_id,
        include_archived=include_archived,
    )

    items = [Note(**model_to_dict(n)) for n in notes]
    return ApiResponse(data=items)


@router.post("/", response_model=ApiResponse[Note])
async def create_note(
    request: NoteCreate,
    service=Depends(get_note_service),
):
    """创建新笔记"""
    success, message, note_id = await run_sync(
        service.create_note,
        title=request.title,
        content=request.content,
        tags=request.tags,
        note_type=request.note_type.value if request.note_type else NoteType.OBSERVATION.value,
    )

    if not success or note_id is None:
        raise HTTPException(status_code=400, detail=message)

    note = await run_sync(service.get_note, note_id)
    return ApiResponse(data=Note(**model_to_dict(note)), message="创建成功")


@router.post("/observation", response_model=ApiResponse[Note])
async def record_observation(
    request: ObservationCreate,
    service=Depends(get_note_service),
):
    """
    记录观察

    观察是对数据或现象的客观记录，是研究的起点。
    """
    success, message, note_id = await run_sync(
        service.record_observation,
        title=request.title,
        content=request.content,
        tags=request.tags,
    )

    if not success or note_id is None:
        raise HTTPException(status_code=400, detail=message)

    note = await run_sync(service.get_note, note_id)
    return ApiResponse(data=Note(**model_to_dict(note)), message="观察记录成功")


@router.post("/hypothesis", response_model=ApiResponse[Note])
async def record_hypothesis(
    request: HypothesisCreate,
    service=Depends(get_note_service),
):
    """
    记录假设

    假设是基于观察提出的待验证假说。
    """
    success, message, note_id = await run_sync(
        service.record_hypothesis,
        title=request.title,
        content=request.content,
        tags=request.tags,
    )

    if not success or note_id is None:
        raise HTTPException(status_code=400, detail=message)

    note = await run_sync(service.get_note, note_id)
    return ApiResponse(data=Note(**model_to_dict(note)), message="假设记录成功")


@router.post("/verification", response_model=ApiResponse[Note])
async def record_verification(
    request: VerificationCreate,
    service=Depends(get_note_service),
):
    """
    记录检验

    检验是对假设的验证过程和结论。
    通过 Edge 系统关联到假设笔记。
    """
    success, message, note_id = await run_sync(
        service.record_verification,
        title=request.title,
        content=request.content,
        tags=request.tags,
        hypothesis_id=request.hypothesis_id,
    )

    if not success or note_id is None:
        raise HTTPException(status_code=400, detail=message)

    note = await run_sync(service.get_note, note_id)
    return ApiResponse(data=Note(**model_to_dict(note)), message="检验记录成功")


@router.patch("/{note_id}", response_model=ApiResponse[Note])
async def update_note(
    update: NoteUpdate,
    note=Depends(get_note_or_404),
    service=Depends(get_note_service),
):
    """更新笔记字段"""
    update_fields = update.model_dump(exclude_unset=True)

    # 处理枚举类型
    if "note_type" in update_fields and update_fields["note_type"] is not None:
        update_fields["note_type"] = update_fields["note_type"].value

    if not update_fields:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    note_id = note.id
    success = await run_sync(service.update_note, note_id, **update_fields)
    if not success:
        raise HTTPException(status_code=500, detail="更新失败")

    updated = await run_sync(service.get_note, note_id)
    return ApiResponse(data=Note(**model_to_dict(updated)), message="更新成功")


@router.post("/{note_id}/archive", response_model=ApiResponse[Note])
async def archive_note(
    note=Depends(get_note_or_404),
    service=Depends(get_note_service),
):
    """
    归档笔记

    归档后的笔记默认不会在列表中显示，但可以通过筛选查看。
    """
    success, message = await run_sync(service.archive_note, note.id)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    updated = await run_sync(service.get_note, note.id)
    return ApiResponse(data=Note(**model_to_dict(updated)), message=message)


@router.post("/{note_id}/unarchive", response_model=ApiResponse[Note])
async def unarchive_note(
    note=Depends(get_note_or_404),
    service=Depends(get_note_service),
):
    """
    取消归档笔记

    将已归档的笔记恢复为活跃状态。
    """
    success, message = await run_sync(service.unarchive_note, note.id)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    updated = await run_sync(service.get_note, note.id)
    return ApiResponse(data=Note(**model_to_dict(updated)), message=message)


@router.post("/{note_id}/promote", response_model=ApiResponse[Note])
async def promote_to_experience(
    request: PromoteRequest,
    note=Depends(get_note_or_404),
    service=Depends(get_note_service),
):
    """
    提炼为经验

    将笔记标记为已提炼为经验。实际创建经验需要调用 experience_hub。
    此端点仅标记笔记的提炼状态。
    """
    success, message = await run_sync(
        service.promote_to_experience,
        note.id,
        request.experience_id
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)

    updated = await run_sync(service.get_note, note.id)
    return ApiResponse(data=Note(**model_to_dict(updated)), message=message)


@router.delete("/{note_id}", response_model=ApiResponse[None])
async def delete_note(
    note=Depends(get_note_or_404),
    service=Depends(get_note_service),
):
    """删除笔记"""
    success = await run_sync(service.delete_note, note.id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")

    return ApiResponse(message="删除成功")
