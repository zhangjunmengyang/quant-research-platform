"""
日志存储模块

生产环境使用 StdoutStorage，日志输出到 stdout。
开发环境保留 MemoryStorage 用于测试。
"""

import os
import threading
from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime
from typing import Any

from ..logging import get_logger
from .models import (
    CallStatus,
    LLMCallRecord,
    MCPRequestRecord,
    SessionRecord,
    SessionStatus,
    ToolCallRecord,
)

# 结构化日志器 - 使用 mcp_core.logging 模块以确保配置一致性
logger = get_logger(__name__)


class LogStorage(ABC):
    """日志存储抽象基类"""

    @abstractmethod
    def save_llm_call(self, record: LLMCallRecord) -> None:
        """保存 LLM 调用记录"""
        pass

    @abstractmethod
    def save_tool_call(self, record: ToolCallRecord) -> None:
        """保存工具调用记录"""
        pass

    @abstractmethod
    def save_session(self, record: SessionRecord) -> None:
        """保存会话记录"""
        pass

    @abstractmethod
    def save_mcp_request(self, record: MCPRequestRecord) -> None:
        """保存 MCP 请求记录"""
        pass

    # 查询方法 - 在 StdoutStorage 中返回空
    def get_llm_call(self, call_id: str) -> LLMCallRecord | None:
        return None

    def get_tool_call(self, call_id: str) -> ToolCallRecord | None:
        return None

    def get_session(self, session_id: str) -> SessionRecord | None:
        return None

    def get_mcp_request(self, request_id: str) -> MCPRequestRecord | None:
        return None

    def query_llm_calls(self, **kwargs) -> list[LLMCallRecord]:
        return []

    def query_tool_calls(self, **kwargs) -> list[ToolCallRecord]:
        return []

    def query_mcp_requests(self, **kwargs) -> list[MCPRequestRecord]:
        return []

    def get_stats(self, **kwargs) -> dict[str, Any]:
        return {"message": "请使用日志查询接口"}


