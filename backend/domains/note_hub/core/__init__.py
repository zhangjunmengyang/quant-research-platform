"""
核心层：数据模型和存储

Note Hub 定位为"研究草稿/临时记录"层，支持：
- 笔记类型分类（observation/hypothesis/finding/trail/general）
- 研究会话追踪
- 归档管理
- 提炼为经验
"""

from .models import Note, NoteType
from .store import NoteStore, get_note_store

__all__ = ['Note', 'NoteType', 'NoteStore', 'get_note_store']
