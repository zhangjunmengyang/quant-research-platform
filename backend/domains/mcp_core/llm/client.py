"""
LLM 客户端

基于 LangChain 提供统一的 LLM 调用接口。
这是一个纯技术封装，不包含业务逻辑。
"""

import time
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    BaseMessageChunk,
    HumanMessage,
    SystemMessage,
    AIMessage,
)

from .compatible import ChatOpenAICompatible
from .config import get_llm_settings, LLMSettings
from ..observability.llm_logger import get_llm_logger

try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession
    from curl_cffi import requests as curl_requests
except ImportError:  # pragma: no cover - optional dependency
    CurlAsyncSession = None
    curl_requests = None


class _CurlCffiAsyncTransport(httpx.AsyncBaseTransport):
    """Async httpx transport backed by curl_cffi (BoringSSL).

    Python 3.11.0 bundles OpenSSL 1.1.1 which cannot TLS-handshake with some
    relays. curl_cffi ships its own BoringSSL, bypassing the limitation.
    """

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if CurlAsyncSession is None:
            raise RuntimeError("http_transport=curl_cffi 但未安装 curl-cffi")
        async with CurlAsyncSession() as s:
            r = await s.request(
                method=request.method.decode() if isinstance(request.method, bytes) else request.method,
                url=str(request.url),
                headers=dict(request.headers),
                data=request.content,
                timeout=120,
            )
            return httpx.Response(
                status_code=r.status_code,
                headers=list(r.headers.items()),
                content=r.content,
                request=request,
            )


class _CurlCffiSyncTransport(httpx.BaseTransport):
    """Sync httpx transport backed by curl_cffi."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if curl_requests is None:
            raise RuntimeError("http_transport=curl_cffi 但未安装 curl-cffi")
        r = curl_requests.request(
            method=request.method,
            url=str(request.url),
            headers=dict(request.headers),
            data=request.content,
            timeout=120,
        )
        return httpx.Response(
            status_code=r.status_code,
            headers=list(r.headers.items()),
            content=r.content,
            request=request,
        )


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

    @staticmethod
    def _build_transport_clients(http_transport: str) -> Dict[str, Any]:
        """按配置构建可选 HTTP 客户端。"""
        if http_transport == "default":
            return {}

        if http_transport != "curl_cffi":
            raise ValueError(f"不支持的 http_transport: {http_transport}")

        if CurlAsyncSession is None or curl_requests is None:
            raise RuntimeError(
                "模型配置要求使用 curl_cffi transport，但当前环境未安装 curl-cffi"
            )

        return {
            "http_client": httpx.Client(transport=_CurlCffiSyncTransport()),
            "http_async_client": httpx.AsyncClient(transport=_CurlCffiAsyncTransport()),
        }

    def _create_model(
        self,
        model_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> BaseChatModel:
        """
        创建 LangChain 模型实例

        根据配置选择:
        - openai_compatible=True: 使用 ChatOpenAICompatible (兼容不支持新 API 参数的代理)
        - openai_compatible=False: 使用标准 ChatOpenAI
        """
        config = self.settings.resolve_config(
            model_key=model_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        model_class = (
            ChatOpenAICompatible if config.get("openai_compatible") else ChatOpenAI
        )

        api_url = config.get("api_url") or self.settings.api_url
        api_key = config.get("api_key") or self.settings.api_key

        extra = {"max_tokens": config["max_tokens"]}
        if config.get("extra_body"):
            extra.update(config["extra_body"])

        kwargs: Dict[str, Any] = dict(
            model=config["model"],
            temperature=config["temperature"],
            openai_api_base=api_url,
            openai_api_key=api_key,
            timeout=self.settings.timeout,
            extra_body=extra,
        )

        kwargs.update(
            self._build_transport_clients(config.get("http_transport", "default"))
        )

        return model_class(**kwargs)

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

        config = self.settings.resolve_config(model_key, temperature, max_tokens)
        system_prompt, user_prompt = self._extract_prompts(messages)

        llm_logger = get_llm_logger()
        call_id = llm_logger.log_request(
            model=config["model"],
            messages=messages,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            caller=caller,
            purpose=purpose,
            provider=config.get("provider", "openai"),
        )

        start_time = time.time()

        try:
            response = await model.ainvoke(lc_messages)
            duration_ms = (time.time() - start_time) * 1000
            prompt_tokens, completion_tokens, total_tokens = self._extract_token_usage(response)

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
        system_prompt, user_prompt = self._extract_prompts(messages)

        llm_logger = get_llm_logger()
        call_id = llm_logger.log_request(
            model=config["model"],
            messages=messages,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            caller=caller,
            purpose=purpose,
            provider=config.get("provider", "openai"),
        )

        start_time = time.time()
        full_content = ""
        usage_metadata = None

        try:
            async for chunk in model.astream(lc_messages):
                if hasattr(chunk, "content") and chunk.content:
                    full_content += chunk.content
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    usage_metadata = chunk.usage_metadata
                yield chunk

            duration_ms = (time.time() - start_time) * 1000
            prompt_tokens, completion_tokens, total_tokens = (
                (usage_metadata.get("input_tokens", 0),
                 usage_metadata.get("output_tokens", 0),
                 usage_metadata.get("total_tokens", 0))
                if usage_metadata else (0, 0, 0)
            )

            llm_logger.log_response(
                call_id=call_id,
                content=full_content,
                finish_reason="stop",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
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
        system_prompt, user_prompt = self._extract_prompts(messages)

        llm_logger = get_llm_logger()
        call_id = llm_logger.log_request(
            model=config["model"],
            messages=messages,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            caller=caller,
            purpose=purpose,
            provider=config.get("provider", "openai"),
        )

        start_time = time.time()

        try:
            response = model.invoke(lc_messages)
            duration_ms = (time.time() - start_time) * 1000
            prompt_tokens, completion_tokens, total_tokens = self._extract_token_usage(response)

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

    @staticmethod
    def _extract_prompts(
        messages: List[Dict[str, str]],
    ) -> tuple[str, str]:
        """
        从消息列表提取 system 和 user prompt

        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = ""
        user_prompt = ""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system" and not system_prompt:
                system_prompt = content
            elif role == "user":
                user_prompt = content  # 取最后一个 user message
        return system_prompt, user_prompt

    @staticmethod
    def _extract_token_usage(response) -> tuple[int, int, int]:
        """
        从响应对象提取 token 使用信息

        Returns:
            (prompt_tokens, completion_tokens, total_tokens)
        """
        usage_metadata = getattr(response, "usage_metadata", None)
        if not usage_metadata:
            return 0, 0, 0
        return (
            usage_metadata.get("input_tokens", 0),
            usage_metadata.get("output_tokens", 0),
            usage_metadata.get("total_tokens", 0),
        )


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
