"""
切块器实现

提供多种文档切块策略:
- RecursiveChunker: 递归切块，保持语义完整性
- SemanticChunker: 语义切块，基于嵌入相似度
- MarkdownChunker: Markdown 结构感知切块
"""

from .recursive import RecursiveChunker

__all__ = ["RecursiveChunker"]
