"""
研报 Agent 模块

提供可扩展的 Agent 架构，用于不同的研报对话场景。

Agent 与 RAG 的关系:
- RAG 是数据处理层，负责检索和生成
- Agent 是应用层，负责对话流程、模型选择、扩展能力

可用 Agent:
- ResearchChatAgent: 单研报对话
- (后续扩展) LibraryChatAgent: 全库对话
- (后续扩展) BriefingAgent: 知识简报生成
"""

from .base import BaseAgent, AgentConfig, AgentResponse
from .research_chat import ResearchChatAgent

__all__ = [
    "BaseAgent",
    "AgentConfig",
    "AgentResponse",
    "ResearchChatAgent",
]
