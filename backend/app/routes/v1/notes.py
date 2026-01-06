"""Note API routes.

提供笔记的 CRUD 接口。

NOTE: 所有同步服务调用都使用 run_sync 包装，避免阻塞 event loop。
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.common import ApiResponse, PaginatedResponse, model_to_dict
from app.schemas.note import (
    Note,
    NoteCreate,
    NoteUpdate,
    NoteStats,
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
    source: Optional[str] = None,
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
        source=source or "",
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
        source=request.source,
        source_ref=request.source_ref,
    )

    if not success or note_id is None:
        raise HTTPException(status_code=400, detail=message)

    note = await run_sync(service.get_note, note_id)
    return ApiResponse(data=Note(**model_to_dict(note)), message="创建成功")


@router.patch("/{note_id}", response_model=ApiResponse[Note])
async def update_note(
    update: NoteUpdate,
    note=Depends(get_note_or_404),
    service=Depends(get_note_service),
):
    """更新笔记字段"""
    update_fields = update.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    note_id = note.id
    success = await run_sync(service.update_note, note_id, **update_fields)
    if not success:
        raise HTTPException(status_code=500, detail="更新失败")

    updated = await run_sync(service.get_note, note_id)
    return ApiResponse(data=Note(**model_to_dict(updated)), message="更新成功")


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
