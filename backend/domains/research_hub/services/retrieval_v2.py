"""
研报检索服务 (LlamaIndex 版本)

基于 LlamaIndex 的语义检索和 RAG 问答服务。
"""

import logging
from typing import Any, Dict, List, Optional

from ..core.store import get_research_store, ResearchStore
from .llamaindex_rag import get_llamaindex_rag_service, LlamaIndexRAGService

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    研报检索服务

    功能:
    - 语义检索：根据查询文本检索相关研报片段
    - RAG 问答：检索 + 生成回答
    - 相似切块查询

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
        pipeline_name: Optional[str] = None,  # 保留兼容性，LlamaIndex 版本不使用
    ):
        self.database_url = database_url
        self._research_store: Optional[ResearchStore] = None
        self._rag_service: Optional[LlamaIndexRAGService] = None

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
        results = await self.rag_service.search(
            query=query,
            top_k=top_k,
            report_id=report_id,
            report_uuid=report_uuid,
            min_score=min_score,
        )

        # 丰富研报信息（如果 LlamaIndex 返回的信息不完整）
        for result in results:
            if not result.get("report_title") and result.get("report_uuid"):
                report = self.research_store.get_by_uuid(result["report_uuid"])
                if report:
                    result["report_title"] = report.title
                    result["report_id"] = report.id

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
            conversation_history: 对话历史（当前版本暂不支持）

        Returns:
            问答结果:
            - answer: 回答内容
            - sources: 来源引用列表
            - retrieved_chunks: 检索到的切块数量
        """
        result = await self.rag_service.ask(
            question=question,
            top_k=top_k,
            report_id=report_id,
            report_uuid=report_uuid,
            rerank=True,
        )

        # 丰富来源信息
        for source in result.get("sources", []):
            if not source.get("report_title") and source.get("report_uuid"):
                report = self.research_store.get_by_uuid(source["report_uuid"])
                if report:
                    source["report_title"] = report.title

        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "retrieved_chunks": result.get("retrieved_chunks", 0),
            "total_time": 0,  # LlamaIndex 版本暂不提供耗时统计
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
        results = await self.rag_service.get_similar_chunks(
            chunk_id=chunk_id,
            top_k=top_k,
            exclude_same_report=exclude_same_report,
        )

        # 丰富研报信息
        for result in results:
            if not result.get("report_title") and result.get("report_uuid"):
                report = self.research_store.get_by_uuid(result["report_uuid"])
                if report:
                    result["report_title"] = report.title

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
