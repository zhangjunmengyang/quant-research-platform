"""
检索器实现

提供稠密检索和混合检索策略。
"""

import logging
from typing import Any, Dict, List, Optional

from ..base.retriever import BaseRetriever, RetrievalResult
from ..base.embedder import BaseEmbedder
from ..base.vector_store import BaseVectorStore
from ..base.registry import component_registries

logger = logging.getLogger(__name__)


@component_registries.retriever.register("dense")
class DenseRetriever(BaseRetriever):
    """
    稠密向量检索器

    使用嵌入模型将查询转换为向量，然后在向量库中搜索。

    使用示例:
        retriever = DenseRetriever(
            embedder=bge_m3_embedder,
            vector_store=pgvector_store,
            top_k=20,
        )
        results = await retriever.retrieve("什么是动量因子？")
    """

    def __init__(
        self,
        embedder: Optional[BaseEmbedder] = None,
        vector_store: Optional[BaseVectorStore] = None,
        top_k: int = 20,
        **kwargs,
    ):
        super().__init__(top_k=top_k, **kwargs)
        self.embedder = embedder
        self.vector_store = vector_store

    def set_embedder(self, embedder: BaseEmbedder) -> None:
        """设置嵌入器"""
        self.embedder = embedder

    def set_vector_store(self, vector_store: BaseVectorStore) -> None:
        """设置向量存储"""
        self.vector_store = vector_store

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        检索相关文档

        Args:
            query: 查询文本
            top_k: 返回数量
            filter_conditions: 过滤条件

        Returns:
            检索结果列表
        """
        if self.embedder is None:
            raise ValueError("Embedder not set. Call set_embedder() first.")
        if self.vector_store is None:
            raise ValueError("Vector store not set. Call set_vector_store() first.")

        k = top_k or self.config.top_k

        # 生成查询向量
        query_embedding = await self.embedder.embed_query(query)

        # 在向量库中搜索
        search_results = await self.vector_store.search(
            query_vector=query_embedding.dense,
            top_k=k,
            filter_conditions=filter_conditions,
        )

        # 转换为 RetrievalResult
        results = []
        for sr in search_results:
            results.append(
                RetrievalResult(
                    content=sr.content,
                    score=sr.score,
                    document_id=sr.document_id,
                    chunk_id=sr.chunk_id,
                    page_number=sr.chunk.metadata.page_start if sr.chunk.metadata else None,
                    metadata={
                        "distance": sr.distance,
                        "retrieval_method": "dense",
                    },
                    raw_result=sr,
                )
            )

        logger.info(f"Dense retrieval returned {len(results)} results for query: {query[:50]}...")
        return results


@component_registries.retriever.register("hybrid")
class HybridRetriever(BaseRetriever):
    """
    混合检索器

    结合稠密向量检索和稀疏检索（BM25/全文搜索），
    使用 RRF (Reciprocal Rank Fusion) 融合结果。

    使用示例:
        retriever = HybridRetriever(
            embedder=bge_m3_embedder,
            vector_store=pgvector_store,
            top_k=20,
            dense_weight=0.7,
            sparse_weight=0.3,
        )
        results = await retriever.retrieve("动量因子的计算公式")
    """

    def __init__(
        self,
        embedder: Optional[BaseEmbedder] = None,
        vector_store: Optional[BaseVectorStore] = None,
        top_k: int = 20,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        enable_query_expansion: bool = False,
        rrf_k: int = 60,
        **kwargs,
    ):
        super().__init__(top_k=top_k, **kwargs)
        self.embedder = embedder
        self.vector_store = vector_store
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.enable_query_expansion = enable_query_expansion
        self.rrf_k = rrf_k

    def set_embedder(self, embedder: BaseEmbedder) -> None:
        """设置嵌入器"""
        self.embedder = embedder

    def set_vector_store(self, vector_store: BaseVectorStore) -> None:
        """设置向量存储"""
        self.vector_store = vector_store

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        混合检索

        Args:
            query: 查询文本
            top_k: 返回数量
            filter_conditions: 过滤条件

        Returns:
            融合后的检索结果
        """
        if self.embedder is None:
            raise ValueError("Embedder not set")
        if self.vector_store is None:
            raise ValueError("Vector store not set")

        k = top_k or self.config.top_k

        # 生成查询嵌入
        query_embedding = await self.embedder.embed_query(query)

        # 混合搜索
        search_results = await self.vector_store.search_hybrid(
            query_vector=query_embedding.dense,
            sparse_vector=query_embedding.sparse,
            top_k=k,
            dense_weight=self.dense_weight,
            sparse_weight=self.sparse_weight,
            filter_conditions=filter_conditions,
        )

        # 转换结果
        results = []
        for sr in search_results:
            results.append(
                RetrievalResult(
                    content=sr.content,
                    score=sr.score,
                    document_id=sr.document_id,
                    chunk_id=sr.chunk_id,
                    page_number=sr.chunk.metadata.page_start if sr.chunk.metadata else None,
                    metadata={
                        "distance": sr.distance,
                        "retrieval_method": "hybrid",
                        "dense_weight": self.dense_weight,
                        "sparse_weight": self.sparse_weight,
                    },
                    raw_result=sr,
                )
            )

        logger.info(f"Hybrid retrieval returned {len(results)} results")
        return results

    def _rrf_fusion(
        self,
        dense_results: List[RetrievalResult],
        sparse_results: List[RetrievalResult],
        top_k: int,
    ) -> List[RetrievalResult]:
        """
        RRF (Reciprocal Rank Fusion) 融合

        公式: RRF(d) = sum(1 / (k + r(d)))
        其中 k 是常数（默认 60），r(d) 是文档在各个列表中的排名
        """
        scores = {}
        chunk_map = {}

        # 处理稠密检索结果
        for rank, result in enumerate(dense_results):
            cid = result.chunk_id
            rrf_score = self.dense_weight / (self.rrf_k + rank + 1)
            scores[cid] = scores.get(cid, 0) + rrf_score
            chunk_map[cid] = result

        # 处理稀疏检索结果
        for rank, result in enumerate(sparse_results):
            cid = result.chunk_id
            rrf_score = self.sparse_weight / (self.rrf_k + rank + 1)
            scores[cid] = scores.get(cid, 0) + rrf_score
            if cid not in chunk_map:
                chunk_map[cid] = result

        # 按 RRF 分数排序
        sorted_chunks = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # 构建结果
        results = []
        for cid, rrf_score in sorted_chunks[:top_k]:
            original = chunk_map[cid]
            results.append(
                RetrievalResult(
                    content=original.content,
                    score=rrf_score,
                    document_id=original.document_id,
                    chunk_id=original.chunk_id,
                    page_number=original.page_number,
                    metadata={
                        **original.metadata,
                        "rrf_score": rrf_score,
                        "retrieval_method": "hybrid_rrf",
                    },
                    raw_result=original.raw_result,
                )
            )

        return results