class StdoutStorage(LogStorage):
    """
    标准输出存储

    将日志以 JSON 格式输出到 stdout。
    这是生产环境的默认存储方式。

    日志格式设计:
    - 每条日志包含 log_type 字段标识类型 (llm_call, tool_call, session, mcp_request)
    - 包含完整的追踪信息 (trace_id, session_id, call_id)
    - 包含业务指标 (tokens, cost, duration_ms)
    """

    def __init__(self, console_output: bool = True):
        """
        Args:
            console_output: 是否输出到控制台（生产环境应为 True）
        """
        self.console_output = console_output
        self._log = get_logger("observability.storage")

    def _emit_log(self, log_type: str, data: dict[str, Any]) -> None:
        """输出结构化日志"""
        if not self.console_output:
            return

        # 使用 structlog 输出，自动处理 JSON 格式
        self._log.info(
            log_type,
            **data
        )

    def save_llm_call(self, record: LLMCallRecord) -> None:
        """
        保存 LLM 调用记录到 stdout

        日志结构以"任务"为中心，包含完整的上下文信息：
        - 任务上下文：workflow, factor_name, field
        - 完整消息：system_prompt, user_prompt
        - 完整响应：response_content
        - 性能指标：tokens, duration, cost
        """
        req = record.request
        resp = record.response

        # 从 purpose 解析任务信息 (格式: "fill_description", "review_style" 等)
        # workflow: fill(字段填充), review(审核)
        # field: style, formula, description, analysis, llm_score 等
        workflow = ""
        field = ""
        if req.purpose:
            parts = req.purpose.split("_", 1)
            if len(parts) == 2:
                workflow = parts[0]  # fill, review
                field = parts[1]    # style, formula, description, analysis, llm_score 等
            else:
                workflow = req.purpose

        # 从 extra_params 获取更多上下文
        factor_name = req.extra_params.get("factor_name", "") if req.extra_params else ""

        # 构建任务中心的日志数据
        data = {
            # 任务标识
            "call_id": req.call_id,
            "trace_id": req.trace_id,
            "session_id": req.session_id,

            # 任务上下文（用户最关心的）
            "workflow": workflow,           # 什么流程：fill/review/analysis
            "factor_name": factor_name,     # 哪个因子
            "field": field,                 # 什么字段

            # 模型信息
            "model": req.model,
            "provider": req.provider,
            "caller": req.caller,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,

            # 完整消息内容（AI 应用核心）
            "system_prompt": req.system_prompt,
            "user_prompt": req.user_prompt,

            # 时间戳
            "request_timestamp": req.timestamp.isoformat(),
        }

        if resp:
            # 响应内容（完整保存）
            data["response_content"] = resp.content

            # 响应元数据
            data.update({
                "response_timestamp": resp.timestamp.isoformat(),
                "status": resp.status.value,
                "duration_ms": resp.duration_ms,
                "finish_reason": resp.finish_reason,
            })

            # Token 统计
            if resp.usage:
                data["input_tokens"] = resp.usage.prompt_tokens
                data["output_tokens"] = resp.usage.completion_tokens
                data["total_tokens"] = resp.usage.total_tokens

                # 计算成本
                cost = self._estimate_cost(
                    req.model,
                    resp.usage.prompt_tokens,
                    resp.usage.completion_tokens
                )
                data["cost"] = cost

            # 错误信息
            if resp.error_message:
                data["error_message"] = resp.error_message
                data["error_type"] = resp.error_type

        self._emit_log("llm_call", data)

    def save_tool_call(self, record: ToolCallRecord) -> None:
        """保存工具调用记录到 stdout"""
        req = record.request
        resp = record.response

        data = {
            "call_id": req.call_id,
            "trace_id": req.trace_id,
            "llm_call_id": req.llm_call_id,
            "tool_name": req.tool_name,
            "tool_version": req.tool_version,
            "request_timestamp": req.timestamp.isoformat(),
            "argument_keys": list(req.arguments.keys()) if req.arguments else [],
        }

        if resp:
            data.update({
                "response_timestamp": resp.timestamp.isoformat(),
                "status": resp.status.value,
                "duration_ms": resp.duration_ms,
                "result_type": resp.result_type,
                "result_summary": resp.result_summary[:200] if resp.result_summary else "",
            })

            if resp.error_message:
                data["error_message"] = resp.error_message
                data["error_type"] = resp.error_type

        self._emit_log("tool_call", data)

    def save_session(self, record: SessionRecord) -> None:
        """保存会话记录到 stdout"""
        data = {
            "session_id": record.session_id,
            "start_time": record.start_time.isoformat(),
            "status": record.status.value,
            "total_llm_calls": record.total_llm_calls,
            "total_tool_calls": record.total_tool_calls,
            "total_tokens": record.total_tokens,
            "total_cost": record.total_cost,
            "metadata": record.metadata,
        }

        if record.end_time:
            data["end_time"] = record.end_time.isoformat()
            data["duration_seconds"] = (record.end_time - record.start_time).total_seconds()

        if record.error_message:
            data["error_message"] = record.error_message

        self._emit_log("session", data)

    def save_mcp_request(self, record: MCPRequestRecord) -> None:
        """保存 MCP 请求记录到 stdout（包含完整排查信息）"""
        data = {
            "request_id": record.request_id,
            "timestamp": record.timestamp.isoformat(),
            "server_name": record.server_name,
            "server_port": record.server_port,
            "client_ip": record.client_ip,
            "client_name": record.client_name,
            "method": record.method,
            "tool_name": record.tool_name,
            "resource_uri": record.resource_uri,
            "status": record.status.value if record.status else "pending",
            "duration_ms": record.duration_ms,
            "response_size": record.response_size,
            "response_summary": record.response_summary,
            "trace_id": record.trace_id,
            "session_id": record.session_id,
        }

        # 工具入参（排查必需）
        if record.tool_arguments:
            data["tool_arguments"] = record.tool_arguments

        # 响应数据（排查必需）
        if record.response_data:
            data["response_data"] = record.response_data

        if record.error_code:
            data["error_code"] = record.error_code
        if record.error_message:
            data["error_message"] = record.error_message

        self._emit_log("mcp_request", data)

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """估算 LLM 调用成本"""
        # Token 价格 (USD per 1K tokens)
        prices = {
            # OpenAI
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            # Anthropic
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
            # DeepSeek
            "deepseek-chat": {"input": 0.00014, "output": 0.00028},
            "deepseek-coder": {"input": 0.00014, "output": 0.00028},
        }

        # 查找匹配的价格
        price = None
        model_lower = model.lower()
        for key, val in prices.items():
            if key in model_lower:
                price = val
                break

        if not price:
            price = {"input": 0.001, "output": 0.002}  # 默认价格

        cost = (input_tokens * price["input"] + output_tokens * price["output"]) / 1000
        return round(cost, 6)


