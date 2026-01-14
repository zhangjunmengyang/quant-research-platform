"""
检索器实现

提供多种检索策略:
- DenseRetriever: 稠密向量检索
- HybridRetriever: 混合检索（稠密 + 稀疏）
- MultiQueryRetriever: 多查询扩展检索
"""

from .hybrid import DenseRetriever, HybridRetriever

__all__ = ["DenseRetriever", "HybridRetriever"]
