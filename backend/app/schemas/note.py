"""Note-related Pydantic schemas."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    """Base note fields."""

    title: str = Field(..., description="笔记标题", min_length=1, max_length=500)
    content: str = Field("", description="笔记内容（Markdown 格式）")
    tags: str = Field("", description="标签（逗号分隔）")
    source: str = Field("", description="来源（如 factor, strategy, manual）")
    source_ref: str = Field("", description="来源引用")


class NoteCreate(NoteBase):
    """Note create request."""

    pass


class NoteUpdate(BaseModel):
    """Note update request."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    tags: Optional[str] = None
    source: Optional[str] = None
    source_ref: Optional[str] = None


class Note(NoteBase):
    """Complete note model for API responses."""

    id: int = Field(..., description="笔记 ID")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NoteListParams(BaseModel):
    """Note list query parameters."""

    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    search: Optional[str] = Field(None, description="搜索关键词")
    tags: Optional[str] = Field(None, description="标签筛选（逗号分隔）")
    source: Optional[str] = Field(None, description="来源筛选")
    order_by: str = Field("updated_at", description="排序字段")
    order_desc: bool = Field(True, description="降序排序")


class NoteStats(BaseModel):
    """Note statistics."""

    total: int = Field(..., description="笔记总数")
    tags_count: int = Field(..., description="标签数量")
    tags: List[str] = Field(default_factory=list, description="所有标签")
