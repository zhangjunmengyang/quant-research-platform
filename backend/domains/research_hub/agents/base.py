"""
Agent 基类

定义 Agent 的通用接口和行为。

Agent 职责:
- 管理对话流程
- 模型选择和切换
- 调用 RAG Pipeline
- 扩展能力 (工具调用、规划等)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent 配置"""

    model_key: str = "gemini"
    temperature: float = 0.6
    max_tokens: int = 4096
    system_prompt: Optional[str] = None
    enable_rag: bool = True

    # 扩展配置
    extra: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """获取扩展配置"""
        return self.extra.get(key, default)


@dataclass
class AgentResponse:
    """Agent 响应"""

    content: str
    sources: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_complete: bool = True

    @classmethod
    def streaming(cls, content: str, **metadata) -> "AgentResponse":
        """创建流式响应片段"""
        return cls(
            content=content,
            sources=[],
            metadata=metadata,
            is_complete=False,
        )

    @classmethod
    def complete(
        cls,
        content: str,
        sources: Optional[List[Any]] = None,
        **metadata,
    ) -> "AgentResponse":
        """创建完整响应"""
        return cls(
            content=content,
            sources=sources or [],
            metadata=metadata,
            is_complete=True,
        )


class BaseAgent(ABC):
    """
    Agent 基类

    所有 Agent 继承此类实现具体场景。

    设计要点:
    1. 与 RAG Pipeline 解耦，通过依赖注入使用
    2. 支持动态模型切换
    3. 提供流式和同步两种对话模式
    4. 预留扩展点用于工具调用、规划等

    使用示例:
        agent = ResearchChatAgent(pipeline=pipeline)
        response = await agent.chat(
            query="什么是动量因子?",
            model_key="claude",
            report_id=123,
        )
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        **kwargs,
    ):
        self.config = config or AgentConfig(**kwargs)
        self._initialized = False

    async def setup(self) -> None:
        """初始化 Agent 资源"""
        if self._initialized:
            return
        await self._do_setup()
        self._initialized = True
        logger.debug(f"{self.__class__.__name__} initialized")

    async def _do_setup(self) -> None:
        """子类实现的初始化逻辑"""
        pass

    async def cleanup(self) -> None:
        """清理 Agent 资源"""
        if not self._initialized:
            return
        await self._do_cleanup()
        self._initialized = False

    async def _do_cleanup(self) -> None:
        """子类实现的清理逻辑"""
        pass

    @abstractmethod
    async def chat(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        model_key: Optional[str] = None,
        **kwargs,
    ) -> AgentResponse:
        """
        同步对话

        Args:
            query: 用户问题
            conversation_history: 对话历史
            model_key: 指定使用的模型 (覆盖默认配置)
            **kwargs: 其他参数 (如 report_id)

        Returns:
            Agent 响应
        """
        raise NotImplementedError

    @abstractmethod
    async def chat_stream(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        model_key: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[AgentResponse]:
        """
        流式对话

        Args:
            query: 用户问题
            conversation_history: 对话历史
            model_key: 指定使用的模型 (覆盖默认配置)
            **kwargs: 其他参数 (如 report_id)

        Yields:
            Agent 响应片段
        """
        raise NotImplementedError

    def get_effective_model(self, model_key: Optional[str] = None) -> str:
        """获取实际使用的模型 key"""
        return model_key or self.config.model_key

    @property
    def name(self) -> str:
        """Agent 名称"""
        return self.__class__.__name__

    def __repr__(self) -> str:
        return f"{self.name}(model={self.config.model_key}, initialized={self._initialized})"
