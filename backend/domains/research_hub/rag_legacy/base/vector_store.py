"""
向量存储基类

负责向量的存储和检索。
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from .component import AsyncComponent, ComponentConfig, ComponentType
from .chunker import Chunk


class IndexType(Enum):
    """索引类型"""
    FLAT = "flat"  # 精确搜索
    IVFFLAT = "ivfflat"  # IVF 索引
    HNSW = "hnsw"  # HNSW 索引
    DISKANN = "diskann"  # DiskANN 索引


class DistanceMetric(Enum):
    """距离度量"""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"


@dataclass
class SearchResult:
    """搜索结果"""
    chunk: Chunk
    score: float  # 相似度分数
    distance: Optional[float] = None  # 距离

    # 来源信息
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def content(self) -> str:
        """内容快捷访问"""
        return self.chunk.content


@dataclass
class VectorStoreConfig(ComponentConfig):
    """向量存储配置"""
    # 连接配置
    connection_string: Optional[str] = None
    collection_name: str = "research_chunks"

    # 索引配置
    index_type: IndexType = IndexType.HNSW
    distance_metric: DistanceMetric = DistanceMetric.COSINE

    # 向量配置
    dimensions: int = 1024

    # HNSW 参数
    hnsw_m: int = 16
    hnsw_ef_construction: int = 64
    hnsw_ef_search: int = 40


class BaseVectorStore(AsyncComponent[VectorStoreConfig, None]):
    """
    向量存储基类

    负责向量的存储和检索，支持:
    - 稠密向量搜索
    - 稀疏向量搜索
    - 混合搜索

    设计要点:
    1. 抽象接口，支持多种后端 (pgvector, Qdrant, Milvus)
    2. 支持批量操作
    3. 支持元数据过滤

    示例:
        @component_registries.vector_store.register("pgvector")
        class PgVectorStore(BaseVectorStore):
            async def upsert(self, chunks: List[Chunk]) -> None:
                # 插入或更新向量
                ...
    """

    component_type = ComponentType.VECTOR_STORE

    def __init__(
        self,
        connection_string: Optional[str] = None,
        collection_name: str = "research_chunks",
        dimensions: int = 1024,
        index_type: str = "hnsw",
        **kwargs,
    ):
        config = VectorStoreConfig(
            connection_string=connection_string,
            collection_name=collection_name,
            dimensions=dimensions,
            index_type=IndexType(index_type) if isinstance(index_type, str) else index_type,
            extra=kwargs,
        )
        super().__init__(config)

    @abstractmethod
    async def upsert(self, chunks: List[Chunk]) -> None:
        """
        插入或更新向量

        Args:
            chunks: 带有嵌入的切块列表
        """
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        向量搜索

        Args:
            query_vector: 查询向量
            top_k: 返回数量
            filter_conditions: 元数据过滤条件

        Returns:
            搜索结果列表
        """
        raise NotImplementedError

    async def search_hybrid(
        self,
        query_vector: List[float],
        sparse_vector: Optional[Dict[str, float]] = None,
        top_k: int = 10,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        混合搜索（稠密 + 稀疏）

        默认实现只使用稠密向量，子类可覆盖以支持混合搜索。
        """
        return await self.search(query_vector, top_k, filter_conditions)

    @abstractmethod
    async def delete(
        self,
        chunk_ids: Optional[List[str]] = None,
        document_id: Optional[str] = None,
    ) -> int:
        """
        删除向量

        Args:
            chunk_ids: 切块 ID 列表
            document_id: 文档 ID（删除该文档的所有切块）

        Returns:
            删除的数量
        """
        raise NotImplementedError

    async def get_by_id(self, chunk_id: str) -> Optional[Chunk]:
        """根据 ID 获取切块"""
        raise NotImplementedError

    async def count(
        self,
        document_id: Optional[str] = None,
    ) -> int:
        """
        统计数量

        Args:
            document_id: 可选的文档 ID 过滤

        Returns:
            向量数量
        """
        raise NotImplementedError

    async def execute(self, *args, **kwargs) -> None:
        """向量存储不使用通用 execute"""
        raise NotImplementedError("Use specific methods like upsert, search, delete")
