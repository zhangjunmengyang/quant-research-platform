"""
ChatBot 服务

提供研报对话功能，管理对话会话和消息。
"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from dataclasses import asdict

from ..core.store import (
    get_conversation_store,
    get_research_store,
    ConversationStore,
)
from ..core.models import Conversation, Message
from ..rag.base.pipeline import PipelineResult
from ..rag.base.generator import GenerationResult
from .pipeline_factory import get_pipeline_factory, PipelineFactory
from ..agents import ResearchChatAgent

logger = logging.getLogger(__name__)


class ChatBotService:
    """
    研报 ChatBot 服务

    功能:
    - 管理对话会话
    - 执行 RAG 流水线
    - 保存对话历史
    - 支持流式响应

    使用示例:
        service = ChatBotService()

        # 创建新对话
        conv = await service.create_conversation()

        # 发送消息
        response = await service.chat(conv.id, "什么是动量因子？")

        # 流式响应
        async for chunk in service.chat_stream(conv.id, "继续解释"):
            print(chunk.content, end="")
    """

    def __init__(
        self,
        pipeline_name: Optional[str] = None,
        database_url: Optional[str] = None,
    ):
        self.pipeline_name = pipeline_name
        self.database_url = database_url
        self._pipeline = None
        self._agent: Optional[ResearchChatAgent] = None
        self._conversation_store: Optional[ConversationStore] = None

    @property
    def conversation_store(self) -> ConversationStore:
        """获取对话存储"""
        if self._conversation_store is None:
            self._conversation_store = get_conversation_store(self.database_url)
        return self._conversation_store

    async def _get_pipeline(self):
        """获取 RAG 流水线"""
        if self._pipeline is None:
            factory = get_pipeline_factory()
            self._pipeline = await factory.get_or_create_pipeline(self.pipeline_name)
        return self._pipeline

    async def _get_agent(self) -> ResearchChatAgent:
        """获取 Agent"""
        if self._agent is None:
            pipeline = await self._get_pipeline()
            self._agent = ResearchChatAgent(pipeline=pipeline)
            await self._agent.setup()
        return self._agent

    # ==================== 对话管理 ====================

    async def create_conversation(
        self,
        title: Optional[str] = None,
        report_id: Optional[int] = None,
    ) -> Conversation:
        """
        创建新对话

        Args:
            title: 对话标题（可选，可后续自动生成）
            report_id: 关联的研报 ID（可选）

        Returns:
            新创建的对话
        """
        conv = Conversation(
            title=title or "新对话",
            report_id=report_id,
        )
        conv_id = self.conversation_store.add(conv)
        conv.id = conv_id
        logger.info(f"Created conversation: {conv_id}")
        return conv

    async def get_conversation(self, conv_id: int) -> Optional[Conversation]:
        """获取对话"""
        return self.conversation_store.get(conv_id)

    async def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        """列出所有对话"""
        return self.conversation_store.get_all(limit=limit, offset=offset)

    async def delete_conversation(self, conv_id: int) -> bool:
        """删除对话"""
        return self.conversation_store.delete(conv_id)

    async def get_messages(
        self,
        conv_id: int,
        limit: int = 100,
    ) -> List[Message]:
        """获取对话消息"""
        return self.conversation_store.get_messages(conv_id, limit=limit)

    # ==================== 对话功能 ====================

    async def chat(
        self,
        conv_id: int,
        message: str,
        report_id: Optional[int] = None,
        model_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        发送消息并获取回复

        Args:
            conv_id: 对话 ID
            message: 用户消息
            report_id: 限制检索的研报 ID（可选）
            model_key: 指定使用的模型（可选）

        Returns:
            包含回复内容和来源的字典
        """
        # 获取对话历史
        history = await self._get_conversation_history(conv_id)

        # 保存用户消息
        user_msg = Message(
            conversation_id=conv_id,
            role="user",
            content=message,
        )
        self.conversation_store.add_message(user_msg)

        # 使用 Agent 执行对话
        agent = await self._get_agent()
        response = await agent.chat(
            query=message,
            conversation_history=history,
            model_key=model_key,
            report_id=report_id,
        )

        # 保存助手回复
        assistant_msg = Message(
            conversation_id=conv_id,
            role="assistant",
            content=response.content,
            sources=self._format_sources(response.sources),
        )
        self.conversation_store.add_message(assistant_msg)

        # 自动更新对话标题（如果是第一条消息）
        if len(history) == 0:
            await self._auto_update_title(conv_id, message)

        return {
            "content": response.content,
            "sources": self._format_sources(response.sources),
            "metadata": response.metadata,
        }

    async def chat_stream(
        self,
        conv_id: int,
        message: str,
        report_id: Optional[int] = None,
        model_key: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式对话

        Args:
            conv_id: 对话 ID
            message: 用户消息
            report_id: 限制检索的研报 ID
            model_key: 指定使用的模型（可选）

        Yields:
            包含增量内容的字典
        """
        # 获取对话历史
        history = await self._get_conversation_history(conv_id)

        # 保存用户消息
        user_msg = Message(
            conversation_id=conv_id,
            role="user",
            content=message,
        )
        self.conversation_store.add_message(user_msg)

        # 使用 Agent 流式执行对话
        agent = await self._get_agent()
        full_content = ""
        sources = []

        async for response in agent.chat_stream(
            query=message,
            conversation_history=history,
            model_key=model_key,
            report_id=report_id,
        ):
            if response.is_complete:
                # 完成响应
                sources = self._format_sources(response.sources)
                yield {
                    "type": "done",
                    "metadata": response.metadata,
                }
            else:
                # 流式片段
                full_content += response.content
                yield {
                    "type": "content",
                    "content": response.content,
                }

        # 保存完整回复
        assistant_msg = Message(
            conversation_id=conv_id,
            role="assistant",
            content=full_content,
            sources=sources,
        )
        self.conversation_store.add_message(assistant_msg)

        # 自动更新对话标题
        if len(history) == 0:
            await self._auto_update_title(conv_id, message)

    async def _get_conversation_history(
        self,
        conv_id: int,
        max_turns: int = 10,
    ) -> List[Dict[str, str]]:
        """获取对话历史（格式化为 LLM 消息格式）"""
        messages = await self.get_messages(conv_id, limit=max_turns * 2)

        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.content,
            })

        return history

    async def _auto_update_title(self, conv_id: int, first_message: str) -> None:
        """自动更新对话标题"""
        # 使用第一条消息的前 50 个字符作为标题
        title = first_message[:50]
        if len(first_message) > 50:
            title += "..."
        self.conversation_store.update_title(conv_id, title)

    def _format_sources(self, sources: List[Any]) -> str:
        """格式化来源为 JSON 字符串"""
        import json

        if not sources:
            return "[]"

        formatted = []
        for source in sources:
            if hasattr(source, "__dict__"):
                formatted.append({
                    "document_id": getattr(source, "document_id", ""),
                    "chunk_id": getattr(source, "chunk_id", ""),
                    "content_preview": getattr(source, "content", "")[:100],
                    "page_number": getattr(source, "page_number", None),
                    "relevance": getattr(source, "relevance", 0),
                })
            else:
                formatted.append(source)

        return json.dumps(formatted, ensure_ascii=False)


# 单例管理
_chatbot_service: Optional[ChatBotService] = None


def get_chatbot_service(
    pipeline_name: Optional[str] = None,
    database_url: Optional[str] = None,
) -> ChatBotService:
    """获取 ChatBot 服务单例"""
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatBotService(
            pipeline_name=pipeline_name,
            database_url=database_url,
        )
    return _chatbot_service
