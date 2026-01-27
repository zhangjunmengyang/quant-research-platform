"""
Research Hub 配置管理

从 config/research_hub.yaml 加载配置。
简化版本，只保留必要的配置项。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ParserConfig(BaseModel):
    """解析器配置"""
    type: str = "basic"


class ChunkerConfig(BaseModel):
    """切块器配置"""
    type: str = "recursive"
    chunk_size: int = 512
    chunk_overlap: int = 50


class EmbedderConfig(BaseModel):
    """嵌入器配置"""
    type: str = "openai"
    model: str = "text-embedding-3-small"
    dimensions: int = 512


class VectorStoreConfig(BaseModel):
    """向量存储配置"""
    type: str = "pgvector"
    collection_name: str = "research_chunks"
    index_type: str = "hnsw"


class RetrieverConfig(BaseModel):
    """检索器配置"""
    type: str = "dense"
    top_k: int = 20


class PipelineConfig(BaseModel):
    """流水线配置"""
    name: str = "default"
    description: str = ""

    parser: ParserConfig = Field(default_factory=ParserConfig)
    chunker: ChunkerConfig = Field(default_factory=ChunkerConfig)
    embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    retriever: RetrieverConfig = Field(default_factory=RetrieverConfig)

    enable_query_rewrite: bool = False
    enable_rerank: bool = False
    max_context_length: int = 8000


class ResearchHubSettings(BaseSettings):
    """Research Hub 配置"""

    model_config = SettingsConfigDict(
        env_prefix="RESEARCH_HUB_",
        extra="ignore",
    )

    default_pipeline: str = "default"
    upload_dir: str = "private/research"
    max_file_size_mb: int = 100
    pipelines: Dict[str, PipelineConfig] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, yaml_path: Optional[Path] = None) -> "ResearchHubSettings":
        """从 YAML 文件加载配置"""
        if yaml_path is None:
            current = Path(__file__).resolve()
            project_root = current.parent.parent.parent.parent.parent
            yaml_path = project_root / "config" / "research_hub.yaml"

        if not yaml_path.exists():
            return cls()

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        default = data.get("default", {})
        pipelines_data = data.get("pipelines", {})
        pipelines = {}

        for name, config in pipelines_data.items():
            pipeline_config = PipelineConfig(
                name=config.get("name", name),
                description=config.get("description", ""),
                parser=ParserConfig(**config.get("parser", {})),
                chunker=ChunkerConfig(**config.get("chunker", {})),
                embedder=EmbedderConfig(**config.get("embedder", {})),
                vector_store=VectorStoreConfig(**config.get("vector_store", {})),
                retriever=RetrieverConfig(**config.get("retriever", {})),
                enable_query_rewrite=config.get("enable_query_rewrite", False),
                enable_rerank=config.get("enable_rerank", False),
                max_context_length=config.get("max_context_length", 8000),
            )
            pipelines[name] = pipeline_config

        return cls(
            default_pipeline=default.get("pipeline", "default"),
            upload_dir=default.get("upload_dir", "private/research"),
            max_file_size_mb=default.get("max_file_size_mb", 100),
            pipelines=pipelines,
        )

    def get_pipeline_config(self, pipeline_name: Optional[str] = None) -> PipelineConfig:
        """获取流水线配置"""
        name = pipeline_name or self.default_pipeline
        if name not in self.pipelines:
            return PipelineConfig(name=name)
        return self.pipelines[name]

    def list_pipelines(self) -> List[str]:
        """列出所有可用的流水线"""
        return list(self.pipelines.keys())


_settings: Optional[ResearchHubSettings] = None


def get_research_hub_settings(yaml_path: Optional[Path] = None) -> ResearchHubSettings:
    """获取 Research Hub 配置单例"""
    global _settings
    if _settings is None:
        _settings = ResearchHubSettings.from_yaml(yaml_path)
    return _settings


def get_pipeline_config(pipeline_name: Optional[str] = None) -> PipelineConfig:
    """获取流水线配置的便捷函数"""
    settings = get_research_hub_settings()
    return settings.get_pipeline_config(pipeline_name)
