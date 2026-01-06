"""
RAG 组件基类

所有 RAG 组件的基础抽象，定义了:
- 组件生命周期管理
- 配置验证
- 结果标准化
- Agentic RAG 扩展点
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, TypeVar
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ComponentType(Enum):
    """组件类型"""
    PARSER = "parser"
    CHUNKER = "chunker"
    EMBEDDER = "embedder"
    VECTOR_STORE = "vector_store"
    RETRIEVER = "retriever"
    RERANKER = "reranker"
    GENERATOR = "generator"
    PIPELINE = "pipeline"
    # Agentic RAG 扩展
    AGENT = "agent"
    TOOL = "tool"
    PLANNER = "planner"


@dataclass
class ComponentConfig:
    """组件配置基类"""
    type: str = ""  # 组件类型标识符
    enabled: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """获取额外配置项"""
        return self.extra.get(key, default)


@dataclass
class ComponentResult:
    """组件执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any = None, **metadata) -> "ComponentResult":
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, **metadata) -> "ComponentResult":
        return cls(success=False, error=error, metadata=metadata)


ConfigT = TypeVar("ConfigT", bound=ComponentConfig)
ResultT = TypeVar("ResultT")


class BaseComponent(ABC, Generic[ConfigT, ResultT]):
    """
    RAG 组件基类

    所有 RAG 组件（Parser, Chunker, Embedder 等）都继承自此类。

    设计要点:
    1. 配置驱动: 通过 config 对象初始化
    2. 生命周期: setup() -> execute() -> cleanup()
    3. 可观测性: 内置日志和指标采集点
    4. Agentic 扩展: 预留 agent_context 用于 Agent 驱动的 RAG

    示例:
        @parser_registry.register("mineru")
        class MinerUParser(BaseParser):
            def __init__(self, model: str = "MinerU2.5"):
                self.model = model

            async def parse(self, file_path: str) -> ParsedDocument:
                ...
    """

    component_type: ComponentType = ComponentType.PIPELINE

    def __init__(self, config: Optional[ConfigT] = None):
        self.config = config or self._default_config()
        self._initialized = False
        self._agent_context: Optional[Dict[str, Any]] = None

    def _default_config(self) -> ConfigT:
        """返回默认配置，子类可覆盖"""
        return ComponentConfig()  # type: ignore

    async def setup(self) -> None:
        """
        初始化组件资源

        在首次使用前调用，用于:
        - 加载模型
        - 建立连接
        - 预热缓存
        """
        if self._initialized:
            return
        await self._do_setup()
        self._initialized = True
        logger.debug(f"{self.__class__.__name__} initialized")

    async def _do_setup(self) -> None:
        """子类实现的初始化逻辑"""
        pass

    async def cleanup(self) -> None:
        """
        清理组件资源

        用于:
        - 释放模型内存
        - 关闭连接
        - 清理临时文件
        """
        if not self._initialized:
            return
        await self._do_cleanup()
        self._initialized = False
        logger.debug(f"{self.__class__.__name__} cleaned up")

    async def _do_cleanup(self) -> None:
        """子类实现的清理逻辑"""
        pass

    def set_agent_context(self, context: Dict[str, Any]) -> None:
        """
        设置 Agent 上下文

        用于 Agentic RAG 场景，Agent 可以通过上下文:
        - 传递全局状态
        - 控制组件行为
        - 实现动态决策

        Args:
            context: Agent 上下文信息，可能包含:
                - conversation_history: 对话历史
                - user_intent: 用户意图
                - retrieval_feedback: 检索反馈
                - tool_results: 工具调用结果
        """
        self._agent_context = context

    def get_agent_context(self) -> Optional[Dict[str, Any]]:
        """获取 Agent 上下文"""
        return self._agent_context

    @property
    def name(self) -> str:
        """组件名称"""
        return self.__class__.__name__

    def __repr__(self) -> str:
        return f"{self.name}(initialized={self._initialized})"


class AsyncComponent(BaseComponent[ConfigT, ResultT]):
    """
    异步组件基类

    扩展 BaseComponent，提供异步执行支持。
    大多数 RAG 组件应该继承此类。
    """

    @abstractmethod
    async def execute(self, *args, **kwargs) -> ResultT:
        """
        执行组件逻辑

        子类必须实现此方法。
        """
        raise NotImplementedError


class SyncComponent(BaseComponent[ConfigT, ResultT]):
    """
    同步组件基类

    用于不需要异步的场景，如简单的文本处理。
    """

    @abstractmethod
    def execute(self, *args, **kwargs) -> ResultT:
        """
        执行组件逻辑

        子类必须实现此方法。
        """
        raise NotImplementedError
