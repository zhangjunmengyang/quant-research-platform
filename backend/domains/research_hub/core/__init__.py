"""
Research Hub 核心层

提供数据模型、存储层和配置管理。
"""

from .models import (
    ResearchReport,
    ResearchChunk,
    ProcessingStatus,
)
from .store import (
    ResearchStore,
    ChunkStore,
    get_research_store,
    get_chunk_store,
)

__all__ = [
    # 模型
    "ResearchReport",
    "ResearchChunk",
    "ProcessingStatus",
    # 存储
    "ResearchStore",
    "ChunkStore",
    "get_research_store",
    "get_chunk_store",
]
