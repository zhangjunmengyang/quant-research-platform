"""
重排器实现

使用交叉编码器对检索结果进行精排。
"""

import logging
from typing import Any, Dict, List, Optional

from ..base.reranker import BaseReranker, RerankResult
from ..base.retriever import RetrievalResult
from ..base.registry import component_registries

logger = logging.getLogger(__name__)


@component_registries.reranker.register("bge_reranker")
class BGEReranker(BaseReranker):
    """
    BGE 重排器

    使用 BAAI/bge-reranker-v2-m3 模型对检索结果进行重排。
    交叉编码器直接计算 query-document 相关性分数。

    要求:
        pip install FlagEmbedding

    使用示例:
        reranker = BGEReranker(model="BAAI/bge-reranker-v2-m3", top_k=5)
        await reranker.setup()
        results = await reranker.rerank(query, retrieval_results)
    """

    def __init__(
        self,
        model: str = "BAAI/bge-reranker-v2-m3",
        top_k: int = 5,
        max_length: int = 1024,
        batch_size: int = 32,
        device: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(model=model, top_k=top_k, **kwargs)
        self.max_length = max_length
        self.batch_size = batch_size
        self.device = device
        self._model = None

    async def setup(self) -> None:
        """初始化模型"""
        try:
            from FlagEmbedding import FlagReranker

            logger.info(f"Loading BGE reranker: {self.config.model}")

            self._model = FlagReranker(
                self.config.model,
                use_fp16=True,
                device=self.device,
            )

            logger.info("BGE reranker loaded successfully")

        except ImportError:
            logger.error(
                "FlagEmbedding not installed. "
                "Install with: pip install FlagEmbedding"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to load BGE reranker: {e}")
            raise

    async def teardown(self) -> None:
        """清理模型资源"""
        self._model = None
        logger.info("BGE reranker unloaded")

    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: Optional[int] = None,
    ) -> List[RerankResult]:
        """
        重排检索结果

        Args:
            query: 查询文本
            results: 检索结果列表
            top_k: 返回数量

        Returns:
            重排后的结果
        """
        if self._model is None:
            await self.setup()

        if not results:
            return []

        k = top_k or self.config.top_k

        # 构建 query-document 对
        pairs = [[query, r.chunk.content] for r in results]

        # 计算相关性分数
        scores = self._model.compute_score(
            pairs,
            batch_size=self.batch_size,
            max_length=self.max_length,
            normalize=True,  # 归一化到 0-1
        )

        # 如果只有一个结果，scores 是单个值
        if not isinstance(scores, list):
            scores = [scores]

        # 创建结果并排序
        reranked = []
        for i, (result, score) in enumerate(zip(results, scores)):
            reranked.append(
                RerankResult(
                    chunk=result.chunk,
                    original_score=result.score,
                    rerank_score=float(score),
                    original_rank=i,
                    metadata={
                        **result.metadata,
                        "reranker": "bge_reranker",
                    },
                )
            )

        # 按重排分数降序排列
        reranked.sort(key=lambda x: x.rerank_score, reverse=True)

        # 更新排名
        for i, r in enumerate(reranked):
            r.rerank_rank = i

        logger.info(
            f"Reranked {len(results)} results, returning top {min(k, len(reranked))}"
        )

        return reranked[:k]


@component_registries.reranker.register("none")
class NoOpReranker(BaseReranker):
    """
    空操作重排器

    不进行重排，直接返回原始结果。
    用于快速流水线或测试。
    """

    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: Optional[int] = None,
    ) -> List[RerankResult]:
        """直接返回结果，不重排"""
        k = top_k or self.config.top_k

        reranked = []
        for i, result in enumerate(results[:k]):
            reranked.append(
                RerankResult(
                    chunk=result.chunk,
                    original_score=result.score,
                    rerank_score=result.score,  # 保持原始分数
                    original_rank=i,
                    rerank_rank=i,
                    metadata={
                        **result.metadata,
                        "reranker": "none",
                    },
                )
            )

        return reranked


@component_registries.reranker.register("cohere")
class CohereReranker(BaseReranker):
    """
    Cohere 重排器

    使用 Cohere Rerank API 进行重排。
    需要 Cohere API Key。

    使用示例:
        reranker = CohereReranker(
            model="rerank-multilingual-v3.0",
            api_key="your-api-key",
        )
        results = await reranker.rerank(query, retrieval_results)
    """

    def __init__(
        self,
        model: str = "rerank-multilingual-v3.0",
        top_k: int = 5,
        api_key: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(model=model, top_k=top_k, **kwargs)
        self.api_key = api_key
        self._client = None

    async def setup(self) -> None:
        """初始化 Cohere 客户端"""
        try:
            import cohere
            import os

            self._client = cohere.Client(
                api_key=self.api_key or os.getenv("COHERE_API_KEY")
            )
            logger.info(f"Cohere reranker initialized with model: {self.config.model}")

        except ImportError:
            logger.error("cohere package not installed. Install with: pip install cohere")
            raise

    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: Optional[int] = None,
    ) -> List[RerankResult]:
        """使用 Cohere API 重排"""
        if self._client is None:
            await self.setup()

        if not results:
            return []

        k = top_k or self.config.top_k

        # 调用 Cohere Rerank API
        documents = [r.chunk.content for r in results]

        response = self._client.rerank(
            model=self.config.model,
            query=query,
            documents=documents,
            top_n=k,
        )

        # 构建结果
        reranked = []
        for item in response.results:
            original_result = results[item.index]
            reranked.append(
                RerankResult(
                    chunk=original_result.chunk,
                    original_score=original_result.score,
                    rerank_score=item.relevance_score,
                    original_rank=item.index,
                    rerank_rank=len(reranked),
                    metadata={
                        **original_result.metadata,
                        "reranker": "cohere",
                    },
                )
            )

        return reranked
