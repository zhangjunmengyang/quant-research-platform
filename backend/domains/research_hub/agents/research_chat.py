"""
研报对话 Agent

单研报 Chat 场景的 Agent 实现。
"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from .base import BaseAgent, AgentConfig, AgentResponse
from ..rag.base.pipeline import BasePipeline, PipelineResult
from ..rag.base.generator import GenerationResult

logger = logging.getLogger(__name__)


class ResearchChatAgent(BaseAgent):
    """
    研报对话 Agent

    针对单研报 Chat 场景，基于指定研报进行问答。

    特性:
    - 支持动态模型切换
    - 调用 RAG Pipeline 进行检索增强生成
    - 支持流式响应

    使用示例:
        from domains.research_hub.services.pipeline_factory import get_pipeline_factory

        factory = get_pipeline_factory()
        pipeline = await factory.get_or_create_pipeline()
        agent = ResearchChatAgent(pipeline=pipeline)

        # 同步对话
        response = await agent.chat(
            query="什么是动量因子?",
            report_id=123,
            model_key="claude",
        )

        # 流式对话
        async for chunk in agent.chat_stream(query, report_id=123):
            print(chunk.content, end="")
    """

    def __init__(
        self,
        pipeline: Optional[BasePipeline] = None,
        config: Optional[AgentConfig] = None,
        **kwargs,
    ):
        super().__init__(config=config, **kwargs)
        self._pipeline = pipeline

    def set_pipeline(self, pipeline: BasePipeline) -> None:
        """设置 RAG Pipeline"""
        self._pipeline = pipeline

    async def _do_setup(self) -> None:
        """初始化 Agent"""
        if self._pipeline is not None:
            await self._pipeline.setup()

    async def chat(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        model_key: Optional[str] = None,
        report_id: Optional[int] = None,
        **kwargs,
    ) -> AgentResponse:
        """
        同步对话

        Args:
            query: 用户问题
            conversation_history: 对话历史
            model_key: 指定使用的模型
            report_id: 限制检索的研报 ID

        Returns:
            Agent 响应
        """
        if self._pipeline is None:
            return AgentResponse.complete(
                content="Agent 未配置 Pipeline，无法执行对话",
                sources=[],
                error="pipeline_not_configured",
            )

        # 获取实际使用的模型
        effective_model = self.get_effective_model(model_key)

        # 临时修改 generator 的模型配置
        original_model_key = None
        if hasattr(self._pipeline, "generator") and self._pipeline.generator:
            original_model_key = self._pipeline.generator.config.model_key
            self._pipeline.generator.config.model_key = effective_model

        try:
            # 构建过滤条件
            filter_conditions = None
            if report_id:
                filter_conditions = {"report_id": report_id}

            # 执行 RAG Pipeline
            result: PipelineResult = await self._pipeline.run(
                query=query,
                conversation_history=conversation_history,
                filter_conditions=filter_conditions,
            )

            return AgentResponse.complete(
                content=result.answer,
                sources=result.sources,
                model=effective_model,
                retrieved_chunks=result.retrieved_chunks,
                reranked_chunks=result.reranked_chunks,
                total_time=result.total_time,
                timings=result.timings,
            )

        except Exception as e:
            logger.error(f"ResearchChatAgent.chat error: {e}")
            return AgentResponse.complete(
                content=f"对话出错: {str(e)}",
                sources=[],
                error=str(e),
            )

        finally:
            # 恢复原始模型配置
            if original_model_key is not None and hasattr(self._pipeline, "generator"):
                self._pipeline.generator.config.model_key = original_model_key

    async def chat_stream(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        model_key: Optional[str] = None,
        report_id: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[AgentResponse]:
        """
        流式对话

        Args:
            query: 用户问题
            conversation_history: 对话历史
            model_key: 指定使用的模型
            report_id: 限制检索的研报 ID

        Yields:
            Agent 响应片段
        """
        if self._pipeline is None:
            yield AgentResponse.complete(
                content="Agent 未配置 Pipeline，无法执行对话",
                sources=[],
                error="pipeline_not_configured",
            )
            return

        # 获取实际使用的模型
        effective_model = self.get_effective_model(model_key)

        # 临时修改 generator 的模型配置
        original_model_key = None
        if hasattr(self._pipeline, "generator") and self._pipeline.generator:
            original_model_key = self._pipeline.generator.config.model_key
            self._pipeline.generator.config.model_key = effective_model

        try:
            # 构建过滤条件
            filter_conditions = None
            if report_id:
                filter_conditions = {"report_id": report_id}

            # 流式执行 RAG Pipeline
            async for chunk in self._pipeline.run_stream(
                query=query,
                conversation_history=conversation_history,
                filter_conditions=filter_conditions,
            ):
                if isinstance(chunk, GenerationResult):
                    if chunk.is_complete:
                        # 最终结果，包含来源
                        yield AgentResponse.complete(
                            content=chunk.content,
                            sources=chunk.sources,
                            model=effective_model,
                        )
                    else:
                        # 流式片段
                        yield AgentResponse.streaming(
                            content=chunk.content,
                            model=effective_model,
                        )

                elif isinstance(chunk, PipelineResult):
                    # Pipeline 完成结果
                    yield AgentResponse.complete(
                        content=chunk.answer,
                        sources=chunk.sources,
                        model=effective_model,
                        retrieved_chunks=chunk.retrieved_chunks,
                        reranked_chunks=chunk.reranked_chunks,
                        total_time=chunk.total_time,
                    )

        except Exception as e:
            logger.error(f"ResearchChatAgent.chat_stream error: {e}")
            yield AgentResponse.complete(
                content=f"对话出错: {str(e)}",
                sources=[],
                error=str(e),
            )

        finally:
            # 恢复原始模型配置
            if original_model_key is not None and hasattr(self._pipeline, "generator"):
                self._pipeline.generator.config.model_key = original_model_key
