"""
Research Hub 服务层

提供:
- ReportService: 研报管理服务（上传、解析、切块、向量化、索引）
- RetrievalService: 语义检索服务
- LlamaIndexRAGService: 基于 LlamaIndex 的向量存储核心服务
- QueryProcessor: 查询重写和结果重排
"""

from .report import ReportService, get_report_service
from .retrieval import RetrievalService, get_retrieval_service
from .llamaindex_rag import (
    LlamaIndexRAGService,
    get_llamaindex_rag_service,
    get_initialized_rag_service,
)
from .query_processor import QueryProcessor, get_query_processor

__all__ = [
    "ReportService",
    "get_report_service",
    "RetrievalService",
    "get_retrieval_service",
    "LlamaIndexRAGService",
    "get_llamaindex_rag_service",
    "get_initialized_rag_service",
    "QueryProcessor",
    "get_query_processor",
]
