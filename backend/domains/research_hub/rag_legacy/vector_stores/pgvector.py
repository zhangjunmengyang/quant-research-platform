"""
pgvector 向量存储

使用 PostgreSQL pgvector 扩展进行向量存储和检索。
支持:
- HNSW 索引（高性能近似最近邻搜索）
- 元数据过滤
- 混合搜索（向量 + 全文）
"""

import json
import logging
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

from ..base.vector_store import BaseVectorStore, SearchResult
from ..base.chunker import Chunk, ChunkMetadata
from ..base.registry import component_registries

logger = logging.getLogger(__name__)


@component_registries.vector_store.register("pgvector")
class PgVectorStore(BaseVectorStore):
    """
    pgvector 向量存储

    使用 PostgreSQL pgvector 扩展，复用项目已有的数据库连接。

    特性:
    - HNSW 索引支持高效的 ANN 搜索
    - 支持余弦相似度、欧几里得距离、内积
    - 与 research_chunks 表集成

    使用示例:
        store = PgVectorStore(
            connection_string="postgresql://...",
            collection_name="research_chunks",
        )
        await store.setup()
        await store.upsert(chunks)
        results = await store.search(query_vector, top_k=10)
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        collection_name: str = "research_chunks",
        dimensions: int = 1024,
        index_type: str = "hnsw",
        distance_metric: str = "cosine",
        hnsw_m: int = 16,
        hnsw_ef_construction: int = 64,
        hnsw_ef_search: int = 40,
        **kwargs,
    ):
        super().__init__(
            connection_string=connection_string,
            collection_name=collection_name,
            dimensions=dimensions,
            index_type=index_type,
            **kwargs,
        )
        self.distance_metric = distance_metric
        self.hnsw_m = hnsw_m
        self.hnsw_ef_construction = hnsw_ef_construction
        self.hnsw_ef_search = hnsw_ef_search
        self._conn = None

    async def setup(self) -> None:
        """初始化数据库连接"""
        import os

        connection_string = self.config.connection_string or os.getenv("DATABASE_URL")

        if not connection_string:
            raise ValueError(
                "Database connection string required. "
                "Set DATABASE_URL environment variable or pass connection_string."
            )

        self._conn = psycopg2.connect(
            connection_string,
            cursor_factory=RealDictCursor,
        )
        self._conn.autocommit = True

        # 确保 pgvector 扩展已启用
        with self._conn.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")

        logger.info(f"PgVectorStore connected to {self.config.collection_name}")

    async def teardown(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
        logger.info("PgVectorStore connection closed")

    async def upsert(self, chunks: List[Chunk]) -> None:
        """
        更新向量嵌入

        切块数据已存在于 research_chunks 表中，此方法只更新 embedding 列。

        Args:
            chunks: 带有嵌入的切块列表
        """
        if not chunks:
            return

        if self._conn is None:
            await self.setup()

        # 过滤没有嵌入的切块
        valid_chunks = [c for c in chunks if c.embedding is not None]
        if not valid_chunks:
            logger.warning("No chunks with embeddings to upsert")
            return

        with self._conn.cursor() as cursor:
            # 只更新 embedding 列（切块数据已由 ChunkStore 插入）
            for chunk in valid_chunks:
                cursor.execute(
                    f"""
                    UPDATE {self.config.collection_name}
                    SET embedding = %s::vector
                    WHERE chunk_id = %s
                    """,
                    (chunk.embedding, chunk.chunk_id),
                )

        logger.info(f"Updated embeddings for {len(valid_chunks)} chunks")

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
        if self._conn is None:
            await self.setup()

        # 构建查询
        vector_str = f"[{','.join(map(str, query_vector))}]"

        # 选择距离运算符
        if self.distance_metric == "cosine":
            distance_op = "<=>"  # 余弦距离
        elif self.distance_metric == "euclidean":
            distance_op = "<->"  # 欧几里得距离
        else:
            distance_op = "<#>"  # 内积（负值）

        # 构建 WHERE 子句
        where_clauses = ["embedding IS NOT NULL"]
        params = [vector_str]

        if filter_conditions:
            if "report_id" in filter_conditions:
                where_clauses.append("report_id = %s")
                params.append(filter_conditions["report_id"])
            if "report_uuid" in filter_conditions:
                where_clauses.append("report_uuid = %s")
                params.append(filter_conditions["report_uuid"])
            if "chunk_type" in filter_conditions:
                where_clauses.append("chunk_type = %s")
                params.append(filter_conditions["chunk_type"])

        where_sql = " AND ".join(where_clauses)

        # 设置 HNSW 搜索参数
        with self._conn.cursor() as cursor:
            cursor.execute(
                f"SET hnsw.ef_search = {self.hnsw_ef_search}"
            )

            # 执行搜索
            cursor.execute(
                f'''
                SELECT
                    chunk_id,
                    report_id,
                    report_uuid,
                    chunk_index,
                    page_start,
                    page_end,
                    chunk_type,
                    content,
                    token_count,
                    heading_path,
                    section_title,
                    metadata,
                    embedding {distance_op} %s::vector AS distance
                FROM {self.config.collection_name}
                WHERE {where_sql}
                ORDER BY embedding {distance_op} %s::vector
                LIMIT %s
                ''',
                params + [vector_str, top_k],
            )

            rows = cursor.fetchall()

        # 转换结果
        results = []
        for row in rows:
            # 将距离转换为相似度分数
            distance = row["distance"]
            if self.distance_metric == "cosine":
                score = 1 - distance  # 余弦相似度 = 1 - 余弦距离
            elif self.distance_metric == "euclidean":
                score = 1 / (1 + distance)  # 转换为 0-1 范围
            else:
                score = -distance  # 内积

            # 解析 heading_path
            heading_path = []
            if row["heading_path"]:
                try:
                    heading_path = json.loads(row["heading_path"])
                except json.JSONDecodeError:
                    pass

            chunk = Chunk(
                content=row["content"],
                chunk_id=row["chunk_id"],
                token_count=row["token_count"],
                metadata=ChunkMetadata(
                    document_id=row["report_uuid"],
                    chunk_index=row["chunk_index"],
                    page_start=row["page_start"],
                    page_end=row["page_end"],
                    heading_path=heading_path,
                    section_title=row["section_title"],
                ),
            )

            results.append(
                SearchResult(
                    chunk=chunk,
                    score=score,
                    distance=distance,
                    document_id=row["report_uuid"],
                    chunk_id=row["chunk_id"],
                    metadata=row["metadata"] if row["metadata"] else {},
                )
            )

        logger.info(f"Search returned {len(results)} results")
        return results

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
        混合搜索（稠密向量 + 全文搜索）

        Args:
            query_vector: 稠密查询向量
            sparse_vector: 稀疏向量（未使用，用全文搜索替代）
            top_k: 返回数量
            dense_weight: 稠密搜索权重
            sparse_weight: 稀疏搜索权重
            filter_conditions: 过滤条件

        Returns:
            融合后的搜索结果
        """
        # 简化实现：使用向量搜索 + 全文搜索的 RRF 融合
        # 首先获取向量搜索结果
        dense_results = await self.search(
            query_vector, top_k * 2, filter_conditions
        )

        # 如果没有稀疏向量，直接返回稠密结果
        if sparse_vector is None:
            return dense_results[:top_k]

        # TODO: 实现真正的混合搜索（RRF 融合）
        # 当前简化为只使用稠密搜索
        return dense_results[:top_k]

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
        if self._conn is None:
            await self.setup()

        if not chunk_ids and not document_id:
            return 0

        with self._conn.cursor() as cursor:
            if chunk_ids:
                cursor.execute(
                    f"DELETE FROM {self.config.collection_name} WHERE chunk_id = ANY(%s)",
                    (chunk_ids,),
                )
            elif document_id:
                cursor.execute(
                    f"DELETE FROM {self.config.collection_name} WHERE report_uuid = %s",
                    (document_id,),
                )

            deleted = cursor.rowcount

        logger.info(f"Deleted {deleted} chunks")
        return deleted

    async def get_by_id(self, chunk_id: str) -> Optional[Chunk]:
        """根据 ID 获取切块"""
        if self._conn is None:
            await self.setup()

        with self._conn.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {self.config.collection_name} WHERE chunk_id = %s",
                (chunk_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        heading_path = []
        if row["heading_path"]:
            try:
                heading_path = json.loads(row["heading_path"])
            except json.JSONDecodeError:
                pass

        return Chunk(
            content=row["content"],
            chunk_id=row["chunk_id"],
            token_count=row["token_count"],
            metadata=ChunkMetadata(
                document_id=row["report_uuid"],
                chunk_index=row["chunk_index"],
                page_start=row["page_start"],
                page_end=row["page_end"],
                heading_path=heading_path,
                section_title=row["section_title"],
            ),
        )

    async def count(self, document_id: Optional[str] = None) -> int:
        """统计向量数量"""
        if self._conn is None:
            await self.setup()

        with self._conn.cursor() as cursor:
            if document_id:
                cursor.execute(
                    f"SELECT COUNT(*) as count FROM {self.config.collection_name} WHERE report_uuid = %s",
                    (document_id,),
                )
            else:
                cursor.execute(
                    f"SELECT COUNT(*) as count FROM {self.config.collection_name}"
                )
            return cursor.fetchone()["count"]