@component_registries.retriever.register("multi_query")
class MultiQueryRetriever(BaseRetriever):
    """
    多查询检索器

    通过 LLM 生成多个查询变体，扩展检索范围。
    适合复杂或模糊的查询。

    流程:
    1. 使用 LLM 生成 N 个查询变体
    2. 对每个变体进行检索
    3. 融合去重结果
    """

    def __init__(
        self,
        base_retriever: Optional[BaseRetriever] = None,
        llm_client: Optional[Any] = None,
        num_queries: int = 3,
        top_k: int = 20,
        **kwargs,
    ):
        super().__init__(top_k=top_k, **kwargs)
        self.base_retriever = base_retriever
        self.llm_client = llm_client
        self.num_queries = num_queries

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        多查询检索

        Args:
            query: 原始查询
            top_k: 返回数量
            filter_conditions: 过滤条件

        Returns:
            融合后的检索结果
        """
        if self.base_retriever is None:
            raise ValueError("Base retriever not set")

        k = top_k or self.config.top_k

        # 生成查询变体
        queries = await self._generate_query_variants(query)
        queries.insert(0, query)  # 包含原始查询

        # 对每个查询进行检索
        all_results = []
        seen_chunks = set()

        for q in queries:
            results = await self.base_retriever.retrieve(
                q, top_k=k, filter_conditions=filter_conditions
            )
            for r in results:
                if r.chunk.chunk_id not in seen_chunks:
                    seen_chunks.add(r.chunk.chunk_id)
                    r.metadata["source_query"] = q
                    all_results.append(r)

        # 按分数排序并截取
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:k]

    async def _generate_query_variants(self, query: str) -> List[str]:
        """生成查询变体"""
        if self.llm_client is None:
            # 无 LLM 时返回简单变体
            return [query]

        # TODO: 使用 LLM 生成查询变体
        # 示例提示词:
        # "请为以下查询生成 3 个不同角度的变体，用于扩展检索范围..."
        return [query]
