"""
OpenAI 兼容模式的 ChatOpenAI 扩展

用于不支持新版 OpenAI API 参数的代理服务:
1. 将 max_completion_tokens 转换回 max_tokens
2. 支持 Gemini 的 thought_signature 传递

参考:
- https://github.com/langchain-ai/langchain/issues/30113
- https://github.com/langchain-ai/langchain/issues/34056
"""

from collections.abc import Iterator
from typing import Any

import openai
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI


class ChatOpenAICompatible(ChatOpenAI):
    """兼容自定义 OpenAI 端点的 ChatOpenAI

    扩展功能:
    1. 将 max_completion_tokens 转换回 max_tokens，兼容不支持新参数的 API
    2. 支持 Gemini 的 thought_signature 传递
    """

    def _get_request_payload(
        self,
        input_: LanguageModelInput,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        # 先获取原始消息（在转换前）
        messages = self._convert_input(input_).to_messages()

        payload = super()._get_request_payload(input_, stop=stop, **kwargs)

        # 将 max_completion_tokens 转换回 max_tokens，兼容不支持新参数的 API
        if "max_completion_tokens" in payload:
            payload["max_tokens"] = payload.pop("max_completion_tokens")

        # 恢复 Gemini thought_signature 到 tool_calls
        self._restore_thought_signatures(payload, messages)
        return payload

    def _restore_thought_signatures(
        self, payload: dict, original_messages: list[BaseMessage]
    ) -> None:
        """从 additional_kwargs 恢复 thought_signature 到 tool_calls

        Gemini 的 thinking 模式要求在后续请求中传回 thought_signature。
        LangChain 标准转换会丢失 extra_content 字段，我们需要从原始消息中恢复。

        Args:
            payload: 已转换的请求 payload
            original_messages: 转换前的原始 LangChain 消息列表
        """
        payload_messages = payload.get("messages", [])

        # 建立原始消息的索引映射：找出哪些是 AIMessage 且有 _raw_tool_calls
        ai_msg_raw_tool_calls = {}
        for i, msg in enumerate(original_messages):
            if isinstance(msg, (AIMessage, AIMessageChunk)):
                raw_tool_calls = msg.additional_kwargs.get("_raw_tool_calls")
                if raw_tool_calls:
                    ai_msg_raw_tool_calls[i] = raw_tool_calls

        if not ai_msg_raw_tool_calls:
            return

        # 遍历 payload 中的消息，恢复 extra_content
        for i, msg_dict in enumerate(payload_messages):
            if msg_dict.get("role") != "assistant":
                continue

            tool_calls = msg_dict.get("tool_calls")
            if not tool_calls:
                continue

            # 尝试从对应的原始消息获取 _raw_tool_calls
            raw_tool_calls = ai_msg_raw_tool_calls.get(i)
            if not raw_tool_calls:
                continue

            # 建立 id -> extra_content 的映射
            id_to_extra = {}
            for raw_tc in raw_tool_calls:
                tc_id = raw_tc.get("id")
                extra_content = raw_tc.get("extra_content")
                if tc_id and extra_content:
                    id_to_extra[tc_id] = extra_content

            # 恢复 extra_content 到 tool_calls
            for tc in tool_calls:
                tc_id = tc.get("id")
                if tc_id and tc_id in id_to_extra:
                    tc["extra_content"] = id_to_extra[tc_id]

    def _create_chat_result(
        self,
        response: dict | openai.BaseModel,
        generation_info: dict | None = None,
    ) -> ChatResult:
        """重写结果创建，保存原始 tool_calls 用于 thought_signature 传递"""
        result = super()._create_chat_result(response, generation_info)

        # 从原始响应中提取 tool_calls（包含 extra_content）
        response_dict = (
            response if isinstance(response, dict) else response.model_dump()
        )

        for i, choice in enumerate(response_dict.get("choices", [])):
            raw_tool_calls = choice.get("message", {}).get("tool_calls")
            if not raw_tool_calls:
                continue

            # 检查是否包含 extra_content（Gemini thought_signature）
            has_extra = any(tc.get("extra_content") for tc in raw_tool_calls)
            if has_extra and i < len(result.generations):
                msg = result.generations[i].message
                if isinstance(msg, AIMessage):
                    msg.additional_kwargs["_raw_tool_calls"] = raw_tool_calls

        return result

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        """重写 chunk 转换，保存原始 tool_calls 用于 thought_signature 传递"""
        result = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )

        if result is None:
            return None

        # 从原始 chunk 中提取 tool_calls（包含 extra_content）
        choices = chunk.get("choices", [])
        if not choices:
            return result

        delta = choices[0].get("delta", {})
        raw_tool_calls = delta.get("tool_calls") or []

        if not raw_tool_calls:
            return result

        # 检查是否有 extra_content
        has_extra = any(tc.get("extra_content") for tc in raw_tool_calls)
        if has_extra:
            msg = result.message
            if isinstance(msg, AIMessageChunk):
                # 保存原始 tool_calls 到 additional_kwargs
                msg.additional_kwargs["_raw_tool_calls"] = raw_tool_calls

        return result

    def _stream(self, *args: Any, **kwargs: Any) -> Iterator[ChatGenerationChunk]:
        """重写流式响应，累积并保存原始 tool_calls"""
        accumulated_tool_calls: dict[int, dict] = {}  # index -> tool_call
        last_chunk: ChatGenerationChunk | None = None

        for chunk in super()._stream(*args, **kwargs):
            # 累积 tool_calls（流式响应是增量的）
            self._accumulate_tool_calls(chunk, accumulated_tool_calls)
            last_chunk = chunk
            yield chunk

        # 流结束后，把累积的 tool_calls 保存到最后一个 chunk
        # 注意：这里需要确保 AIMessageChunk 的 + 操作能正确合并 additional_kwargs
        if last_chunk and accumulated_tool_calls:
            has_extra = any(
                tc.get("extra_content") for tc in accumulated_tool_calls.values()
            )
            if has_extra:
                msg = last_chunk.message
                if isinstance(msg, AIMessageChunk):
                    msg.additional_kwargs["_raw_tool_calls"] = list(
                        accumulated_tool_calls.values()
                    )

    def _accumulate_tool_calls(
        self, chunk: ChatGenerationChunk, accumulated: dict[int, dict]
    ) -> None:
        """累积流式响应中的 tool_calls"""
        msg = chunk.message
        if not isinstance(msg, AIMessageChunk):
            return

        # 从 _raw_tool_calls 获取原始数据（由 _convert_chunk_to_generation_chunk 保存）
        raw_tool_calls = msg.additional_kwargs.get("_raw_tool_calls", [])
        for tc in raw_tool_calls:
            index = tc.get("index", 0)
            if index not in accumulated:
                accumulated[index] = {
                    "id": None,
                    "function": {"name": "", "arguments": ""},
                }

            # 累积字段
            if tc.get("id"):
                accumulated[index]["id"] = tc["id"]
            if tc.get("function", {}).get("name"):
                accumulated[index]["function"]["name"] = tc["function"]["name"]
            if tc.get("function", {}).get("arguments"):
                accumulated[index]["function"]["arguments"] += tc["function"][
                    "arguments"
                ]
            if tc.get("extra_content"):
                accumulated[index]["extra_content"] = tc["extra_content"]
