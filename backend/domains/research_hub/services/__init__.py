"""
Research Hub 服务层

提供:
- ReportService: 研报管理服务（上传、解析、切块、向量化、索引）
- RetrievalService: 语义检索和 RAG 问答服务
- LlamaIndexRAGService: 基于 LlamaIndex 的 RAG 核心服务
"""

from .report import ReportService, get_report_service
from .retrieval import RetrievalService, get_retrieval_service
from .llamaindex_rag import (
    LlamaIndexRAGService,
    get_llamaindex_rag_service,
    get_initialized_rag_service,
)

__all__ = [
    "ReportService",
    "get_report_service",
    "RetrievalService",
    "get_retrieval_service",
    "LlamaIndexRAGService",
    "get_llamaindex_rag_service",
    "get_initialized_rag_service",
]
