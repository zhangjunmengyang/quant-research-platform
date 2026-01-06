"""
核心层：数据模型和存储
"""

from .models import Note
from .store import NoteStore, get_note_store

__all__ = ['Note', 'NoteStore', 'get_note_store']
