"""
嵌入器实现

提供基于 API 的文本嵌入功能，支持:
- OpenAI Embeddings API (兼容各种 OpenAI 格式的 API)
"""

import logging
import os
from typing import List, Optional

from ..base.chunker import Chunk
from ..base.embedder import BaseEmbedder, EmbeddingResult
from ..base.registry import component_registries

logger = logging.getLogger(__name__)


@component_registries.embedder.register("openai")
class OpenAIEmbedder(BaseEmbedder):
    """
    OpenAI 嵌入器

    使用 OpenAI Embeddings API 生成嵌入。
    支持所有兼容 OpenAI API 格式的服务（如 Azure OpenAI、各种代理服务等）。

    环境变量:
        OPENAI_API_KEY: API 密钥
        OPENAI_API_BASE: API 基础 URL（可选，用于自定义端点）

    使用示例:
        embedder = OpenAIEmbedder(model_name="text-embedding-3-small")
        await embedder.setup()
        result = await embedder.embed(["Hello world"])
    """

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        dimensions: int = 1536,
        batch_size: int = 100,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            model_name=model_name,
            dimensions=dimensions,
            batch_size=batch_size,
            **kwargs,
        )
        self.api_key = api_key
        self.api_base = api_base
        self._client = None

    async def setup(self) -> None:
        """初始化 OpenAI 客户端"""
        try:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.api_key or os.getenv("OPENAI_API_KEY"),
                base_url=self.api_base or os.getenv("OPENAI_API_BASE"),
            )
            logger.info(f"OpenAI embedder initialized with model: {self.config.model_name}")

        except ImportError:
            logger.error("openai package not installed. Install with: pip install openai")
            raise

    async def teardown(self) -> None:
        """清理资源"""
        if self._client:
            await self._client.close()
            self._client = None
        logger.info("OpenAI embedder closed")

    async def embed(self, texts: List[str]) -> List[EmbeddingResult]:
        """批量嵌入文本"""
        if self._client is None:
            await self.setup()

        if not texts:
            return []

        results = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]

            response = await self._client.embeddings.create(
                model=self.config.model_name,
                input=batch,
                dimensions=self.config.dimensions,
            )

            for item in response.data:
                results.append(
                    EmbeddingResult(
                        dense=item.embedding,
                        model=self.config.model_name,
                        dimensions=len(item.embedding),
                        token_count=response.usage.total_tokens // len(batch),
                    )
                )

        logger.info(f"Embedded {len(texts)} texts via OpenAI API")
        return results

    async def embed_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """为切块添加嵌入向量"""
        texts = [chunk.content for chunk in chunks]
        embeddings = await self.embed(texts)

        for chunk, emb_result in zip(chunks, embeddings):
            chunk.embedding = emb_result.dense

        logger.info(f"Added embeddings to {len(chunks)} chunks")
        return chunks