class MemoryStorage(LogStorage):
    """内存存储（适合测试和开发）"""

    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self._llm_calls: deque = deque(maxlen=max_records)
        self._tool_calls: deque = deque(maxlen=max_records)
        self._mcp_requests: deque = deque(maxlen=max_records)
        self._sessions: dict[str, SessionRecord] = {}
        self._llm_index: dict[str, LLMCallRecord] = {}
        self._tool_index: dict[str, ToolCallRecord] = {}
        self._mcp_index: dict[str, MCPRequestRecord] = {}
        self._lock = threading.Lock()

    def save_llm_call(self, record: LLMCallRecord) -> None:
        with self._lock:
            self._llm_calls.append(record)
            self._llm_index[record.request.call_id] = record

    def save_tool_call(self, record: ToolCallRecord) -> None:
        with self._lock:
            self._tool_calls.append(record)
            self._tool_index[record.request.call_id] = record

    def save_session(self, record: SessionRecord) -> None:
        with self._lock:
            self._sessions[record.session_id] = record

    def save_mcp_request(self, record: MCPRequestRecord) -> None:
        with self._lock:
            self._mcp_requests.append(record)
            self._mcp_index[record.request_id] = record

    def get_llm_call(self, call_id: str) -> LLMCallRecord | None:
        return self._llm_index.get(call_id)

    def get_tool_call(self, call_id: str) -> ToolCallRecord | None:
        return self._tool_index.get(call_id)

    def get_session(self, session_id: str) -> SessionRecord | None:
        return self._sessions.get(session_id)

    def get_mcp_request(self, request_id: str) -> MCPRequestRecord | None:
        return self._mcp_index.get(request_id)

    def query_llm_calls(
        self,
        trace_id: str | None = None,
        session_id: str | None = None,
        model: str | None = None,
        caller: str | None = None,
        purpose: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: CallStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LLMCallRecord]:
        results = []
        for record in self._llm_calls:
            if trace_id and record.request.trace_id != trace_id:
                continue
            if session_id and record.request.session_id != session_id:
                continue
            if model and record.request.model != model:
                continue
            if caller and record.request.caller != caller:
                continue
            if purpose and record.request.purpose != purpose:
                continue
            if start_time and record.request.timestamp < start_time:
                continue
            if end_time and record.request.timestamp > end_time:
                continue
            if status and record.response and record.response.status != status:
                continue
            results.append(record)

        return results[offset:offset + limit]

    def query_tool_calls(
        self,
        trace_id: str | None = None,
        llm_call_id: str | None = None,
        tool_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: CallStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ToolCallRecord]:
        results = []
        for record in self._tool_calls:
            if trace_id and record.request.trace_id != trace_id:
                continue
            if llm_call_id and record.request.llm_call_id != llm_call_id:
                continue
            if tool_name and record.request.tool_name != tool_name:
                continue
            if start_time and record.request.timestamp < start_time:
                continue
            if end_time and record.request.timestamp > end_time:
                continue
            if status and record.response and record.response.status != status:
                continue
            results.append(record)

        return results[offset:offset + limit]

    def query_mcp_requests(
        self,
        server_name: str | None = None,
        method: str | None = None,
        tool_name: str | None = None,
        client_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: CallStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MCPRequestRecord]:
        results = []
        for record in self._mcp_requests:
            if server_name and record.server_name != server_name:
                continue
            if method and record.method != method:
                continue
            if tool_name and record.tool_name != tool_name:
                continue
            if client_name and record.client_name != client_name:
                continue
            if start_time and record.timestamp < start_time:
                continue
            if end_time and record.timestamp > end_time:
                continue
            if status and record.status != status:
                continue
            results.append(record)

        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results[offset:offset + limit]

    def get_stats(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        llm_calls = list(self._llm_calls)
        if start_time:
            llm_calls = [r for r in llm_calls if r.request.timestamp >= start_time]
        if end_time:
            llm_calls = [r for r in llm_calls if r.request.timestamp <= end_time]

        total_tokens = sum(
            r.response.usage.total_tokens
            for r in llm_calls
            if r.response and r.response.usage
        )

        success_count = sum(1 for r in llm_calls if r.success)

        mcp_requests = list(self._mcp_requests)
        if start_time:
            mcp_requests = [r for r in mcp_requests if r.timestamp >= start_time]
        if end_time:
            mcp_requests = [r for r in mcp_requests if r.timestamp <= end_time]

        mcp_success = sum(1 for r in mcp_requests if r.status == CallStatus.SUCCESS)

        return {
            "llm_calls": {
                "total": len(llm_calls),
                "success_count": success_count,
                "error_count": len(llm_calls) - success_count,
                "total_tokens": total_tokens,
            },
            "tool_calls": {
                "total": len(self._tool_calls),
            },
            "mcp_requests": {
                "total": len(mcp_requests),
                "success_count": mcp_success,
                "error_count": len(mcp_requests) - mcp_success,
            },
            "active_sessions": sum(
                1 for s in self._sessions.values()
                if s.status == SessionStatus.RUNNING
            ),
        }


# 默认存储实例
_default_storage: LogStorage | None = None


def get_log_storage(
    storage_type: str | None = None,
    **kwargs
) -> LogStorage:
    """
    获取日志存储实例

    Args:
        storage_type: 存储类型
            - "stdout": 标准输出（生产环境默认）
            - "memory": 内存存储（测试用）
            - None: 根据环境自动选择
        **kwargs: 存储配置参数

    Returns:
        LogStorage 实例
    """
    global _default_storage

    if _default_storage is None:
        # 自动选择存储类型
        if storage_type is None:
            # 根据环境变量决定
            env = os.environ.get("LOG_STORAGE", "stdout")
            storage_type = env

        if storage_type == "memory":
            _default_storage = MemoryStorage(**kwargs)
        else:
            # 默认使用 StdoutStorage
            _default_storage = StdoutStorage(**kwargs)

    return _default_storage


def reset_storage():
    """重置存储实例（主要用于测试）"""
    global _default_storage
    _default_storage = None
