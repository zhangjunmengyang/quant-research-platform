"""
研究笔记知识库领域模块

Note Hub 定位为"研究草稿/临时记录"层（Knowledge Layer），
用于存储研究过程中的观察、假设、发现和研究轨迹。
笔记可以被提炼为正式经验（Experience）。

核心功能：
- 笔记类型分类：observation/hypothesis/finding/trail/general
- 研究会话追踪：通过 research_session_id 追踪研究轨迹
- 归档管理：支持归档/取消归档
- 提炼为经验：关联到 experience_hub
"""

from .core.models import Note, NoteType
from .core.store import NoteStore, get_note_store
from .services.note_service import NoteService, get_note_service

__all__ = [
    'Note',
    'NoteType',
    'NoteStore',
    'get_note_store',
    'NoteService',
    'get_note_service',
]
