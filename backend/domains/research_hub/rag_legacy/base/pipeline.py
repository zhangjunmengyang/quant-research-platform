"""
RAG 流水线基类

负责编排完整的 RAG 流程。
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union
from enum import Enum
import time
import logging

from .component import AsyncComponent, ComponentConfig, ComponentType
from .parser import BaseParser, ParsedDocument
from .chunker import BaseChunker, Chunk
from .embedder import BaseEmbedder, EmbeddingResult
from .vector_store import BaseVectorStore
from .retriever import BaseRetriever, RetrievalResult
from .reranker import BaseReranker
from .generator import BaseGenerator, GenerationResult, SourceReference

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """流水线阶段"""
    QUERY_REWRITE = "query_rewrite"
    RETRIEVAL = "retrieval"
    RERANK = "rerank"
    CONTEXT_BUILD = "context_build"
    GENERATION = "generation"
    POST_PROCESS = "post_process"
    # Agentic 扩展
    PLANNING = "planning"
    TOOL_CALL = "tool_call"
    REFLECTION = "reflection"


@dataclass
class PipelineContext:
    """
    流水线上下文

    在流水线各阶段之间传递状态。
    为 Agentic RAG 预留扩展字段。
    """
    # 输入
    query: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)

    # 中间结果
    rewritten_query: Optional[str] = None
    retrieval_results: List[RetrievalResult] = field(default_factory=list)
    reranked_results: List[RetrievalResult] = field(default_factory=list)
    context_text: Optional[str] = None

    # 输出
    generation_result: Optional[GenerationResult] = None

    # 过滤条件
    filter_conditions: Optional[Dict[str, Any]] = None

    # Agentic RAG 扩展
    agent_state: Dict[str, Any] = field(default_factory=dict)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    planning_steps: List[str] = field(default_factory=list)
    reflection_notes: List[str] = field(default_factory=list)

    # 执行追踪
    stage_timings: Dict[str, float] = field(default_factory=dict)
    current_stage: Optional[PipelineStage] = None

    def record_timing(self, stage: str, duration: float) -> None:
        """记录阶段耗时"""
        self.stage_timings[stage] = duration


@dataclass
class PipelineResult:
    """流水线结果"""
    # 主要输出
    answer: str
    sources: List[SourceReference] = field(default_factory=list)

    # 检索信息
    retrieved_chunks: int = 0
    reranked_chunks: int = 0

    # 执行信息
    success: bool = True
    error: Optional[str] = None
    timings: Dict[str, float] = field(default_factory=dict)
    total_time: float = 0.0

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_context(cls, ctx: PipelineContext) -> "PipelineResult":
        """从上下文创建结果"""
        gen_result = ctx.generation_result
        return cls(
            answer=gen_result.content if gen_result else "",
            sources=gen_result.sources if gen_result else [],
            retrieved_chunks=len(ctx.retrieval_results),
            reranked_chunks=len(ctx.reranked_results),
            timings=ctx.stage_timings,
            total_time=sum(ctx.stage_timings.values()),
        )

    @classmethod
    def error(cls, error_msg: str) -> "PipelineResult":
        """创建错误结果"""
        return cls(
            answer="",
            success=False,
            error=error_msg,
        )


@dataclass
class PipelineConfig(ComponentConfig):
    """流水线配置"""
    # 检索配置
    retrieval_top_k: int = 20
    rerank_top_k: int = 5

    # 生成配置
    max_context_length: int = 8000
    include_sources: bool = True

    # 行为配置
    enable_query_rewrite: bool = False
    enable_rerank: bool = True

    # Agentic 配置
    enable_planning: bool = False
    enable_reflection: bool = False
    max_iterations: int = 3


# 钩子函数类型
StageHook = Callable[[PipelineContext], None]


class BasePipeline(AsyncComponent[PipelineConfig, PipelineResult]):
    """
    RAG 流水线基类

    编排完整的 RAG 流程:
    1. Query Rewrite (可选)
    2. Retrieval
    3. Rerank (可选)
    4. Context Build
    5. Generation
    6. Post Process

    Agentic RAG 扩展:
    - Planning: 规划执行步骤
    - Tool Call: 调用外部工具
    - Reflection: 反思和自我修正

    设计要点:
    1. 组件可插拔
    2. 阶段钩子支持自定义逻辑
    3. 上下文在阶段间传递
    4. 支持流式输出

    示例:
        @component_registries.pipeline.register("advanced_rag")
        class AdvancedRAGPipeline(BasePipeline):
            async def run(self, query: str) -> PipelineResult:
                # 高级 RAG 流程
                ...
    """

    component_type = ComponentType.PIPELINE

    def __init__(
        self,
        retriever: Optional[BaseRetriever] = None,
        reranker: Optional[BaseReranker] = None,
        generator: Optional[BaseGenerator] = None,
        retrieval_top_k: int = 20,
        rerank_top_k: int = 5,
        enable_rerank: bool = True,
        **kwargs,
    ):
        config = PipelineConfig(
            retrieval_top_k=retrieval_top_k,
            rerank_top_k=rerank_top_k,
            enable_rerank=enable_rerank,
            extra=kwargs,
        )
        super().__init__(config)

        self.retriever = retriever
        self.reranker = reranker
        self.generator = generator

        # 阶段钩子
        self._pre_hooks: Dict[PipelineStage, List[StageHook]] = {}
        self._post_hooks: Dict[PipelineStage, List[StageHook]] = {}

    def set_retriever(self, retriever: BaseRetriever) -> None:
        """设置检索器"""
        self.retriever = retriever

    def set_reranker(self, reranker: BaseReranker) -> None:
        """设置重排器"""
        self.reranker = reranker

    def set_generator(self, generator: BaseGenerator) -> None:
        """设置生成器"""
        self.generator = generator

    def add_pre_hook(self, stage: PipelineStage, hook: StageHook) -> None:
        """添加阶段前钩子"""
        if stage not in self._pre_hooks:
            self._pre_hooks[stage] = []
        self._pre_hooks[stage].append(hook)

    def add_post_hook(self, stage: PipelineStage, hook: StageHook) -> None:
        """添加阶段后钩子"""
        if stage not in self._post_hooks:
            self._post_hooks[stage] = []
        self._post_hooks[stage].append(hook)

    async def _run_hooks(
        self,
        hooks: List[StageHook],
        ctx: PipelineContext,
    ) -> None:
        """执行钩子"""
        for hook in hooks:
            hook(ctx)

    async def _run_stage(
        self,
        stage: PipelineStage,
        ctx: PipelineContext,
        stage_fn: Callable,
    ) -> None:
        """执行阶段"""
        ctx.current_stage = stage

        # 前钩子
        if stage in self._pre_hooks:
            await self._run_hooks(self._pre_hooks[stage], ctx)

        # 执行阶段
        start_time = time.time()
        await stage_fn(ctx)
        duration = time.time() - start_time
        ctx.record_timing(stage.value, duration)

        # 后钩子
        if stage in self._post_hooks:
            await self._run_hooks(self._post_hooks[stage], ctx)

    @abstractmethod
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
            filter_conditions: 过滤条件

        Returns:
            流水线结果
        """
        raise NotImplementedError

    async def run_stream(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Union[PipelineResult, GenerationResult]]:
        """
        流式执行 RAG 流水线

        Yields:
            生成结果的增量部分
        """
        # 默认实现：一次性返回
        result = await self.run(query, conversation_history, filter_conditions)
        yield result

    async def execute(
        self,
        query: str,
        **kwargs,
    ) -> PipelineResult:
        """执行流水线"""
        return await self.run(query, **kwargs)


