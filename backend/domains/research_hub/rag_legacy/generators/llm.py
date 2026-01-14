"""
LLM 生成器

使用 mcp_core LLM 客户端进行回答生成。
"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from ..base.generator import BaseGenerator, GenerationResult, SourceReference
from ..base.retriever import RetrievalResult
from ..base.reranker import RerankResult
from ..base.registry import component_registries

logger = logging.getLogger(__name__)

# 默认系统提示
DEFAULT_SYSTEM_PROMPT = """你是一个专业的量化研究助手，帮助用户理解和分析量化研究报告。

你的职责:
1. 基于提供的研报内容准确回答用户问题
2. 如果上下文不足以回答问题，请明确说明
3. 回答时引用具体来源，使用 [1]、[2] 等标注
4. 保持专业、准确、简洁的风格

注意:
- 只使用提供的上下文信息回答，不要编造内容
- 如果涉及具体数据或公式，确保准确引用
- 对于复杂问题，可以分步骤解释"""


@component_registries.generator.register("openai")
class LLMGenerator(BaseGenerator):
    """
    LLM 生成器

    使用项目 mcp_core LLM 客户端进行回答生成。
    支持多种 LLM 后端（OpenAI、Claude 等）。

    使用示例:
        generator = LLMGenerator(
            model_key="gpt",
            temperature=0.3,
        )
        result = await generator.generate(query, context)
    """

    def __init__(
        self,
        model_key: str = "gpt",
        model: Optional[str] = None,  # 直接指定模型名称
        temperature: float = 0.3,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        max_context_length: int = 8000,
        include_sources: bool = True,
        **kwargs,
    ):
        super().__init__(
            model_key=model_key,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
            **kwargs,
        )
        self.model = model
        self.max_context_length = max_context_length
        self.include_sources = include_sources
        self._client = None

    async def setup(self) -> None:
        """初始化 LLM 客户端"""
        from domains.mcp_core.llm import get_llm_client

        self._client = get_llm_client()
        logger.info(f"LLM generator initialized with model_key: {self.config.model_key}")

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
            context: 检索到的上下文（可以是 RetrievalResult 或 RerankResult）
            conversation_history: 对话历史

        Returns:
            生成结果
        """
        if self._client is None:
            await self.setup()

        # 构建上下文
        context_text = self._build_context(context)

        # 构建消息
        messages = self._build_messages(query, context_text, conversation_history)

        try:
            # 调用 LLM (返回 str)
            response = await self._client.ainvoke(
                messages=messages,
                model_key=self.config.model_key,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            # 提取来源
            sources = self._extract_sources(context) if self.include_sources else []

            # response 是 str 类型
            content = response if isinstance(response, str) else getattr(response, "content", str(response))

            return GenerationResult(
                content=content,
                sources=sources,
                model=self.model or self.config.model_key,
            )

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return GenerationResult(
                content=f"生成回答时出错: {str(e)}",
                sources=[],
            )

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
        if self._client is None:
            await self.setup()

        # 构建上下文和消息
        context_text = self._build_context(context)
        messages = self._build_messages(query, context_text, conversation_history)

        try:
            # 流式调用
            full_content = ""
            async for chunk in self._client.astream(
                messages=messages,
                model_key=self.config.model_key,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            ):
                if hasattr(chunk, "content") and chunk.content:
                    full_content += chunk.content
                    yield GenerationResult(
                        content=chunk.content,
                        sources=[],
                        is_complete=False,
                    )

            # 最后一次返回完整结果和来源
            sources = self._extract_sources(context) if self.include_sources else []
            yield GenerationResult(
                content=full_content,
                sources=sources,
                model=self.model or self.config.model_key,
                is_complete=True,
            )

        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            yield GenerationResult(
                content=f"生成回答时出错: {str(e)}",
                sources=[],
                is_complete=True,
            )

    def _build_context(self, results: List[RetrievalResult]) -> str:
        """构建上下文字符串"""
        parts = []
        current_length = 0

        for i, result in enumerate(results, 1):
            # 支持 RetrievalResult 和 RerankResult
            if hasattr(result, "chunk"):
                content = result.chunk.content
                page_start = getattr(result.chunk.metadata, "page_start", None)
            else:
                content = result.content
                page_start = getattr(result, "page_number", None)

            # 格式化
            if page_start:
                part = f"[{i}] (第{page_start}页)\n{content}"
            else:
                part = f"[{i}]\n{content}"

            part_length = len(part)
            if current_length + part_length > self.max_context_length:
                break

            parts.append(part)
            current_length += part_length

        return "\n\n---\n\n".join(parts)

    def _build_messages(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        """构建消息列表"""
        messages = [
            {"role": "system", "content": self.config.system_prompt or DEFAULT_SYSTEM_PROMPT},
        ]

        # 添加对话历史
        if conversation_history:
            for msg in conversation_history:
                messages.append(msg)

        # 添加当前问题和上下文
        user_message = f"""请根据以下研报内容回答问题。

## 研报内容

{context}

## 问题

{query}

请基于上述内容回答问题。如果内容不足以回答，请说明。引用来源时使用 [1]、[2] 等标注。"""

        messages.append({"role": "user", "content": user_message})

        return messages

    def _extract_sources(
        self, results: List[RetrievalResult]
    ) -> List[SourceReference]:
        """提取来源引用"""
        sources = []
        for result in results:
            # 支持 RetrievalResult 和 RerankResult
            if hasattr(result, "chunk"):
                chunk = result.chunk
                content = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
                doc_id = getattr(chunk.metadata, "document_id", "") or ""
                chunk_id = chunk.chunk_id or ""
                page_num = getattr(chunk.metadata, "page_start", None)
                score = getattr(result, "rerank_score", None) or getattr(result, "score", 0)
            else:
                content = result.content[:200] + "..." if len(result.content) > 200 else result.content
                doc_id = getattr(result, "document_id", "") or ""
                chunk_id = getattr(result, "chunk_id", "") or ""
                page_num = getattr(result, "page_number", None)
                score = result.score

            sources.append(
                SourceReference(
                    document_id=doc_id,
                    chunk_id=chunk_id,
                    content=content,
                    page_number=page_num,
                    relevance=score,
                )
            )

        return sources


@component_registries.generator.register("anthropic")
class AnthropicGenerator(LLMGenerator):
    """
    Anthropic Claude 生成器

    使用 Claude API 进行回答生成。
    继承自 LLMGenerator，只是默认使用 Claude 模型。
    """

    def __init__(
        self,
        model: str = "claude-3-opus-20240229",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs,
    ):
        super().__init__(
            model_key="claude",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
