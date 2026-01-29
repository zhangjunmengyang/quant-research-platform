"""
Experience Hub 配置管理
"""

from pathlib import Path

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


class ExperienceHubSettings(BaseSettings):
    """Experience Hub 配置"""

    model_config = SettingsConfigDict(
        env_prefix="EXPERIENCE_HUB_",
        extra="ignore",
    )

    # 向量化配置
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)

    # 向量存储配置
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)

    @classmethod
    def from_yaml(cls, yaml_path: Path | None = None) -> "ExperienceHubSettings":
        """从 YAML 文件加载配置"""
        if yaml_path is None:
            current = Path(__file__).resolve()
            project_root = current.parent.parent.parent.parent.parent
            yaml_path = project_root / "config" / "experience_hub.yaml"

        if not yaml_path.exists():
            return cls()

        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        embedding_data = data.get("embedding", {})
        embedding = EmbeddingConfig(**embedding_data)

        vector_store_data = data.get("vector_store", {})
        vector_store = VectorStoreConfig(**vector_store_data)

        return cls(
            embedding=embedding,
            vector_store=vector_store,
        )


_settings: ExperienceHubSettings | None = None


def get_experience_hub_settings(
    yaml_path: Path | None = None
) -> ExperienceHubSettings:
    """获取 Experience Hub 配置单例"""
    global _settings
    if _settings is None:
        _settings = ExperienceHubSettings.from_yaml(yaml_path)
    return _settings


def reload_settings(yaml_path: Path | None = None) -> ExperienceHubSettings:
    """重新加载配置"""
    global _settings
    _settings = ExperienceHubSettings.from_yaml(yaml_path)
    return _settings
