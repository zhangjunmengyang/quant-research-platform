"""Note-related Pydantic schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class NoteType(str, Enum):
    """笔记类型枚举"""

    OBSERVATION = "observation"  # 观察 - 对数据或现象的客观记录
    HYPOTHESIS = "hypothesis"    # 假设 - 基于观察提出的假设
    FINDING = "finding"          # 发现 - 验证后的发现
    TRAIL = "trail"              # 轨迹 - 研究过程记录（自动生成）
    GENERAL = "general"          # 通用 - 一般性笔记（向后兼容）


class NoteBase(BaseModel):
    """Base note fields."""

    title: str = Field(..., description="笔记标题", min_length=1, max_length=500)
    content: str = Field("", description="笔记内容（Markdown 格式）")
    tags: str = Field("", description="标签（逗号分隔）")
    source: str = Field("", description="来源（如 factor, strategy, manual）")
    source_ref: str = Field("", description="来源引用")


class NoteCreate(NoteBase):
    """Note create request."""

    note_type: NoteType = Field(NoteType.GENERAL, description="笔记类型")
    research_session_id: Optional[str] = Field(None, description="研究会话 ID")


class NoteUpdate(BaseModel):
    """Note update request."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    tags: Optional[str] = None
    source: Optional[str] = None
    source_ref: Optional[str] = None
    note_type: Optional[NoteType] = None
    research_session_id: Optional[str] = None


class Note(NoteBase):
    """Complete note model for API responses."""

    id: int = Field(..., description="笔记 ID")
    note_type: NoteType = Field(NoteType.GENERAL, description="笔记类型")
    research_session_id: Optional[str] = Field(None, description="研究会话 ID")
    promoted_to_experience_id: Optional[int] = Field(None, description="已提炼为经验的 ID")
    is_archived: bool = Field(False, description="是否已归档")
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
    note_type: Optional[NoteType] = Field(None, description="笔记类型筛选")
    is_archived: Optional[bool] = Field(None, description="归档状态筛选")
    order_by: str = Field("updated_at", description="排序字段")
    order_desc: bool = Field(True, description="降序排序")


class NoteStats(BaseModel):
    """Note statistics."""

    total: int = Field(..., description="笔记总数")
    tags_count: int = Field(..., description="标签数量")
    tags: List[str] = Field(default_factory=list, description="所有标签")
    active_count: int = Field(0, description="活跃笔记数")
    archived_count: int = Field(0, description="已归档笔记数")
    promoted_count: int = Field(0, description="已提炼为经验的笔记数")
    session_count: int = Field(0, description="研究会话数")
    by_type: Dict[str, int] = Field(default_factory=dict, description="按类型统计")


# ==================== 研究记录相关 Schema ====================


class ObservationCreate(BaseModel):
    """记录观察请求"""

    title: str = Field(..., description="观察标题", min_length=1, max_length=500)
    content: str = Field(..., description="观察内容（Markdown 格式）")
    tags: str = Field("", description="标签（逗号分隔）")
    source: str = Field("", description="来源")
    source_ref: str = Field("", description="来源引用")
    research_session_id: Optional[str] = Field(None, description="研究会话 ID")


class HypothesisCreate(BaseModel):
    """记录假设请求"""

    title: str = Field(..., description="假设标题", min_length=1, max_length=500)
    content: str = Field(..., description="假设内容（Markdown 格式）")
    tags: str = Field("", description="标签（逗号分隔）")
    source: str = Field("", description="来源")
    source_ref: str = Field("", description="来源引用")
    research_session_id: Optional[str] = Field(None, description="研究会话 ID")


class FindingCreate(BaseModel):
    """记录发现请求"""

    title: str = Field(..., description="发现标题", min_length=1, max_length=500)
    content: str = Field(..., description="发现内容（Markdown 格式）")
    tags: str = Field("", description="标签（逗号分隔）")
    source: str = Field("", description="来源")
    source_ref: str = Field("", description="来源引用")
    research_session_id: Optional[str] = Field(None, description="研究会话 ID")


class PromoteRequest(BaseModel):
    """提炼为经验请求"""

    experience_id: int = Field(..., description="经验 ID")


class ResearchTrail(BaseModel):
    """研究轨迹响应"""

    session_id: str = Field(..., description="研究会话 ID")
    notes: List[Note] = Field(default_factory=list, description="笔记列表")
    total: int = Field(0, description="笔记总数")
    by_type: Dict[str, int] = Field(default_factory=dict, description="按类型统计")
