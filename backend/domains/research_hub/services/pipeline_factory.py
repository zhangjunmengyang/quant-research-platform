"""
RAG 流水线工厂

根据配置创建完整的 RAG 流水线实例。
"""

import logging
from typing import Optional

from ..core.config import (
    get_pipeline_config,
    PipelineConfig,
)
from ..rag.base.pipeline import BasePipeline
from ..rag.base.retriever import BaseRetriever
from ..rag.base.reranker import BaseReranker
from ..rag.base.generator import BaseGenerator
from ..rag.base.embedder import BaseEmbedder
from ..rag.base.vector_store import BaseVectorStore
from ..rag.base.registry import component_registries

logger = logging.getLogger(__name__)


class PipelineFactory:
    """
    RAG 流水线工厂

    根据配置创建完整的 RAG 流水线，包括:
    - Embedder
    - VectorStore
    - Retriever
    - Reranker
    - Generator
    - Pipeline

    使用示例:
        factory = PipelineFactory()
        pipeline = await factory.create_pipeline("default")
        result = await pipeline.run("什么是动量因子？")
    """

    def __init__(self):
        self._pipelines: dict = {}

    async def create_pipeline(
        self,
        pipeline_name: Optional[str] = None,
        config: Optional[PipelineConfig] = None,
    ) -> BasePipeline:
        """
        创建流水线实例

        Args:
            pipeline_name: 流水线名称（从 config/research_hub.yaml 加载）
            config: 直接传入的配置（优先级高于 pipeline_name）

        Returns:
            配置好的流水线实例
        """
        # 获取配置
        if config is None:
            config = get_pipeline_config(pipeline_name)

        logger.info(f"Creating pipeline: {config.name}")

        # 创建各组件
        embedder = await self._create_embedder(config)
        vector_store = await self._create_vector_store(config)
        retriever = await self._create_retriever(config, embedder, vector_store)
        reranker = await self._create_reranker(config) if config.enable_rerank else None
        generator = await self._create_generator(config)

        # 创建流水线
        pipeline_type = config.name if config.name in ["default", "fast", "quality"] else "default"
        pipeline_cls = component_registries.pipeline.get(pipeline_type)

        pipeline = pipeline_cls(
            retriever=retriever,
            reranker=reranker,
            generator=generator,
            embedder=embedder,
            vector_store=vector_store,
            retrieval_top_k=config.retriever.top_k,
            rerank_top_k=config.reranker.top_k,
            enable_rerank=config.enable_rerank,
            enable_query_rewrite=config.enable_query_rewrite,
            max_context_length=config.max_context_length,
        )

        await pipeline.setup()
        logger.info(f"Pipeline {config.name} created successfully")

        return pipeline

    async def _create_embedder(self, config: PipelineConfig) -> BaseEmbedder:
        """创建嵌入器"""
        embedder_config = config.embedder
        embedder_cls = component_registries.embedder.get(embedder_config.type)

        embedder = embedder_cls(
            model_name=embedder_config.model,
            dimensions=embedder_config.dimensions,
            batch_size=embedder_config.batch_size,
            **embedder_config.options,
        )

        await embedder.setup()
        logger.info(f"Created embedder: {embedder_config.type}")
        return embedder

    async def _create_vector_store(self, config: PipelineConfig) -> BaseVectorStore:
        """创建向量存储"""
        vs_config = config.vector_store
        vs_cls = component_registries.vector_store.get(vs_config.type)

        vector_store = vs_cls(
            collection_name=vs_config.collection_name,
            dimensions=config.embedder.dimensions,
            index_type=vs_config.index_type,
            distance_metric=vs_config.distance_metric,
            **vs_config.options,
        )

        await vector_store.setup()
        logger.info(f"Created vector store: {vs_config.type}")
        return vector_store

    async def _create_retriever(
        self,
        config: PipelineConfig,
        embedder: BaseEmbedder,
        vector_store: BaseVectorStore,
    ) -> BaseRetriever:
        """创建检索器"""
        retriever_config = config.retriever
        retriever_cls = component_registries.retriever.get(retriever_config.type)

        retriever = retriever_cls(
            embedder=embedder,
            vector_store=vector_store,
            top_k=retriever_config.top_k,
            **retriever_config.options,
        )

        logger.info(f"Created retriever: {retriever_config.type}")
        return retriever

    async def _create_reranker(self, config: PipelineConfig) -> Optional[BaseReranker]:
        """创建重排器"""
        reranker_config = config.reranker
        if reranker_config.type == "none":
            return None

        reranker_cls = component_registries.reranker.get(reranker_config.type)

        reranker = reranker_cls(
            model=reranker_config.model,
            top_k=reranker_config.top_k,
            **reranker_config.options,
        )

        await reranker.setup()
        logger.info(f"Created reranker: {reranker_config.type}")
        return reranker

    async def _create_generator(self, config: PipelineConfig) -> BaseGenerator:
        """创建生成器"""
        gen_config = config.generator
        gen_cls = component_registries.generator.get(gen_config.type)

        generator = gen_cls(
            model=gen_config.model,
            temperature=gen_config.temperature,
            max_tokens=gen_config.max_tokens,
            **gen_config.options,
        )

        await generator.setup()
        logger.info(f"Created generator: {gen_config.type}")
        return generator

    async def get_or_create_pipeline(
        self,
        pipeline_name: Optional[str] = None,
    ) -> BasePipeline:
        """
        获取或创建流水线（缓存）

        Args:
            pipeline_name: 流水线名称，None 则使用配置的默认流水线

        Returns:
            流水线实例（可能是缓存的）
        """
        from ..core.config import get_research_hub_settings
        settings = get_research_hub_settings()
        name = pipeline_name or settings.default_pipeline
        if name not in self._pipelines:
            self._pipelines[name] = await self.create_pipeline(name)
        return self._pipelines[name]

    async def clear_cache(self) -> None:
        """清除流水线缓存"""
        for pipeline in self._pipelines.values():
            await pipeline.teardown()
        self._pipelines.clear()


# 全局工厂实例
_factory: Optional[PipelineFactory] = None


def get_pipeline_factory() -> PipelineFactory:
    """获取流水线工厂单例"""
    global _factory
    if _factory is None:
        _factory = PipelineFactory()
    return _factory
