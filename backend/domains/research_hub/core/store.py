"""
研报存储层 - PostgreSQL 数据源

提供研报、切块的持久化存储和查询功能。
继承 mcp_core.BaseStore，复用连接管理和通用 CRUD。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import psycopg2

from domains.mcp_core.base.store import (
    BaseStore,
    get_store_instance,
    reset_store_instance,
)
from domains.mcp_core.database.query_builder import QueryBuilder

from .models import (
    ResearchReport,
    ResearchChunk,
    ProcessingStatus,
)

logger = logging.getLogger(__name__)


class ResearchStore(BaseStore[ResearchReport]):
    """
    研报存储层

    提供研报的 CRUD 操作、查询等功能。
    """

    table_name = "research_reports"

    allowed_columns = {
        'id', 'uuid', 'title', 'filename', 'file_path', 'file_size', 'page_count',
        'author', 'source_url', 'publish_date',
        'content_markdown', 'summary', 'tags', 'category',
        'status', 'progress', 'error_message',
        'created_at', 'updated_at', 'parsed_at', 'indexed_at'
    }

    numeric_fields = {'id', 'file_size', 'page_count', 'progress'}

    def _row_to_entity(self, row: Dict[str, Any]) -> ResearchReport:
        """将数据库行转换为 ResearchReport 对象"""
        valid_fields = {k: v for k, v in row.items() if k in ResearchReport.__dataclass_fields__}
        return ResearchReport(**valid_fields)

    def _create_query_builder(self) -> QueryBuilder:
        """创建查询构建器"""
        return QueryBuilder(
            table=self.table_name,
            allowed_columns=self.allowed_columns,
            numeric_fields=self.numeric_fields
        )

    # ==================== 基本 CRUD ====================

    def get(self, report_id: int) -> Optional[ResearchReport]:
        """获取单个研报"""
        with self._cursor() as cursor:
            cursor.execute(
                f'SELECT * FROM {self.table_name} WHERE id = %s',
                (report_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entity(dict(row))
        return None

    def get_by_uuid(self, uuid: str) -> Optional[ResearchReport]:
        """通过 UUID 获取研报"""
        with self._cursor() as cursor:
            cursor.execute(
                f'SELECT * FROM {self.table_name} WHERE uuid = %s',
                (uuid,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entity(dict(row))
        return None

    def get_all(self, limit: int = 100, offset: int = 0) -> List[ResearchReport]:
        """获取所有研报"""
        with self._cursor() as cursor:
            cursor.execute(
                f'SELECT * FROM {self.table_name} ORDER BY created_at DESC LIMIT %s OFFSET %s',
                (limit, offset)
            )
            return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

    def add(self, report: ResearchReport) -> Optional[int]:
        """添加研报，返回新研报的 ID"""
        report.created_at = datetime.now()
        report.updated_at = datetime.now()

        try:
            with self._cursor() as cursor:
                cursor.execute(f'''
                    INSERT INTO {self.table_name} (
                        uuid, title, filename, file_path, file_size, page_count,
                        author, source_url, publish_date,
                        content_markdown, summary, tags, category,
                        status, progress, error_message,
                        created_at, updated_at, parsed_at, indexed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    report.uuid, report.title, report.filename, report.file_path,
                    report.file_size, report.page_count,
                    report.author, report.source_url, report.publish_date,
                    report.content_markdown, report.summary, report.tags, report.category,
                    report.status, report.progress, report.error_message,
                    report.created_at, report.updated_at, report.parsed_at, report.indexed_at
                ))
                result = cursor.fetchone()
                return result['id'] if result else None
        except psycopg2.IntegrityError as e:
            logger.error(f"添加研报失败: {e}")
            return None

    def update(self, report_id: int, **fields) -> bool:
        """更新研报字段"""
        if not fields:
            return False

        safe_fields = {k: v for k, v in fields.items() if k in self.allowed_columns}
        if not safe_fields:
            logger.warning(f"No valid fields to update: {list(fields.keys())}")
            return False

        safe_fields['updated_at'] = datetime.now()

        set_clause = ', '.join(f'{k} = %s' for k in safe_fields.keys())
        values = list(safe_fields.values()) + [report_id]

        with self._cursor() as cursor:
            cursor.execute(
                f'UPDATE {self.table_name} SET {set_clause} WHERE id = %s',
                values
            )
            return cursor.rowcount > 0

    def delete(self, report_id: int) -> bool:
        """删除研报"""
        with self._cursor() as cursor:
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = %s', (report_id,))
            return cursor.rowcount > 0

    # ==================== 查询操作 ====================

    def query(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        order_by: str = "created_at DESC",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[ResearchReport], int]:
        """条件查询研报"""
        builder = self._create_query_builder()

        if search:
            builder.where_raw(
                "(title ILIKE %s OR summary ILIKE %s)",
                [f'%{search}%', f'%{search}%']
            )

        if status:
            builder.where("status", status)

        if category:
            builder.where("category", category)

        if tags:
            for tag in tags:
                builder.where_raw("tags ILIKE %s", [f'%{tag}%'])

        # 先获取总数
        count_sql, count_params = builder.build_count()
        with self._cursor() as cursor:
            cursor.execute(count_sql, count_params)
            total = cursor.fetchone()['count']

        # 添加排序和分页
        builder.order_by(order_by)
        builder.limit(limit)
        builder.offset(offset)

        sql, params = builder.build()

        with self._cursor() as cursor:
            cursor.execute(sql, params)
            reports = [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

        return reports, total

    def get_by_status(self, status: str) -> List[ResearchReport]:
        """按状态获取研报"""
        with self._cursor() as cursor:
            cursor.execute(
                f'SELECT * FROM {self.table_name} WHERE status = %s ORDER BY created_at DESC',
                (status,)
            )
            return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

    def update_status(
        self,
        report_id: int,
        status: str,
        progress: int = 0,
        error_message: str = ""
    ) -> bool:
        """更新处理状态"""
        return self.update(
            report_id,
            status=status,
            progress=progress,
            error_message=error_message
        )

    def count(self, status: Optional[str] = None) -> int:
        """统计研报数量"""
        with self._cursor() as cursor:
            if status:
                cursor.execute(
                    f'SELECT COUNT(*) as count FROM {self.table_name} WHERE status = %s',
                    (status,)
                )
            else:
                cursor.execute(f'SELECT COUNT(*) as count FROM {self.table_name}')
            return cursor.fetchone()['count']


class ChunkStore(BaseStore[ResearchChunk]):
    """
    切块存储层

    提供切块的 CRUD 操作。
    注意：向量存储由单独的 VectorStore 处理。
    """

    table_name = "research_chunks"

    allowed_columns = {
        'id', 'chunk_id', 'report_id', 'report_uuid',
        'chunk_index', 'page_start', 'page_end',
        'chunk_type', 'content', 'token_count',
        'heading_path', 'section_title',
        'embedding_model', 'metadata',
        'created_at'
    }

    numeric_fields = {'id', 'report_id', 'chunk_index', 'page_start', 'page_end', 'token_count'}

    def _row_to_entity(self, row: Dict[str, Any]) -> ResearchChunk:
        """将数据库行转换为 ResearchChunk 对象"""
        valid_fields = {k: v for k, v in row.items() if k in ResearchChunk.__dataclass_fields__}
        return ResearchChunk(**valid_fields)

    def add(self, chunk: ResearchChunk) -> Optional[int]:
        """添加切块"""
        chunk.created_at = datetime.now()

        try:
            with self._cursor() as cursor:
                cursor.execute(f'''
                    INSERT INTO {self.table_name} (
                        chunk_id, report_id, report_uuid,
                        chunk_index, page_start, page_end,
                        chunk_type, content, token_count,
                        heading_path, section_title,
                        embedding_model, metadata,
                        created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    chunk.chunk_id, chunk.report_id, chunk.report_uuid,
                    chunk.chunk_index, chunk.page_start, chunk.page_end,
                    chunk.chunk_type, chunk.content, chunk.token_count,
                    chunk.heading_path, chunk.section_title,
                    chunk.embedding_model, chunk.metadata,
                    chunk.created_at
                ))
                result = cursor.fetchone()
                return result['id'] if result else None
        except psycopg2.IntegrityError as e:
            logger.error(f"添加切块失败: {e}")
            return None

    def add_batch(self, chunks: List[ResearchChunk]) -> int:
        """批量添加切块"""
        if not chunks:
            return 0

        now = datetime.now()
        for chunk in chunks:
            chunk.created_at = now

        try:
            with self._cursor() as cursor:
                from psycopg2.extras import execute_values
                values = [
                    (
                        chunk.chunk_id, chunk.report_id, chunk.report_uuid,
                        chunk.chunk_index, chunk.page_start, chunk.page_end,
                        chunk.chunk_type, chunk.content, chunk.token_count,
                        chunk.heading_path, chunk.section_title,
                        chunk.embedding_model, chunk.metadata,
                        chunk.created_at
                    )
                    for chunk in chunks
                ]
                execute_values(
                    cursor,
                    f'''
                    INSERT INTO {self.table_name} (
                        chunk_id, report_id, report_uuid,
                        chunk_index, page_start, page_end,
                        chunk_type, content, token_count,
                        heading_path, section_title,
                        embedding_model, metadata,
                        created_at
                    ) VALUES %s
                    ''',
                    values
                )
                return len(chunks)
        except Exception as e:
            logger.error(f"批量添加切块失败: {e}")
            return 0

    def get_by_report(
        self,
        report_id: int,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Tuple[List[ResearchChunk], int]:
        """获取研报的切块(支持分页)

        Args:
            report_id: 研报ID
            limit: 返回数量限制，None表示返回全部
            offset: 偏移量

        Returns:
            (切块列表, 总数)
        """
        with self._cursor() as cursor:
            # 获取总数
            cursor.execute(
                f'SELECT COUNT(*) as count FROM {self.table_name} WHERE report_id = %s',
                (report_id,)
            )
            total = cursor.fetchone()['count']

            # 获取切块
            if limit is not None:
                cursor.execute(
                    f'SELECT * FROM {self.table_name} WHERE report_id = %s ORDER BY chunk_index LIMIT %s OFFSET %s',
                    (report_id, limit, offset)
                )
            else:
                cursor.execute(
                    f'SELECT * FROM {self.table_name} WHERE report_id = %s ORDER BY chunk_index',
                    (report_id,)
                )
            chunks = [self._row_to_entity(dict(row)) for row in cursor.fetchall()]
            return chunks, total

    def delete_by_report(self, report_id: int) -> int:
        """删除研报的所有切块"""
        with self._cursor() as cursor:
            cursor.execute(
                f'DELETE FROM {self.table_name} WHERE report_id = %s',
                (report_id,)
            )
            return cursor.rowcount

    def count_by_report(self, report_id: int) -> int:
        """统计研报的切块数量"""
        with self._cursor() as cursor:
            cursor.execute(
                f'SELECT COUNT(*) as count FROM {self.table_name} WHERE report_id = %s',
                (report_id,)
            )
            return cursor.fetchone()['count']


# ==================== 单例管理 ====================

def get_research_store(database_url: Optional[str] = None) -> ResearchStore:
    """获取研报存储层单例"""
    return get_store_instance(ResearchStore, "ResearchStore", database_url=database_url)


def get_chunk_store(database_url: Optional[str] = None) -> ChunkStore:
    """获取切块存储层单例"""
    return get_store_instance(ChunkStore, "ChunkStore", database_url=database_url)


def reset_research_store():
    """重置存储层单例（用于测试）"""
    reset_store_instance("ResearchStore")


def reset_chunk_store():
    """重置存储层单例（用于测试）"""
    reset_store_instance("ChunkStore")
