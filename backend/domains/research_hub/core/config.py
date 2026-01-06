"""
Research Hub 配置管理

从 config/research_hub.yaml 加载配置，支持:
- 多流水线配置
- 组件配置热加载
- 配置驱动的流水线组装
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ============================================
# 组件配置模型
# ============================================


class ParserConfig(BaseModel):
    """解析器配置"""
    type: str = "mineru"
    version: str = "2.5"
    options: Dict[str, Any] = Field(default_factory=dict)


class ChunkerConfig(BaseModel):
    """切块器配置"""
    type: str = "recursive"
    chunk_size: int = 512
    chunk_overlap: int = 50
    separators: List[str] = Field(
        default_factory=lambda: ["\n\n", "\n", "。", ".", " "]
    )
    options: Dict[str, Any] = Field(default_factory=dict)


class EmbedderConfig(BaseModel):
    """嵌入器配置"""
    type: str = "bge_m3"
    model: str = "BAAI/bge-m3"
    dimensions: int = 1024
    batch_size: int = 32
    options: Dict[str, Any] = Field(default_factory=dict)


class VectorStoreConfig(BaseModel):
    """向量存储配置"""
    type: str = "pgvector"
    collection_name: str = "research_chunks"
    index_type: str = "hnsw"
    distance_metric: str = "cosine"
    options: Dict[str, Any] = Field(default_factory=dict)


class RetrieverConfig(BaseModel):
    """检索器配置"""
    type: str = "hybrid"
    top_k: int = 20
    options: Dict[str, Any] = Field(default_factory=dict)


class RerankerConfig(BaseModel):
    """重排器配置"""
    type: str = "bge_reranker"
    model: str = "BAAI/bge-reranker-v2-m3"
    top_k: int = 5
    options: Dict[str, Any] = Field(default_factory=dict)


class GeneratorConfig(BaseModel):
    """生成器配置"""
    type: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 4096
    options: Dict[str, Any] = Field(default_factory=dict)


class PipelineConfig(BaseModel):
    """流水线配置"""
    name: str = "default"
    description: str = ""

    # 组件配置
    parser: ParserConfig = Field(default_factory=ParserConfig)
    chunker: ChunkerConfig = Field(default_factory=ChunkerConfig)
    embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    retriever: RetrieverConfig = Field(default_factory=RetrieverConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)
    generator: GeneratorConfig = Field(default_factory=GeneratorConfig)

    # 流水线级别配置
    enable_query_rewrite: bool = False
    enable_rerank: bool = True
    max_context_length: int = 8000

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineConfig":
        """从字典创建"""
        return cls(**data)


class EvaluationConfig(BaseModel):
    """评估配置"""
    enabled: bool = True
    metrics: List[str] = Field(
        default_factory=lambda: [
            "recall_at_k",
            "precision_at_k",
            "ndcg",
            "mrr",
            "faithfulness",
            "answer_relevance",
        ]
    )
    save_results: bool = True


# ============================================
# 主配置类
# ============================================


class ResearchHubSettings(BaseSettings):
    """
    Research Hub 配置

    环境变量:
    - RESEARCH_HUB_PIPELINE: 默认流水线名称
    - RESEARCH_HUB_UPLOAD_DIR: 上传目录
    """

    model_config = SettingsConfigDict(
        env_prefix="RESEARCH_HUB_",
        extra="ignore",
    )

    # 默认配置
    default_pipeline: str = "default"
    upload_dir: str = "data/research"
    max_file_size_mb: int = 100

    # 流水线配置
    pipelines: Dict[str, PipelineConfig] = Field(default_factory=dict)

    # 组件别名
    component_aliases: Dict[str, Dict[str, str]] = Field(default_factory=dict)

    # 评估配置
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)

    @classmethod
    def from_yaml(cls, yaml_path: Optional[Path] = None) -> "ResearchHubSettings":
        """
        从 YAML 文件加载配置

        Args:
            yaml_path: YAML 配置文件路径，None 则使用默认路径
        """
        if yaml_path is None:
            # 默认路径: 项目根目录/config/research_hub.yaml
            current = Path(__file__).resolve()
            # backend/domains/research_hub/core/config.py -> 项目根目录
            project_root = current.parent.parent.parent.parent.parent
            yaml_path = project_root / "config" / "research_hub.yaml"

        if not yaml_path.exists():
            return cls()

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # 解析默认配置
        default = data.get("default", {})

        # 解析流水线配置
        pipelines_data = data.get("pipelines", {})
        pipelines = {}
        for name, config in pipelines_data.items():
            # 解析各组件配置
            pipeline_config = PipelineConfig(
                name=config.get("name", name),
                description=config.get("description", ""),
                parser=ParserConfig(**config.get("parser", {})),
                chunker=ChunkerConfig(**config.get("chunker", {})),
                embedder=EmbedderConfig(**config.get("embedder", {})),
                vector_store=VectorStoreConfig(**config.get("vector_store", {})),
                retriever=RetrieverConfig(**config.get("retriever", {})),
                reranker=RerankerConfig(**config.get("reranker", {})),
                generator=GeneratorConfig(**config.get("generator", {})),
                enable_query_rewrite=config.get("enable_query_rewrite", False),
                enable_rerank=config.get("enable_rerank", True),
                max_context_length=config.get("max_context_length", 8000),
            )
            pipelines[name] = pipeline_config

        # 解析评估配置
        eval_data = data.get("evaluation", {})
        evaluation = EvaluationConfig(**eval_data)

        return cls(
            default_pipeline=default.get("pipeline", "default"),
            upload_dir=default.get("upload_dir", "data/research"),
            max_file_size_mb=default.get("max_file_size_mb", 100),
            pipelines=pipelines,
            component_aliases=data.get("component_aliases", {}),
            evaluation=evaluation,
        )

    def get_pipeline_config(
        self, pipeline_name: Optional[str] = None
    ) -> PipelineConfig:
        """
        获取流水线配置

        Args:
            pipeline_name: 流水线名称，None 则使用默认

        Returns:
            PipelineConfig 实例
        """
        name = pipeline_name or self.default_pipeline
        if name not in self.pipelines:
            # 返回默认配置
            return PipelineConfig(name=name)
        return self.pipelines[name]

    def list_pipelines(self) -> List[str]:
        """列出所有可用的流水线"""
        return list(self.pipelines.keys())

    def resolve_component_type(
        self, component: str, type_alias: str
    ) -> str:
        """
        解析组件类型别名

        Args:
            component: 组件类型 (parser, embedder, etc.)
            type_alias: 类型别名

        Returns:
            实际的类型名称
        """
        aliases = self.component_aliases.get(component, {})
        return aliases.get(type_alias, type_alias)


# ============================================
# 全局配置管理
# ============================================

_settings: Optional[ResearchHubSettings] = None


def get_research_hub_settings(
    yaml_path: Optional[Path] = None
) -> ResearchHubSettings:
    """
    获取 Research Hub 配置单例

    首次调用时从 YAML 加载配置，后续调用返回缓存的实例。
    """
    global _settings
    if _settings is None:
        _settings = ResearchHubSettings.from_yaml(yaml_path)
    return _settings


def reload_settings(yaml_path: Optional[Path] = None) -> ResearchHubSettings:
    """
    重新加载配置

    清除缓存并重新加载。
    """
    global _settings
    _settings = ResearchHubSettings.from_yaml(yaml_path)
    return _settings


def get_pipeline_config(pipeline_name: Optional[str] = None) -> PipelineConfig:
    """
    获取流水线配置的便捷函数

    Args:
        pipeline_name: 流水线名称，None 则使用默认

    Returns:
        PipelineConfig 实例
    """
    settings = get_research_hub_settings()
    return settings.get_pipeline_config(pipeline_name)
