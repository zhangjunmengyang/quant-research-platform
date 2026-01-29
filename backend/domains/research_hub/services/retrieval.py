"""
研报检索服务

基于 LlamaIndex 的语义检索服务，集成查询重写和结果重排功能。
"""

import logging
from typing import Any

from ..core.store import ResearchStore, get_research_store
from .llamaindex_rag import LlamaIndexRAGService, get_llamaindex_rag_service
from .query_processor import QueryProcessor, get_query_processor

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    研报检索服务

    功能:
    - 语义检索: 根据查询文本检索相关研报片段
    - 查询重写: 使用 LLM 优化查询
    - 结果重排: 使用 LLM 对结果重新排序

    使用示例:
        service = RetrievalService()

        # 基础检索
        results = await service.search("什么是动量因子")

        # 启用查询重写和重排
        results = await service.retrieve(
            query="动量",
            enable_rewrite=True,
            enable_rerank=True,
        )
    """

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url
        self._research_store: ResearchStore | None = None
        self._rag_service: LlamaIndexRAGService | None = None
        self._query_processor: QueryProcessor | None = None

    @property
    def research_store(self) -> ResearchStore:
        if self._research_store is None:
            self._research_store = get_research_store(self.database_url)
        return self._research_store

    @property
    def rag_service(self) -> LlamaIndexRAGService:
        if self._rag_service is None:
            self._rag_service = get_llamaindex_rag_service()
        return self._rag_service

    @property
    def query_processor(self) -> QueryProcessor:
        if self._query_processor is None:
            self._query_processor = get_query_processor()
        return self._query_processor

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        report_ids: list[int] | None = None,
        report_uuids: list[str] | None = None,
        categories: list[str] | None = None,
        min_score: float = 0.0,
        enable_rewrite: bool = False,
        enable_rerank: bool = False,
        rerank_top_k: int | None = None,
    ) -> dict[str, Any]:
        """
        统一检索接口

        Args:
            query: 查询文本
            top_k: 返回数量
            report_ids: 限定研报 ID 列表（前置过滤）
            report_uuids: 限定研报 UUID 列表（前置过滤）
            categories: 限定分类列表（前置过滤）
            min_score: 最小相似度分数
            enable_rewrite: 是否启用查询重写
            enable_rerank: 是否启用结果重排
            rerank_top_k: 重排后返回的数量

        Returns:
            检索结果:
            - query: 原始查询
            - rewritten_query: 重写后的查询（如果启用）
            - results: 检索结果列表
            - total: 结果总数
        """
        original_query = query
        rewritten_query = None

        # 查询重写
        if enable_rewrite:
            rewritten_query = await self.query_processor.rewrite_query(query)
            query = rewritten_query

        # 计算检索数量（如果需要重排，多检索一些）
        retrieve_top_k = top_k
        if enable_rerank:
            retrieve_top_k = max(top_k * 3, 30)  # 检索更多用于重排

        # 执行检索
        # 目前只支持单个 report_id/report_uuid 过滤，取第一个
        report_id = report_ids[0] if report_ids else None
        report_uuid = report_uuids[0] if report_uuids else None

        results = await self.rag_service.search(
            query=query,
            top_k=retrieve_top_k,
            report_id=report_id,
            report_uuid=report_uuid,
            min_score=min_score,
        )

        # 丰富研报信息
        self._enrich_results(results)

        # 分类过滤（后置过滤）
        if categories:
            results = [
                r for r in results
                if r.get("category") in categories
            ]

        # 结果重排
        if enable_rerank and len(results) > 1:
            final_top_k = rerank_top_k or top_k
            results = await self.query_processor.rerank(
                query=original_query,
                results=results,
                top_k=final_top_k,
            )
        elif len(results) > top_k:
            results = results[:top_k]

        logger.info(
            f"检索完成: query='{original_query[:30]}...', "
            f"rewrite={enable_rewrite}, rerank={enable_rerank}, "
            f"返回 {len(results)} 条结果"
        )

        return {
            "query": original_query,
            "rewritten_query": rewritten_query,
            "results": results,
            "total": len(results),
        }

    async def search(
        self,
        query: str,
        top_k: int = 10,
        report_id: int | None = None,
        report_uuid: str | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        基础语义检索（兼容旧接口）

        Args:
            query: 查询文本
            top_k: 返回数量
            report_id: 限定搜索的研报 ID
            report_uuid: 限定搜索的研报 UUID
            min_score: 最小相似度分数

        Returns:
            检索结果列表
        """
        results = await self.rag_service.search(
            query=query,
            top_k=top_k,
            report_id=report_id,
            report_uuid=report_uuid,
            min_score=min_score,
        )

        self._enrich_results(results)
        return results

    def _enrich_results(self, results: list[dict[str, Any]]) -> None:
        """丰富检索结果的研报信息"""
        for result in results:
            if not result.get("report_title") and result.get("report_uuid"):
                report = self.research_store.get_by_uuid(result["report_uuid"])
                if report:
                    result["report_title"] = report.title
                    result["report_id"] = report.id
                    result["category"] = report.category


# 单例管理
_retrieval_service: RetrievalService | None = None


def get_retrieval_service(
    database_url: str | None = None,
    **kwargs,  # 兼容旧参数
) -> RetrievalService:
    """获取检索服务单例"""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService(database_url=database_url)
    return _retrieval_service
