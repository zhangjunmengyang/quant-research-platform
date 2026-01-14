"""
检索器基类

负责从向量存储中检索相关内容。
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from .component import AsyncComponent, ComponentConfig, ComponentType
from .vector_store import SearchResult
from .embedder import BaseEmbedder, EmbeddingResult


class RetrievalMode(Enum):
    """检索模式"""
    DENSE = "dense"  # 仅稠密向量
    SPARSE = "sparse"  # 仅稀疏向量 (BM25)
    HYBRID = "hybrid"  # 混合检索
    MULTI_ROUTE = "multi_route"  # 多路检索


@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    score: float

    # 来源信息
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    page_number: Optional[int] = None

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 原始搜索结果
    raw_result: Optional[SearchResult] = None

    @classmethod
    def from_search_result(cls, result: SearchResult) -> "RetrievalResult":
        """从搜索结果创建"""
        return cls(
            content=result.content,
            score=result.score,
            document_id=result.document_id,
            chunk_id=result.chunk_id,
            page_number=result.chunk.metadata.page_start if result.chunk.metadata else None,
            metadata=result.metadata,
            raw_result=result,
        )


@dataclass
class RetrieverConfig(ComponentConfig):
    """检索器配置"""
    # 检索模式
    mode: RetrievalMode = RetrievalMode.HYBRID

    # 基本参数
    top_k: int = 10

    # 混合检索权重
    dense_weight: float = 0.7
    sparse_weight: float = 0.3

    # 过滤
    min_score: float = 0.0
    max_results: Optional[int] = None

    # 多路检索
    routes: List[Dict[str, Any]] = field(default_factory=list)


class BaseRetriever(AsyncComponent[RetrieverConfig, List[RetrievalResult]]):
    """
    检索器基类

    负责从向量存储中检索相关内容，支持:
    - 稠密检索
    - 稀疏检索 (BM25)
    - 混合检索
    - 多路检索

    设计要点:
    1. 封装嵌入和搜索逻辑
    2. 支持查询重写
    3. 支持结果过滤和后处理
    4. 为 Agentic RAG 预留反馈接口

    示例:
        @component_registries.retriever.register("hybrid")
        class HybridRetriever(BaseRetriever):
            async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
                # 混合检索逻辑
                ...
    """

    component_type = ComponentType.RETRIEVER

    def __init__(
        self,
        embedder: Optional[BaseEmbedder] = None,
        vector_store: Optional["BaseVectorStore"] = None,
        mode: str = "hybrid",
        top_k: int = 10,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        **kwargs,
    ):
        config = RetrieverConfig(
            mode=RetrievalMode(mode) if isinstance(mode, str) else mode,
            top_k=top_k,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
            extra=kwargs,
        )
        super().__init__(config)
        self.embedder = embedder
        self.vector_store = vector_store

    def set_embedder(self, embedder: BaseEmbedder) -> None:
        """设置嵌入器"""
        self.embedder = embedder

    def set_vector_store(self, vector_store: "BaseVectorStore") -> None:
        """设置向量存储"""
        from .vector_store import BaseVectorStore
        self.vector_store = vector_store

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        检索相关内容

        Args:
            query: 查询文本
            top_k: 返回数量
            filter_conditions: 过滤条件

        Returns:
            检索结果列表
        """
        raise NotImplementedError

    async def retrieve_with_feedback(
        self,
        query: str,
        feedback: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """
        带反馈的检索（用于 Agentic RAG）

        Args:
            query: 查询文本
            feedback: Agent 反馈，可能包含:
                - relevance_scores: 之前结果的相关性评分
                - excluded_chunks: 需要排除的切块
                - preferred_sources: 偏好的来源
            top_k: 返回数量

        Returns:
            检索结果列表
        """
        # 默认实现忽略反馈
        return await self.retrieve(query, top_k)

    async def rewrite_query(self, query: str) -> str:
        """
        查询重写（用于 Agentic RAG）

        子类可覆盖以实现:
        - 查询扩展
        - 同义词替换
        - 意图识别
        """
        return query

    async def execute(
        self,
        query: str,
        top_k: Optional[int] = None,
        **kwargs,
    ) -> List[RetrievalResult]:
        """执行检索"""
        return await self.retrieve(query, top_k, **kwargs)
