"""
LLM 基础设施层

提供基于 LangChain 的 LLM 调用能力:
- 配置驱动的模型管理
- 自动日志记录（与 observability 集成）
- 简洁的调用接口

这是一个纯技术基础设施模块，不包含业务逻辑。
业务相关的 Prompt 模板和结果解析应在各业务域中实现。

Example:
    from domains.mcp_core.llm import get_llm_client

    client = get_llm_client()

    # 简单调用
    result = await client.ainvoke([
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ])

    # 指定模型和参数
    result = await client.ainvoke(
        messages=[...],
        model_key="claude",
        temperature=0.8,
    )
"""

from .client import (
    LLMClient,
    get_llm_client,
    reset_llm_client,
)
from .config import (
    LLMSettings,
    ModelConfig,
    get_llm_settings,
    reload_llm_settings,
)

__all__ = [
    # Config
    "LLMSettings",
    "ModelConfig",
    "get_llm_settings",
    "reload_llm_settings",
    # Client
    "LLMClient",
    "get_llm_client",
    "reset_llm_client",
]
