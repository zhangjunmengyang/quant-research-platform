"""
经验笔记知识库领域模块

提供笔记的存储、查询和管理功能。
"""

from .core.models import Note
from .core.store import NoteStore, get_note_store
from .services.note_service import NoteService, get_note_service

__all__ = [
    'Note',
    'NoteStore',
    'get_note_store',
    'NoteService',
    'get_note_service',
]
