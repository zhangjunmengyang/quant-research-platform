"""
重排器基类

负责对检索结果进行重排序。
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .component import AsyncComponent, ComponentConfig, ComponentType
from .retriever import RetrievalResult
from .chunker import Chunk


@dataclass
class RerankResult:
    """重排结果"""
    chunk: Chunk
    original_score: float
    rerank_score: float
    original_rank: int
    rerank_rank: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RerankerConfig(ComponentConfig):
    """重排器配置"""
    # 模型配置
    model_name: str = "BAAI/bge-reranker-v2-m3"

    # 输出配置
    top_k: int = 5
    min_score: float = 0.0

    # 批处理
    batch_size: int = 32


class BaseReranker(AsyncComponent[RerankerConfig, List[RetrievalResult]]):
    """
    重排器基类

    负责对检索结果进行重排序，提高最终结果的相关性。

    设计要点:
    1. 使用交叉编码器计算精确相关性
    2. 支持批量处理
    3. 可以基于多种信号排序

    示例:
        @component_registries.reranker.register("bge-reranker")
        class BGEReranker(BaseReranker):
            async def rerank(
                self,
                query: str,
                results: List[RetrievalResult],
                top_k: int = 5,
            ) -> List[RetrievalResult]:
                # 使用 BGE-Reranker 重排序
                ...
    """

    component_type = ComponentType.RERANKER

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        top_k: int = 5,
        batch_size: int = 32,
        **kwargs,
    ):
        config = RerankerConfig(
            model_name=model_name,
            top_k=top_k,
            batch_size=batch_size,
            extra=kwargs,
        )
        super().__init__(config)

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """
        重排序检索结果

        Args:
            query: 查询文本
            results: 检索结果列表
            top_k: 返回数量

        Returns:
            重排序后的结果列表
        """
        raise NotImplementedError

    async def execute(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """执行重排序"""
        return await self.rerank(query, results, top_k)
