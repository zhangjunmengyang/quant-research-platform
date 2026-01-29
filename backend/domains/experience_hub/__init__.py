"""
经验知识库领域模块

提供研究经验的结构化存储和检索功能。
基于 PARL 框架（Problem-Approach-Result-Lesson）存储可迁移的研究智慧。
以标签为核心进行分类管理。
"""

from .core.models import (
    EntityType,
    Experience,
    ExperienceContent,
    ExperienceContext,
    ExperienceLink,
    SourceType,
)
from .core.store import ExperienceStore, get_experience_store
from .services.experience import ExperienceService, get_experience_service

__all__ = [
    # 数据模型
    'Experience',
    'ExperienceContent',
    'ExperienceContext',
    'ExperienceLink',
    'SourceType',
    'EntityType',
    # 存储层
    'ExperienceStore',
    'get_experience_store',
    # 服务层
    'ExperienceService',
    'get_experience_service',
]
