"""
LLM 客户端

基于 LangChain 提供统一的 LLM 调用接口。
这是一个纯技术封装，不包含业务逻辑。
"""

import time
from typing import Any, AsyncIterator, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    BaseMessageChunk,
    HumanMessage,
    SystemMessage,
    AIMessage,
)

from .config import get_llm_settings, LLMSettings
from ..observability.llm_logger import get_llm_logger


class LLMClient:
    """
    LLM 客户端

    提供简洁的 LLM 调用接口，支持:
    - 配置驱动的模型选择
    - 自动日志记录
    - 运行时参数覆盖
    """

    def __init__(
        self,
        settings: Optional[LLMSettings] = None,
        model_key: Optional[str] = None,
    ):
        """
        初始化 LLM 客户端

        Args:
            settings: LLM 配置，None 则使用全局配置
            model_key: 默认模型 key
        """
        self.settings = settings or get_llm_settings()
        self.default_model_key = model_key or self.settings.default_model
        self._models: Dict[str, BaseChatModel] = {}

    def _create_model(
        self,
        model_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ChatOpenAI:
        """
        创建 LangChain 模型实例

        使用 OpenAI 兼容接口 (通过代理)
        """
        config = self.settings.resolve_config(
            model_key=model_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return ChatOpenAI(
            model=config["model"],
            temperature=config["temperature"],
            openai_api_base=self.settings.api_url,
            openai_api_key=self.settings.api_key,
            timeout=self.settings.timeout,
            extra_body={"max_tokens": config["max_tokens"]},
        )

    def get_model(
        self,
        model_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> BaseChatModel:
        """
        获取模型实例 (带缓存)

        注意: 如果传入 temperature/max_tokens，会创建新实例
        """
        key = model_key or self.default_model_key

        # 如果有覆盖参数，不使用缓存
        if temperature is not None or max_tokens is not None:
            return self._create_model(key, temperature, max_tokens)

        # 缓存模型实例
        if key not in self._models:
            self._models[key] = self._create_model(key)

        return self._models[key]

    async def ainvoke(
        self,
        messages: List[Dict[str, str]],
        model_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        caller: str = "",
        purpose: str = "",
    ) -> str:
        """
        异步调用 LLM

        Args:
            messages: 消息列表 [{"role": "system/user", "content": "..."}]
            model_key: 模型 key
            temperature: 温度参数
            max_tokens: 最大 token 数
            caller: 调用方标识 (用于日志)
            purpose: 调用目的 (用于日志)

        Returns:
            LLM 响应内容 (str)
        """
        model = self.get_model(model_key, temperature, max_tokens)
        lc_messages = self._convert_messages(messages)

        # 获取实际使用的配置
        config = self.settings.resolve_config(model_key, temperature, max_tokens)
        actual_model = config["model"]
        actual_temperature = config["temperature"]
        actual_max_tokens = config["max_tokens"]

        # 从 messages 提取 system_prompt 和 user_prompt
        system_prompt = ""
        user_prompt = ""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system" and not system_prompt:
                system_prompt = content
            elif role == "user":
                user_prompt = content  # 取最后一个 user message

        # 记录请求
        llm_logger = get_llm_logger()
        call_id = llm_logger.log_request(
            model=actual_model,
            messages=messages,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=actual_temperature,
            max_tokens=actual_max_tokens,
            caller=caller,
            purpose=purpose,
            provider="langchain",
        )

        start_time = time.time()

        try:
            response = await model.ainvoke(lc_messages)
            duration_ms = (time.time() - start_time) * 1000

            # 提取 token 使用信息
            usage_metadata = getattr(response, "usage_metadata", None)
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0

            if usage_metadata:
                prompt_tokens = usage_metadata.get("input_tokens", 0)
                completion_tokens = usage_metadata.get("output_tokens", 0)
                total_tokens = usage_metadata.get("total_tokens", 0)

            # 记录响应
            llm_logger.log_response(
                call_id=call_id,
                content=response.content,
                finish_reason=getattr(response, "response_metadata", {}).get(
                    "finish_reason", ""
                ),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                duration_ms=duration_ms,
                success=True,
            )

            return response.content

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            llm_logger.log_response(
                call_id=call_id,
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms,
            )
            raise

    async def astream(
        self,
        messages: List[Dict[str, str]],
        model_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        caller: str = "",
        purpose: str = "",
    ) -> AsyncIterator[BaseMessageChunk]:
        """
        异步流式调用 LLM

        Args:
            messages: 消息列表 [{"role": "system/user", "content": "..."}]
            model_key: 模型 key
            temperature: 温度参数
            max_tokens: 最大 token 数
            caller: 调用方标识 (用于日志)
            purpose: 调用目的 (用于日志)

        Yields:
            LLM 响应的增量 chunk
        """
        model = self.get_model(model_key, temperature, max_tokens)
        lc_messages = self._convert_messages(messages)

        config = self.settings.resolve_config(model_key, temperature, max_tokens)
        actual_model = config["model"]

        # 从 messages 提取 system_prompt 和 user_prompt
        system_prompt = ""
        user_prompt = ""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system" and not system_prompt:
                system_prompt = content
            elif role == "user":
                user_prompt = content

        llm_logger = get_llm_logger()
        call_id = llm_logger.log_request(
            model=actual_model,
            messages=messages,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            caller=caller,
            purpose=purpose,
            provider="langchain",
        )

        start_time = time.time()
        full_content = ""

        try:
            async for chunk in model.astream(lc_messages):
                if hasattr(chunk, "content") and chunk.content:
                    full_content += chunk.content
                yield chunk

            duration_ms = (time.time() - start_time) * 1000

            llm_logger.log_response(
                call_id=call_id,
                content=full_content,
                finish_reason="stop",
                duration_ms=duration_ms,
                success=True,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            llm_logger.log_response(
                call_id=call_id,
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms,
            )
            raise

    def invoke(
        self,
        messages: List[Dict[str, str]],
        model_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        caller: str = "",
        purpose: str = "",
    ) -> str:
        """
        同步调用 LLM

        参数与 ainvoke 相同。
        """
        model = self.get_model(model_key, temperature, max_tokens)
        lc_messages = self._convert_messages(messages)

        config = self.settings.resolve_config(model_key, temperature, max_tokens)
        actual_model = config["model"]

        # 从 messages 提取 system_prompt 和 user_prompt
        system_prompt = ""
        user_prompt = ""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system" and not system_prompt:
                system_prompt = content
            elif role == "user":
                user_prompt = content  # 取最后一个 user message

        llm_logger = get_llm_logger()
        call_id = llm_logger.log_request(
            model=actual_model,
            messages=messages,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            caller=caller,
            purpose=purpose,
            provider="langchain",
        )

        start_time = time.time()

        try:
            response = model.invoke(lc_messages)
            duration_ms = (time.time() - start_time) * 1000

            usage_metadata = getattr(response, "usage_metadata", None)
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0

            if usage_metadata:
                prompt_tokens = usage_metadata.get("input_tokens", 0)
                completion_tokens = usage_metadata.get("output_tokens", 0)
                total_tokens = usage_metadata.get("total_tokens", 0)

            llm_logger.log_response(
                call_id=call_id,
                content=response.content,
                finish_reason=getattr(response, "response_metadata", {}).get(
                    "finish_reason", ""
                ),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                duration_ms=duration_ms,
                success=True,
            )

            return response.content

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            llm_logger.log_response(
                call_id=call_id,
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms,
            )
            raise

    def _convert_messages(
        self,
        messages: List[Dict[str, str]],
    ) -> List[BaseMessage]:
        """转换消息格式: dict -> LangChain Message"""
        result = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                result.append(SystemMessage(content=content))
            elif role == "assistant":
                result.append(AIMessage(content=content))
            else:
                result.append(HumanMessage(content=content))

        return result


# 全局客户端实例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局 LLM 客户端"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def reset_llm_client() -> None:
    """重置 LLM 客户端（用于配置变更后）"""
    global _llm_client
    _llm_client = None
