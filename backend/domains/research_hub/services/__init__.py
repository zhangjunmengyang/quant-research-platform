"""
Research Hub 服务层

提供:
- ChatBotService: 研报对话服务
- ReportService: 研报管理服务
- PipelineFactory: RAG 流水线工厂
"""

# 导入 rag 模块以触发组件注册（必须在使用 registry 之前）
from .. import rag  # noqa: F401

from .chatbot import ChatBotService, get_chatbot_service
from .report import ReportService, get_report_service
from .pipeline_factory import PipelineFactory, get_pipeline_factory

__all__ = [
    "ChatBotService",
    "get_chatbot_service",
    "ReportService",
    "get_report_service",
    "PipelineFactory",
    "get_pipeline_factory",
]
