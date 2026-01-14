"""
RAG 组件基础抽象

所有 RAG 组件都继承自这里的基类，通过注册表模式实现可插拔。
"""

from .component import BaseComponent, ComponentConfig, ComponentResult
from .registry import ComponentRegistry, component_registries
from .parser import BaseParser, ParsedDocument, ParsedPage, ContentType
from .chunker import BaseChunker, Chunk, ChunkMetadata
from .reranker import RerankResult
from .embedder import BaseEmbedder, EmbeddingResult
from .vector_store import BaseVectorStore, SearchResult
from .retriever import BaseRetriever, RetrievalResult
from .reranker import BaseReranker
from .generator import BaseGenerator, GenerationResult
from .pipeline import BasePipeline, PipelineResult, PipelineContext

__all__ = [
    # 基础组件
    "BaseComponent",
    "ComponentConfig",
    "ComponentResult",
    "ComponentRegistry",
    "component_registries",
    # 具体组件
    "BaseParser",
    "ParsedDocument",
    "ParsedPage",
    "ContentType",
    "BaseChunker",
    "Chunk",
    "ChunkMetadata",
    "BaseEmbedder",
    "EmbeddingResult",
    "BaseVectorStore",
    "SearchResult",
    "BaseRetriever",
    "RetrievalResult",
    "BaseReranker",
    "RerankResult",
    "BaseGenerator",
    "GenerationResult",
    "BasePipeline",
    "PipelineResult",
    "PipelineContext",
]
