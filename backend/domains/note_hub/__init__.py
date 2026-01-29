"""
研究笔记知识库领域模块

Note Hub 定位为"研究草稿/临时记录"层（Knowledge Layer），
用于存储研究过程中的观察、假设和检验。
笔记可以被提炼为正式经验（Experience）。

研究流程：观察 -> 假设 -> 检验
- observation: 观察 - 对数据或现象的客观记录
- hypothesis: 假设 - 基于观察提出的待验证假说
- verification: 检验 - 对假设的验证过程和结论

核心功能：
- 笔记类型分类：observation/hypothesis/verification
- 实体关联：通过 Graph 系统 (graph_hub) 管理
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
