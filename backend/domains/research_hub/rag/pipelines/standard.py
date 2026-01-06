"""
标准 RAG 流水线

编排完整的 RAG 流程:
Query -> Retrieval -> Rerank -> Generation -> Response
"""

import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from ..base.pipeline import (
    BasePipeline,
    PipelineConfig,
    PipelineContext,
    PipelineResult,
    PipelineStage,
    AgenticPipelineMixin,
)
from ..base.retriever import BaseRetriever, RetrievalResult
from ..base.reranker import BaseReranker, RerankResult
from ..base.generator import BaseGenerator, GenerationResult, SourceReference
from ..base.embedder import BaseEmbedder
from ..base.vector_store import BaseVectorStore
from ..base.registry import component_registries

logger = logging.getLogger(__name__)


@component_registries.pipeline.register("default")
class StandardPipeline(BasePipeline, AgenticPipelineMixin):
    """
    标准 RAG 流水线

    执行完整的 RAG 流程:
    1. Query Rewrite (可选): 改写查询以提高检索效果
    2. Retrieval: 检索相关文档
    3. Rerank (可选): 精排检索结果
    4. Context Build: 构建上下文
    5. Generation: 生成回答
    6. Post Process: 后处理

    支持 Agentic RAG 扩展:
    - Planning: 规划执行步骤
    - Tool Call: 调用外部工具
    - Reflection: 反思和自我修正

    使用示例:
        pipeline = StandardPipeline(
            retriever=hybrid_retriever,
            reranker=bge_reranker,
            generator=llm_generator,
        )
        result = await pipeline.run("什么是动量因子？")
    """

    def __init__(
        self,
        retriever: Optional[BaseRetriever] = None,
        reranker: Optional[BaseReranker] = None,
        generator: Optional[BaseGenerator] = None,
        embedder: Optional[BaseEmbedder] = None,
        vector_store: Optional[BaseVectorStore] = None,
        retrieval_top_k: int = 20,
        rerank_top_k: int = 5,
        enable_rerank: bool = True,
        enable_query_rewrite: bool = False,
        max_context_length: int = 8000,
        **kwargs,
    ):
        super().__init__(
            retriever=retriever,
            reranker=reranker,
            generator=generator,
            retrieval_top_k=retrieval_top_k,
            rerank_top_k=rerank_top_k,
            enable_rerank=enable_rerank,
            **kwargs,
        )
        self.embedder = embedder
        self.vector_store = vector_store
        self.enable_query_rewrite = enable_query_rewrite
        self.max_context_length = max_context_length

        # 如果有 embedder 和 vector_store，自动配置 retriever
        if retriever and embedder:
            retriever.set_embedder(embedder)
        if retriever and vector_store:
            retriever.set_vector_store(vector_store)

    async def run(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> PipelineResult:
        """
        执行 RAG 流水线

        Args:
            query: 用户问题
            conversation_history: 对话历史
            filter_conditions: 过滤条件（如限制特定研报）

        Returns:
            流水线结果
        """
        start_time = time.time()

        # 初始化上下文
        ctx = PipelineContext(
            query=query,
            conversation_history=conversation_history or [],
            filter_conditions=filter_conditions,
        )

        try:
            # 1. Query Rewrite (可选)
            if self.enable_query_rewrite:
                await self._run_stage(
                    PipelineStage.QUERY_REWRITE,
                    ctx,
                    self._query_rewrite,
                )
            else:
                ctx.rewritten_query = query

            # 2. Retrieval
            await self._run_stage(
                PipelineStage.RETRIEVAL,
                ctx,
                self._retrieval,
            )

            # 3. Rerank (可选)
            if self.config.enable_rerank and self.reranker:
                await self._run_stage(
                    PipelineStage.RERANK,
                    ctx,
                    self._rerank,
                )
            else:
                # 直接使用检索结果
                ctx.reranked_results = ctx.retrieval_results[:self.config.rerank_top_k]

            # 4. Context Build
            await self._run_stage(
                PipelineStage.CONTEXT_BUILD,
                ctx,
                self._context_build,
            )

            # 5. Generation
            await self._run_stage(
                PipelineStage.GENERATION,
                ctx,
                self._generation,
            )

            # 6. Post Process
            await self._run_stage(
                PipelineStage.POST_PROCESS,
                ctx,
                self._post_process,
            )

            # 构建结果
            result = PipelineResult.from_context(ctx)
            result.total_time = time.time() - start_time

            logger.info(
                f"Pipeline completed in {result.total_time:.2f}s, "
                f"retrieved {result.retrieved_chunks} chunks, "
                f"reranked to {result.reranked_chunks}"
            )

            return result

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            return PipelineResult.error(str(e))

    async def run_stream(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Union[PipelineResult, GenerationResult]]:
        """
        流式执行 RAG 流水线

        先执行检索和重排，然后流式生成回答。

        Yields:
            生成结果的增量部分
        """
        start_time = time.time()

        # 初始化上下文
        ctx = PipelineContext(
            query=query,
            conversation_history=conversation_history or [],
            filter_conditions=filter_conditions,
        )

        try:
            # 1-4: 执行到 Context Build
            if self.enable_query_rewrite:
                await self._run_stage(PipelineStage.QUERY_REWRITE, ctx, self._query_rewrite)
            else:
                ctx.rewritten_query = query

            await self._run_stage(PipelineStage.RETRIEVAL, ctx, self._retrieval)

            if self.config.enable_rerank and self.reranker:
                await self._run_stage(PipelineStage.RERANK, ctx, self._rerank)
            else:
                ctx.reranked_results = ctx.retrieval_results[:self.config.rerank_top_k]

            await self._run_stage(PipelineStage.CONTEXT_BUILD, ctx, self._context_build)

            # 5. 流式生成
            if self.generator:
                async for gen_result in self.generator.generate_stream(
                    query=ctx.rewritten_query or query,
                    context=ctx.reranked_results,
                    conversation_history=conversation_history,
                ):
                    yield gen_result

            # 最终结果
            result = PipelineResult.from_context(ctx)
            result.total_time = time.time() - start_time
            yield result

        except Exception as e:
            logger.error(f"Pipeline stream error: {e}", exc_info=True)
            yield PipelineResult.error(str(e))

    async def _query_rewrite(self, ctx: PipelineContext) -> None:
        """查询重写"""
        # TODO: 使用 LLM 重写查询
        # 当前简化实现：直接使用原始查询
        ctx.rewritten_query = ctx.query

    async def _retrieval(self, ctx: PipelineContext) -> None:
        """检索"""
        if self.retriever is None:
            raise ValueError("Retriever not configured")

        query = ctx.rewritten_query or ctx.query
        results = await self.retriever.retrieve(
            query=query,
            top_k=self.config.retrieval_top_k,
            filter_conditions=ctx.filter_conditions,
        )
        ctx.retrieval_results = results

    async def _rerank(self, ctx: PipelineContext) -> None:
        """重排"""
        if self.reranker is None:
            ctx.reranked_results = ctx.retrieval_results[:self.config.rerank_top_k]
            return

        query = ctx.rewritten_query or ctx.query
        reranked = await self.reranker.rerank(
            query=query,
            results=ctx.retrieval_results,
            top_k=self.config.rerank_top_k,
        )
        # RerankResult 转换为 RetrievalResult 兼容格式
        ctx.reranked_results = reranked

    async def _context_build(self, ctx: PipelineContext) -> None:
        """构建上下文"""
        if self.generator:
            ctx.context_text = self.generator.build_context(
                ctx.reranked_results,
                max_length=self.max_context_length,
            )
        else:
            # 简单拼接
            parts = []
            for r in ctx.reranked_results:
                if hasattr(r, "chunk"):
                    parts.append(r.chunk.content)
                else:
                    parts.append(r.content)
            ctx.context_text = "\n\n".join(parts)

    async def _generation(self, ctx: PipelineContext) -> None:
        """生成回答"""
        if self.generator is None:
            raise ValueError("Generator not configured")

        query = ctx.rewritten_query or ctx.query
        result = await self.generator.generate(
            query=query,
            context=ctx.reranked_results,
            conversation_history=ctx.conversation_history,
        )
        ctx.generation_result = result

    async def _post_process(self, ctx: PipelineContext) -> None:
        """后处理"""
        # 当前无后处理逻辑
        pass


@component_registries.pipeline.register("fast")
class FastPipeline(StandardPipeline):
    """
    快速流水线

    低延迟配置，适合实时对话场景。
    - 较小的 top_k
    - 跳过重排
    - 较短的上下文
    """

    def __init__(
        self,
        retriever: Optional[BaseRetriever] = None,
        generator: Optional[BaseGenerator] = None,
        retrieval_top_k: int = 10,
        **kwargs,
    ):
        super().__init__(
            retriever=retriever,
            reranker=None,
            generator=generator,
            retrieval_top_k=retrieval_top_k,
            rerank_top_k=retrieval_top_k,
            enable_rerank=False,
            enable_query_rewrite=False,
            max_context_length=4000,
            **kwargs,
        )
