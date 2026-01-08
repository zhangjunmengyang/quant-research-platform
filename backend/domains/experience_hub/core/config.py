"""
Experience Hub 配置管理

支持从环境变量和配置文件加载配置。
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingConfig(BaseModel):
    """向量化配置"""
    enabled: bool = True
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    batch_size: int = 32


class VectorStoreConfig(BaseModel):
    """向量存储配置"""
    type: str = "pgvector"
    index_type: str = "hnsw"
    distance_metric: str = "cosine"
    ef_construction: int = 128
    m: int = 16


class CurationConfig(BaseModel):
    """经验提炼配置"""
    enabled: bool = True
    min_experiences_for_curation: int = 3
    auto_curate: bool = False
    llm_model: str = "gpt-4o-mini"


class ExperienceHubSettings(BaseSettings):
    """
    Experience Hub 配置

    环境变量:
    - EXPERIENCE_HUB_EMBEDDING_ENABLED: 是否启用向量化
    - EXPERIENCE_HUB_AUTO_CURATE: 是否自动提炼
    """

    model_config = SettingsConfigDict(
        env_prefix="EXPERIENCE_HUB_",
        extra="ignore",
    )

    # 默认配置
    default_confidence: float = 0.5
    confidence_delta_on_validate: float = 0.1
    max_confidence: float = 1.0
    min_confidence: float = 0.0

    # 向量化配置
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)

    # 向量存储配置
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)

    # 提炼配置
    curation: CurationConfig = Field(default_factory=CurationConfig)

    # 经验层级配置
    level_order: List[str] = Field(
        default_factory=lambda: ["operational", "tactical", "strategic"]
    )

    @classmethod
    def from_yaml(cls, yaml_path: Optional[Path] = None) -> "ExperienceHubSettings":
        """
        从 YAML 文件加载配置

        Args:
            yaml_path: YAML 配置文件路径，None 则使用默认路径
        """
        if yaml_path is None:
            # 默认路径: 项目根目录/config/experience_hub.yaml
            current = Path(__file__).resolve()
            # backend/domains/experience_hub/core/config.py -> 项目根目录
            project_root = current.parent.parent.parent.parent.parent
            yaml_path = project_root / "config" / "experience_hub.yaml"

        if not yaml_path.exists():
            return cls()

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # 解析配置
        embedding_data = data.get("embedding", {})
        embedding = EmbeddingConfig(**embedding_data)

        vector_store_data = data.get("vector_store", {})
        vector_store = VectorStoreConfig(**vector_store_data)

        curation_data = data.get("curation", {})
        curation = CurationConfig(**curation_data)

        return cls(
            default_confidence=data.get("default_confidence", 0.5),
            confidence_delta_on_validate=data.get("confidence_delta_on_validate", 0.1),
            max_confidence=data.get("max_confidence", 1.0),
            min_confidence=data.get("min_confidence", 0.0),
            embedding=embedding,
            vector_store=vector_store,
            curation=curation,
            level_order=data.get("level_order", ["operational", "tactical", "strategic"]),
        )

    def can_curate_to_level(self, from_level: str, to_level: str) -> bool:
        """
        检查是否可以从一个层级提炼到另一个层级

        只能从低层级提炼到高层级。
        """
        try:
            from_idx = self.level_order.index(from_level)
            to_idx = self.level_order.index(to_level)
            return to_idx > from_idx
        except ValueError:
            return False


# ============================================
# 全局配置管理
# ============================================

_settings: Optional[ExperienceHubSettings] = None


def get_experience_hub_settings(
    yaml_path: Optional[Path] = None
) -> ExperienceHubSettings:
    """
    获取 Experience Hub 配置单例

    首次调用时从 YAML 加载配置，后续调用返回缓存的实例。
    """
    global _settings
    if _settings is None:
        _settings = ExperienceHubSettings.from_yaml(yaml_path)
    return _settings


def reload_settings(yaml_path: Optional[Path] = None) -> ExperienceHubSettings:
    """
    重新加载配置

    清除缓存并重新加载。
    """
    global _settings
    _settings = ExperienceHubSettings.from_yaml(yaml_path)
    return _settings
