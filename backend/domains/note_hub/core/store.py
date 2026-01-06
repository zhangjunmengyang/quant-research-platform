"""
笔记存储层 - PostgreSQL 数据源

提供笔记的持久化存储和查询功能。
继承 mcp_core.BaseStore，复用连接管理和通用 CRUD。
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import psycopg2

from domains.mcp_core.base.store import (
    BaseStore,
    get_store_instance,
    reset_store_instance,
)
from domains.mcp_core.database.query_builder import QueryBuilder

from .models import Note

logger = logging.getLogger(__name__)


class NoteStore(BaseStore[Note]):
    """
    笔记存储层 - PostgreSQL 数据源

    继承 BaseStore，提供笔记的 CRUD 操作、查询等功能。
    """

    # BaseStore 配置
    table_name = "notes"

    allowed_columns = {
        'id', 'title', 'content', 'tags', 'source', 'source_ref',
        'created_at', 'updated_at'
    }

    numeric_fields = {'id'}

    # 向后兼容别名
    ALLOWED_COLUMNS = allowed_columns

    def _row_to_entity(self, row: Dict[str, Any]) -> Note:
        """将数据库行转换为 Note 对象"""
        valid_fields = {k: v for k, v in row.items() if k in Note.__dataclass_fields__}
        return Note(**valid_fields)

    def _create_query_builder(self) -> QueryBuilder:
        """创建查询构建器"""
        return QueryBuilder(
            table=self.table_name,
            allowed_columns=self.allowed_columns,
            numeric_fields=self.numeric_fields
        )

    # ==================== 基本 CRUD ====================

    def get(self, note_id: int) -> Optional[Note]:
        """获取单个笔记"""
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT * FROM notes WHERE id = %s',
                (note_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entity(dict(row))
        return None

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Note]:
        """获取所有笔记"""
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT * FROM notes ORDER BY updated_at DESC LIMIT %s OFFSET %s',
                (limit, offset)
            )
            return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

    def add(self, note: Note) -> Optional[int]:
        """添加笔记，返回新笔记的 ID"""
        note.created_at = datetime.now()
        note.updated_at = datetime.now()

        try:
            with self._cursor() as cursor:
                cursor.execute('''
                    INSERT INTO notes (
                        title, content, tags, source, source_ref,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    note.title, note.content, note.tags, note.source,
                    note.source_ref, note.created_at, note.updated_at
                ))
                result = cursor.fetchone()
                return result['id'] if result else None
        except psycopg2.IntegrityError as e:
            logger.error(f"添加笔记失败: {e}")
            return None

    def update(self, note_id: int, **fields) -> bool:
        """更新笔记字段"""
        if not fields:
            return False

        # 安全验证字段名，防止 SQL 注入
        safe_fields = {k: v for k, v in fields.items() if k in self.allowed_columns}
        if not safe_fields:
            logger.warning(f"No valid fields to update: {list(fields.keys())}")
            return False

        safe_fields['updated_at'] = datetime.now()

        set_clause = ', '.join(f'{k} = %s' for k in safe_fields.keys())
        values = list(safe_fields.values()) + [note_id]

        with self._cursor() as cursor:
            cursor.execute(
                f'UPDATE notes SET {set_clause} WHERE id = %s',
                values
            )
            return cursor.rowcount > 0

    def delete(self, note_id: int) -> bool:
        """删除笔记"""
        with self._cursor() as cursor:
            cursor.execute('DELETE FROM notes WHERE id = %s', (note_id,))
            return cursor.rowcount > 0

    # ==================== 查询操作 ====================

    def query(
        self,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
        order_by: str = "updated_at DESC",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Note], int]:
        """
        条件查询笔记

        Args:
            search: 搜索关键词（标题和内容）
            tags: 标签筛选
            source: 来源筛选
            order_by: 排序
            limit: 限制数量
            offset: 偏移量

        Returns:
            (笔记列表, 总数)
        """
        builder = self._create_query_builder()

        if search:
            builder.where_raw(
                "(title ILIKE %s OR content ILIKE %s)",
                [f'%{search}%', f'%{search}%']
            )

        if tags:
            for tag in tags:
                builder.where_raw("tags ILIKE %s", [f'%{tag}%'])

        if source:
            builder.where("source", source)

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
            notes = [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

        return notes, total

    def search(self, keyword: str, limit: int = 20) -> List[Note]:
        """全文搜索笔记"""
        notes, _ = self.query(search=keyword, limit=limit)
        return notes

    def get_by_source(self, source: str, source_ref: str) -> List[Note]:
        """根据来源获取笔记"""
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT * FROM notes WHERE source = %s AND source_ref = %s ORDER BY updated_at DESC',
                (source, source_ref)
            )
            return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

    def get_tags(self) -> List[str]:
        """获取所有标签（去重）"""
        with self._cursor() as cursor:
            cursor.execute("SELECT DISTINCT tags FROM notes WHERE tags != ''")
            tags = set()
            for row in cursor.fetchall():
                for tag in row['tags'].split(','):
                    tag = tag.strip()
                    if tag:
                        tags.add(tag)
            return sorted(tags)

    def count(self) -> int:
        """统计笔记总数"""
        with self._cursor() as cursor:
            cursor.execute('SELECT COUNT(*) as count FROM notes')
            return cursor.fetchone()['count']


# ==================== 单例管理 ====================

def get_note_store(database_url: Optional[str] = None) -> NoteStore:
    """获取笔记存储层单例"""
    return get_store_instance(NoteStore, "NoteStore", database_url=database_url)


def reset_note_store():
    """重置存储层单例（用于测试）"""
    reset_store_instance("NoteStore")
