"""
Research Hub 服务层

提供:
- ReportService: 研报管理服务（上传、解析、切块、向量化、索引）
- RetrievalService: 语义检索和 RAG 问答服务
- PipelineFactory: RAG 流水线工厂
"""

# 导入 rag 模块以触发组件注册（必须在使用 registry 之前）
from .. import rag  # noqa: F401

from .report import ReportService, get_report_service
from .retrieval import RetrievalService, get_retrieval_service
from .pipeline_factory import PipelineFactory, get_pipeline_factory

__all__ = [
    "ReportService",
    "get_report_service",
    "RetrievalService",
    "get_retrieval_service",
    "PipelineFactory",
    "get_pipeline_factory",
]
