"""
RAG 核心框架

模块化设计，支持:
- 组件可插拔替换
- 配置驱动的流水线
- A/B 测试和对比实验
- Agentic RAG 扩展
"""

# 导入所有组件实现以触发装饰器注册
# 注意：必须在使用 registry 之前导入这些模块

# 解析器
from .parsers.mineru import MinerUParser, BasicPDFParser

# 切块器
from .chunkers.recursive import RecursiveChunker, SentenceChunker

# 嵌入器
from .embedders.bge_m3 import OpenAIEmbedder

# 向量存储
from .vector_stores.pgvector import PgVectorStore

# 检索器
from .retrievers.hybrid import DenseRetriever, HybridRetriever, MultiQueryRetriever

# 重排器
from .rerankers.bge import BGEReranker, NoOpReranker, CohereReranker

# 生成器
from .generators.llm import LLMGenerator, AnthropicGenerator

# 流水线
from .pipelines.standard import StandardPipeline, FastPipeline

__all__ = [
    # 解析器
    "MinerUParser",
    "BasicPDFParser",
    # 切块器
    "RecursiveChunker",
    "SentenceChunker",
    # 嵌入器
    "OpenAIEmbedder",
    # 向量存储
    "PgVectorStore",
    # 检索器
    "DenseRetriever",
    "HybridRetriever",
    "MultiQueryRetriever",
    # 重排器
    "BGEReranker",
    "NoOpReranker",
    "CohereReranker",
    # 生成器
    "LLMGenerator",
    "AnthropicGenerator",
    # 流水线
    "StandardPipeline",
    "FastPipeline",
]
