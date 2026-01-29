"""
会话日志记录器

提供会话级别的日志记录能力，包括：
- 会话生命周期管理
- 统计信息汇总
- 成本计算
"""

import logging
from datetime import datetime
from typing import Any

from .llm_logger import get_trace_id, set_session_id, set_trace_id
from .models import (
    SessionRecord,
    SessionStatus,
    generate_id,
)
from .storage import LogStorage, get_log_storage

logger = logging.getLogger(__name__)


# Token 价格配置（每 1K tokens）
TOKEN_PRICES = {
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

    # 默认价格
    "default": {"input": 0.001, "output": 0.002},
}


def estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """
    估算 LLM 调用成本

    Args:
        model: 模型名称
        prompt_tokens: 输入 token 数
        completion_tokens: 输出 token 数

    Returns:
        预估成本（美元）
    """
    # 查找匹配的价格
    prices = TOKEN_PRICES.get("default")
    for key in TOKEN_PRICES:
        if key in model.lower():
            prices = TOKEN_PRICES[key]
            break

    input_cost = (prompt_tokens / 1000) * prices["input"]
    output_cost = (completion_tokens / 1000) * prices["output"]
    return input_cost + output_cost


class SessionLogger:
    """会话日志记录器"""

    def __init__(
        self,
        storage: LogStorage | None = None,
        enabled: bool = True,
        auto_cost_estimate: bool = True,
        console_output: bool = True,
    ):
        self.storage = storage or get_log_storage()
        self.enabled = enabled
        self.auto_cost_estimate = auto_cost_estimate
        self.console_output = console_output
        self._active_sessions: dict[str, SessionRecord] = {}

    def start_session(
        self,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        开始新会话

        Args:
            session_id: 可选的会话 ID（默认自动生成）
            metadata: 会话元数据

        Returns:
            会话 ID
        """
        if not self.enabled:
            return session_id or generate_id("sess")

        session_id = session_id or generate_id("sess")
        trace_id = generate_id("trace")

        # 设置上下文
        set_session_id(session_id)
        set_trace_id(trace_id)

        session = SessionRecord(
            session_id=session_id,
            start_time=datetime.now(),
            status=SessionStatus.RUNNING,
            metadata=metadata or {},
        )

        self._active_sessions[session_id] = session

        # 保存到存储
        try:
            self.storage.save_session(session)
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

        if self.console_output:
            logger.info(
                f"[Session Start] session_id={session_id} trace_id={trace_id}"
            )

        return session_id

    def end_session(
        self,
        session_id: str,
        status: SessionStatus = SessionStatus.COMPLETED,
        error_message: str = "",
    ) -> SessionRecord | None:
        """
        结束会话

        Args:
            session_id: 会话 ID
            status: 结束状态
            error_message: 错误信息（如果失败）

        Returns:
            会话记录
        """
        if not self.enabled:
            return None

        session = self._active_sessions.pop(session_id, None)
        if not session:
            # 尝试从存储加载
            session = self.storage.get_session(session_id)
            if not session:
                logger.warning(f"Session not found: {session_id}")
                return None

        session.end_time = datetime.now()
        session.status = status
        session.error_message = error_message

        # 统计 LLM 调用
        llm_calls = self.storage.query_llm_calls(session_id=session_id, limit=10000)
        session.total_llm_calls = len(llm_calls)
        session.total_tokens = sum(
            c.response.usage.total_tokens
            for c in llm_calls
            if c.response and c.response.usage
        )
        session.llm_call_ids = [c.call_id for c in llm_calls]

        # 统计工具调用
        tool_calls = self.storage.query_tool_calls(
            trace_id=get_trace_id(),
            limit=10000
        )
        session.total_tool_calls = len(tool_calls)
        session.tool_call_ids = [c.call_id for c in tool_calls]

        # 计算成本
        if self.auto_cost_estimate:
            session.total_cost = sum(
                estimate_cost(
                    c.request.model,
                    c.response.usage.prompt_tokens,
                    c.response.usage.completion_tokens,
                )
                for c in llm_calls
                if c.response and c.response.usage
            )

        # 保存到存储
        try:
            self.storage.save_session(session)
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

        if self.console_output:
            duration = (session.end_time - session.start_time).total_seconds()
            logger.info(
                f"[Session End] session_id={session_id} status={status.value} "
                f"duration={duration:.1f}s llm_calls={session.total_llm_calls} "
                f"tool_calls={session.total_tool_calls} tokens={session.total_tokens} "
                f"cost=${session.total_cost:.4f}"
            )

        return session

    def get_session(self, session_id: str) -> SessionRecord | None:
        """获取会话记录"""
        # 先检查活跃会话
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]
        # 再从存储加载
        return self.storage.get_session(session_id)

    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """
        获取会话摘要

        Returns:
            包含会话统计信息的字典
        """
        session = self.get_session(session_id)
        if not session:
            return {}

        # 获取详细调用记录
        llm_calls = self.storage.query_llm_calls(session_id=session_id, limit=10000)
        tool_calls = []
        for lc in llm_calls:
            tc = self.storage.query_tool_calls(llm_call_id=lc.call_id)
            tool_calls.extend(tc)

        # 模型使用分布
        model_usage = {}
        for c in llm_calls:
            model = c.request.model
            if model not in model_usage:
                model_usage[model] = {"calls": 0, "tokens": 0, "cost": 0}
            model_usage[model]["calls"] += 1
            if c.response and c.response.usage:
                model_usage[model]["tokens"] += c.response.usage.total_tokens
                model_usage[model]["cost"] += estimate_cost(
                    model,
                    c.response.usage.prompt_tokens,
                    c.response.usage.completion_tokens,
                )

        # 工具使用分布
        tool_usage = {}
        for c in tool_calls:
            tool = c.request.tool_name
            if tool not in tool_usage:
                tool_usage[tool] = {"calls": 0, "success": 0, "avg_duration_ms": 0}
            tool_usage[tool]["calls"] += 1
            if c.success:
                tool_usage[tool]["success"] += 1
            if c.response:
                # 更新平均耗时
                n = tool_usage[tool]["calls"]
                old_avg = tool_usage[tool]["avg_duration_ms"]
                new_val = c.response.duration_ms
                tool_usage[tool]["avg_duration_ms"] = old_avg + (new_val - old_avg) / n

        # 性能指标
        llm_durations = [
            c.response.duration_ms for c in llm_calls
            if c.response
        ]

        return {
            "session": session.to_dict(),
            "llm_calls": {
                "total": len(llm_calls),
                "success": sum(1 for c in llm_calls if c.success),
                "failed": sum(1 for c in llm_calls if not c.success),
                "total_tokens": sum(
                    c.response.usage.total_tokens
                    for c in llm_calls
                    if c.response and c.response.usage
                ),
                "avg_duration_ms": sum(llm_durations) / len(llm_durations) if llm_durations else 0,
                "model_distribution": model_usage,
            },
            "tool_calls": {
                "total": len(tool_calls),
                "success": sum(1 for c in tool_calls if c.success),
                "failed": sum(1 for c in tool_calls if not c.success),
                "tool_distribution": tool_usage,
            },
            "cost": {
                "total": session.total_cost,
                "by_model": {m: v["cost"] for m, v in model_usage.items()},
            },
        }

    def list_sessions(
        self,
        status: SessionStatus | None = None,
        limit: int = 100,
    ) -> list[SessionRecord]:
        """列出会话"""
        # 目前简单实现，返回活跃会话
        sessions = list(self._active_sessions.values())

        if status:
            sessions = [s for s in sessions if s.status == status]

        return sessions[:limit]


# 全局会话日志实例
_session_logger: SessionLogger | None = None


def get_session_logger() -> SessionLogger:
    """获取全局会话日志实例"""
    global _session_logger
    if _session_logger is None:
        _session_logger = SessionLogger()
    return _session_logger


def configure_session_logger(
    storage: LogStorage | None = None,
    **kwargs,
) -> SessionLogger:
    """配置全局会话日志实例"""
    global _session_logger
    _session_logger = SessionLogger(storage=storage, **kwargs)
    return _session_logger


class Session:
    """
    会话上下文管理器

    Example:
        with Session(metadata={"task": "field_fill"}) as sess:
            # 所有 LLM 和工具调用都会关联到这个会话
            result = await process()
    """

    def __init__(
        self,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.session_id = session_id
        self.metadata = metadata
        self._session_logger = get_session_logger()
        self._started = False

    def __enter__(self):
        self.session_id = self._session_logger.start_session(
            session_id=self.session_id,
            metadata=self.metadata,
        )
        self._started = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._started:
            return False

        status = SessionStatus.COMPLETED
        error_message = ""

        if exc_type is not None:
            status = SessionStatus.FAILED
            error_message = str(exc_val)

        self._session_logger.end_session(
            session_id=self.session_id,
            status=status,
            error_message=error_message,
        )
        return False

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)

    def get_summary(self) -> dict[str, Any]:
        """获取会话摘要"""
        return self._session_logger.get_session_summary(self.session_id)
