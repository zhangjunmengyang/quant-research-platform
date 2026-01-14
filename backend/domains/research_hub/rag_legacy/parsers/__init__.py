"""
解析器实现

提供多种 PDF/文档解析器实现:
- MinerU: 1.2B 参数的 PDF 解析模型
- Marker: 开源 PDF 解析器
- Unstructured: 通用文档解析器
"""

from .mineru import MinerUParser

__all__ = ["MinerUParser"]
