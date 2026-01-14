"""
Research Hub 服务层

提供:
- ReportService: 研报管理服务（上传、解析、切块、向量化、索引）
- RetrievalService: 语义检索和 RAG 问答服务
- LlamaIndexRAGService: 基于 LlamaIndex 的 RAG 核心服务

版本说明:
- v1 (report.py, retrieval.py): 使用自研 rag/ 模块
- v2 (report_v2.py, retrieval_v2.py): 使用 LlamaIndex 框架

切换版本:
- 默认使用 v2 (LlamaIndex)
- 如需使用 v1，修改下方导入
"""

import os

# 通过环境变量控制使用哪个版本
# RAG_VERSION=v1 使用旧版本，默认使用 v2 (LlamaIndex)
RAG_VERSION = os.getenv("RAG_VERSION", "v2")

if RAG_VERSION == "v1":
    # 旧版本：使用自研 rag/ 模块
    # 导入 rag 模块以触发组件注册
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
else:
    # 新版本：使用 LlamaIndex
    from .report_v2 import ReportService, get_report_service
    from .retrieval_v2 import RetrievalService, get_retrieval_service
    from .llamaindex_rag import (
        LlamaIndexRAGService,
        get_llamaindex_rag_service,
        get_initialized_rag_service,
    )

    # 兼容性：提供空的 PipelineFactory
    class PipelineFactory:
        """兼容性占位，LlamaIndex 版本不使用"""
        pass

    def get_pipeline_factory():
        """兼容性占位"""
        return PipelineFactory()

    __all__ = [
        "ReportService",
        "get_report_service",
        "RetrievalService",
        "get_retrieval_service",
        "LlamaIndexRAGService",
        "get_llamaindex_rag_service",
        "get_initialized_rag_service",
        "PipelineFactory",
        "get_pipeline_factory",
    ]
