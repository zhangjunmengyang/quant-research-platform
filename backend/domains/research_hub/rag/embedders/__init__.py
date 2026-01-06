"""
嵌入器实现

提供多种嵌入模型:
- OpenAI: OpenAI Embeddings API (兼容各种 OpenAI 格式的 API)
"""

from .bge_m3 import OpenAIEmbedder

__all__ = ["OpenAIEmbedder"]
