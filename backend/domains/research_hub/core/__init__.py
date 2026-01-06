"""
Research Hub 核心层

提供数据模型、存储层和配置管理。
"""

from .models import (
    ResearchReport,
    ResearchChunk,
    Conversation,
    Message,
    ProcessingStatus,
)
from .store import (
    ResearchStore,
    ChunkStore,
    ConversationStore,
    get_research_store,
    get_chunk_store,
    get_conversation_store,
)

__all__ = [
    # 模型
    "ResearchReport",
    "ResearchChunk",
    "Conversation",
    "Message",
    "ProcessingStatus",
    # 存储
    "ResearchStore",
    "ChunkStore",
    "ConversationStore",
    "get_research_store",
    "get_chunk_store",
    "get_conversation_store",
]
