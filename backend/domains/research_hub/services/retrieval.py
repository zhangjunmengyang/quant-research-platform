"""
研报检索服务

提供语义检索和 RAG 问答功能。
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..core.store import get_research_store, get_chunk_store, ResearchStore, ChunkStore
from ..core.config import get_pipeline_config
from ..rag.base.registry import component_registries
from ..rag.base.retriever import RetrievalResult
from ..rag.base.embedder import BaseEmbedder
from ..rag.base.vector_store import BaseVectorStore

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    研报检索服务

    功能:
    - 语义检索：根据查询文本检索相关研报片段
    - RAG 问答：检索 + 生成回答

    使用示例:
        service = RetrievalService()

        # 语义检索
        results = await service.search("什么是动量因子")

        # RAG 问答
        answer = await service.ask("动量因子的计算公式是什么？")
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        pipeline_name: Optional[str] = None,
    ):
        self.database_url = database_url
        self.pipeline_name = pipeline_name

        self._research_store: Optional[ResearchStore] = None
        self._chunk_store: Optional[ChunkStore] = None
        self._embedder: Optional[BaseEmbedder] = None
        self._vector_store: Optional[BaseVectorStore] = None
        self._pipeline = None

    @property
    def research_store(self) -> ResearchStore:
        if self._research_store is None:
            self._research_store = get_research_store(self.database_url)
        return self._research_store

    @property
    def chunk_store(self) -> ChunkStore:
        if self._chunk_store is None:
            self._chunk_store = get_chunk_store(self.database_url)
        return self._chunk_store

    async def _ensure_embedder(self) -> BaseEmbedder:
        """确保嵌入器已初始化"""
        if self._embedder is None:
            config = get_pipeline_config(self.pipeline_name)
            embedder_cls = component_registries.embedder.get(config.embedder.type)
            self._embedder = embedder_cls(
                model_name=config.embedder.model,
                dimensions=config.embedder.dimensions,
                batch_size=config.embedder.batch_size,
                **config.embedder.options,
            )
            await self._embedder.setup()
        return self._embedder

    async def _ensure_vector_store(self) -> BaseVectorStore:
        """确保向量存储已初始化"""
        if self._vector_store is None:
            config = get_pipeline_config(self.pipeline_name)
            vs_cls = component_registries.vector_store.get(config.vector_store.type)
            self._vector_store = vs_cls(
                collection_name=config.vector_store.collection_name,
                dimensions=config.embedder.dimensions,
                index_type=config.vector_store.index_type,
                distance_metric=config.vector_store.distance_metric,
                **config.vector_store.options,
            )
            await self._vector_store.setup()
        return self._vector_store

    async def search(
        self,
        query: str,
        top_k: int = 10,
        report_id: Optional[int] = None,
        report_uuid: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        语义检索研报内容

        Args:
            query: 查询文本
            top_k: 返回数量
            report_id: 限定搜索的研报 ID（可选）
            report_uuid: 限定搜索的研报 UUID（可选）
            min_score: 最小相似度分数

        Returns:
            检索结果列表，每个结果包含:
            - chunk_id: 切块 ID
            - content: 切块内容
            - score: 相似度分数
            - report_id: 研报 ID
            - report_uuid: 研报 UUID
            - report_title: 研报标题
            - page_start: 起始页
            - section_title: 章节标题
        """
        embedder = await self._ensure_embedder()
        vector_store = await self._ensure_vector_store()

        # 生成查询向量
        query_embedding = await embedder.embed_query(query)

        # 构建过滤条件
        filter_conditions = {}
        if report_id:
            filter_conditions["report_id"] = report_id
        if report_uuid:
            filter_conditions["report_uuid"] = report_uuid

        # 向量搜索
        search_results = await vector_store.search(
            query_vector=query_embedding.dense,
            top_k=top_k,
            filter_conditions=filter_conditions if filter_conditions else None,
        )

        # 获取研报信息用于丰富结果
        report_cache = {}

        results = []
        for sr in search_results:
            if sr.score < min_score:
                continue

            # 获取研报标题
            doc_id = sr.document_id
            if doc_id not in report_cache:
                report = self.research_store.get_by_uuid(doc_id)
                report_cache[doc_id] = report

            report = report_cache.get(doc_id)
            report_title = report.title if report else ""
            report_id_val = report.id if report else None

            results.append({
                "chunk_id": sr.chunk_id,
                "content": sr.content,
                "score": sr.score,
                "report_id": report_id_val,
                "report_uuid": doc_id,
                "report_title": report_title,
                "page_start": sr.chunk.metadata.page_start if sr.chunk.metadata else None,
                "section_title": sr.chunk.metadata.section_title if sr.chunk.metadata else "",
            })

        logger.info(f"语义检索完成: query='{query[:50]}...', 返回 {len(results)} 条结果")
        return results

    async def ask(
        self,
        question: str,
        top_k: int = 5,
        report_id: Optional[int] = None,
        report_uuid: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        RAG 问答

        Args:
            question: 用户问题
            top_k: 检索的切块数量
            report_id: 限定的研报 ID
            report_uuid: 限定的研报 UUID
            conversation_history: 对话历史

        Returns:
            问答结果:
            - answer: 回答内容
            - sources: 来源引用列表
            - retrieved_chunks: 检索到的切块数量
        """
        from .pipeline_factory import get_pipeline_factory

        factory = get_pipeline_factory()
        pipeline = await factory.get_or_create_pipeline(self.pipeline_name)

        # 构建过滤条件
        filter_conditions = {}
        if report_id:
            filter_conditions["report_id"] = report_id
        if report_uuid:
            filter_conditions["report_uuid"] = report_uuid

        # 执行 RAG 流水线
        result = await pipeline.run(
            query=question,
            conversation_history=conversation_history,
            filter_conditions=filter_conditions if filter_conditions else None,
        )

        # 构建来源引用
        sources = []
        if result.generation and result.generation.sources:
            for src in result.generation.sources:
                # 获取研报标题
                report = None
                if src.document_id:
                    report = self.research_store.get_by_uuid(src.document_id)

                sources.append({
                    "chunk_id": src.chunk_id,
                    "content": src.content,
                    "page_number": src.page_number,
                    "relevance": src.relevance,
                    "report_uuid": src.document_id,
                    "report_title": report.title if report else "",
                })

        return {
            "answer": result.answer or "",
            "sources": sources,
            "retrieved_chunks": result.retrieved_chunks,
            "total_time": result.total_time,
        }

    async def get_similar_chunks(
        self,
        chunk_id: str,
        top_k: int = 5,
        exclude_same_report: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        获取相似的切块

        Args:
            chunk_id: 参考切块 ID
            top_k: 返回数量
            exclude_same_report: 是否排除同一研报的切块

        Returns:
            相似切块列表
        """
        vector_store = await self._ensure_vector_store()

        # 获取参考切块
        ref_chunk = await vector_store.get_by_id(chunk_id)
        if ref_chunk is None:
            return []

        # 获取切块的向量
        # 由于切块可能没有存储向量，需要重新生成
        embedder = await self._ensure_embedder()
        query_embedding = await embedder.embed_query(ref_chunk.content)

        # 搜索相似切块
        filter_conditions = {}
        if exclude_same_report and ref_chunk.metadata:
            # 注意: 这里需要排除同一研报，但 pgvector 不支持 NOT IN
            # 简化处理：返回时过滤
            pass

        search_results = await vector_store.search(
            query_vector=query_embedding.dense,
            top_k=top_k + 10,  # 多取一些，用于过滤
            filter_conditions=filter_conditions if filter_conditions else None,
        )

        results = []
        ref_doc_id = ref_chunk.metadata.document_id if ref_chunk.metadata else None

        for sr in search_results:
            # 排除自身
            if sr.chunk_id == chunk_id:
                continue

            # 排除同一研报
            if exclude_same_report and sr.document_id == ref_doc_id:
                continue

            # 获取研报标题
            report = self.research_store.get_by_uuid(sr.document_id) if sr.document_id else None

            results.append({
                "chunk_id": sr.chunk_id,
                "content": sr.content,
                "score": sr.score,
                "report_uuid": sr.document_id,
                "report_title": report.title if report else "",
            })

            if len(results) >= top_k:
                break

        return results


# 单例管理
_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service(
    database_url: Optional[str] = None,
    pipeline_name: Optional[str] = None,
) -> RetrievalService:
    """获取检索服务单例"""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService(
            database_url=database_url,
            pipeline_name=pipeline_name,
        )
    return _retrieval_service
