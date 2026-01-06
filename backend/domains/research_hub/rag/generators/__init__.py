"""
生成器实现

提供多种 LLM 生成器:
- LLMGenerator: 基于 mcp_core LLM 客户端
- OpenAIGenerator: 直接使用 OpenAI API
"""

from .llm import LLMGenerator

__all__ = ["LLMGenerator"]
