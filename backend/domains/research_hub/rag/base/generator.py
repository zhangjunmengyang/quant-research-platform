"""
生成器基类

负责基于检索结果生成回答。
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

from .component import AsyncComponent, ComponentConfig, ComponentType
from .retriever import RetrievalResult


@dataclass
class SourceReference:
    """来源引用"""
    document_id: str
    chunk_id: str
    content: str  # 引用的内容片段
    page_number: Optional[int] = None
    relevance: float = 0.0
    title: Optional[str] = None


@dataclass
class GenerationResult:
    """生成结果"""
    content: str
    sources: List[SourceReference] = field(default_factory=list)

    # 元数据
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

    # 质量指标
    confidence: Optional[float] = None
    faithfulness: Optional[float] = None

    # 流式生成相关
    is_complete: bool = True


@dataclass
class GeneratorConfig(ComponentConfig):
    """生成器配置"""
    # 模型配置
    model_key: str = "claude"
    temperature: float = 0.7
    max_tokens: int = 2048

    # 上下文配置
    max_context_length: int = 8000
    include_sources: bool = True

    # 系统提示
    system_prompt: Optional[str] = None


class BaseGenerator(AsyncComponent[GeneratorConfig, GenerationResult]):
    """
    生成器基类

    负责基于检索结果生成回答，支持:
    - 同步生成
    - 流式生成
    - 来源引用

    设计要点:
    1. 封装 LLM 调用
    2. 构建包含上下文的 prompt
    3. 提取和格式化来源引用
    4. 支持流式输出

    示例:
        @component_registries.generator.register("llm")
        class LLMGenerator(BaseGenerator):
            async def generate(
                self,
                query: str,
                context: List[RetrievalResult],
            ) -> GenerationResult:
                # 调用 LLM 生成回答
                ...
    """

    component_type = ComponentType.GENERATOR

    def __init__(
        self,
        model_key: str = "claude",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
        **kwargs,
    ):
        config = GeneratorConfig(
            model_key=model_key,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            extra=kwargs,
        )
        super().__init__(config)

    @abstractmethod
    async def generate(
        self,
        query: str,
        context: List[RetrievalResult],
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> GenerationResult:
        """
        生成回答

        Args:
            query: 用户问题
            context: 检索到的上下文
            conversation_history: 对话历史

        Returns:
            生成结果
        """
        raise NotImplementedError

    async def generate_stream(
        self,
        query: str,
        context: List[RetrievalResult],
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[GenerationResult]:
        """
        流式生成回答

        Args:
            query: 用户问题
            context: 检索到的上下文
            conversation_history: 对话历史

        Yields:
            生成结果的增量部分
        """
        # 默认实现：一次性返回
        result = await self.generate(query, context, conversation_history)
        yield result

    def build_context(
        self,
        results: List[RetrievalResult],
        max_length: Optional[int] = None,
    ) -> str:
        """
        构建上下文

        将检索结果格式化为 LLM 可用的上下文字符串。
        """
        max_length = max_length or (self.config.max_context_length if self.config else 8000)
        context_parts = []
        current_length = 0

        for i, result in enumerate(results, 1):
            # 格式化单个结果
            part = f"[{i}] {result.content}"
            if result.page_number:
                part = f"[{i}] (第{result.page_number}页) {result.content}"

            part_length = len(part)
            if current_length + part_length > max_length:
                break

            context_parts.append(part)
            current_length += part_length

        return "\n\n".join(context_parts)

    def extract_sources(
        self,
        results: List[RetrievalResult],
    ) -> List[SourceReference]:
        """
        提取来源引用
        """
        sources = []
        for result in results:
            source = SourceReference(
                document_id=result.document_id or "",
                chunk_id=result.chunk_id or "",
                content=result.content[:200] + "..." if len(result.content) > 200 else result.content,
                page_number=result.page_number,
                relevance=result.score,
            )
            sources.append(source)
        return sources

    async def execute(
        self,
        query: str,
        context: List[RetrievalResult],
        **kwargs,
    ) -> GenerationResult:
        """执行生成"""
        return await self.generate(query, context, **kwargs)