class AgenticPipelineMixin:
    """
    Agentic RAG 混入类

    提供 Agentic RAG 扩展功能:
    - 规划: 分解问题为多个步骤
    - 工具调用: 调用外部工具获取信息
    - 反思: 评估结果质量并改进
    """

    async def plan(self, ctx: PipelineContext) -> List[str]:
        """
        规划执行步骤

        Args:
            ctx: 流水线上下文

        Returns:
            执行步骤列表
        """
        # 默认: 单步执行
        return ["retrieve", "generate"]

    async def call_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        ctx: PipelineContext,
    ) -> Dict[str, Any]:
        """
        调用工具

        Args:
            tool_name: 工具名称
            tool_input: 工具输入
            ctx: 流水线上下文

        Returns:
            工具输出
        """
        raise NotImplementedError("Subclass must implement call_tool")

    async def reflect(
        self,
        ctx: PipelineContext,
    ) -> bool:
        """
        反思执行结果

        Args:
            ctx: 流水线上下文

        Returns:
            是否需要继续迭代
        """
        # 默认: 不需要迭代
        return False

    async def should_continue(self, ctx: PipelineContext) -> bool:
        """判断是否应继续迭代"""
        max_iter = ctx.agent_state.get("max_iterations", 3)
        current_iter = ctx.agent_state.get("current_iteration", 0)
        return current_iter < max_iter and await self.reflect(ctx)
