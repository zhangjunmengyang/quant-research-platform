"""
笔记存储层 - PostgreSQL 数据源

提供笔记的持久化存储和查询功能。
继承 mcp_core.BaseStore，复用连接管理和通用 CRUD。

Note Hub 定位为"研究草稿/临时记录"层，支持：
- 笔记类型分类（observation/hypothesis/verification）
- 归档管理
- 实体关联通过 Edge 系统 (mcp_core/edge) 管理
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

from .models import Note, NoteType

logger = logging.getLogger(__name__)


class NoteStore(BaseStore[Note]):
    """
    笔记存储层 - PostgreSQL 数据源

    继承 BaseStore，提供笔记的 CRUD 操作、查询等功能。
    """

    # BaseStore 配置
    table_name = "notes"

    allowed_columns = {
        'id', 'uuid', 'title', 'content', 'tags',
        'source', 'source_ref',
        'note_type',
        'promoted_to_experience_id', 'is_archived',
        'created_at', 'updated_at'
    }

    numeric_fields = {'id', 'promoted_to_experience_id'}

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

    def get_by_uuid(self, uuid: str) -> Optional[Note]:
        """通过 UUID 获取笔记"""
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT * FROM notes WHERE uuid = %s',
                (uuid,)
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
        import uuid as uuid_lib

        # 确保有 UUID
        if not note.uuid:
            note.uuid = str(uuid_lib.uuid4())

        note.created_at = datetime.now()
        note.updated_at = datetime.now()

        try:
            with self._cursor() as cursor:
                cursor.execute('''
                    INSERT INTO notes (
                        uuid, title, content, tags, source, source_ref,
                        note_type,
                        promoted_to_experience_id, is_archived,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    note.uuid, note.title, note.content, note.tags,
                    note.source, note.source_ref,
                    note.note_type,
                    note.promoted_to_experience_id, note.is_archived,
                    note.created_at, note.updated_at
                ))
                result = cursor.fetchone()
                note_id = result['id'] if result else None
        except psycopg2.IntegrityError as e:
            logger.error(f"添加笔记失败: {e}")
            return None

        # 触发实时同步
        if note_id:
            self._trigger_sync(note_id)

        return note_id

    def _trigger_sync(self, note_id: int) -> None:
        """触发笔记同步到文件（不阻塞主流程）"""
        try:
            from domains.mcp_core.sync.trigger import get_sync_trigger
            get_sync_trigger().sync_note(note_id)
        except Exception as e:
            # 同步失败只记录日志，不影响主业务
            logger.debug(f"note_sync_trigger_skipped: {note_id}, {e}")

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
            updated = cursor.rowcount > 0

        # 触发实时同步
        if updated:
            self._trigger_sync(note_id)

        return updated

    def delete(self, note_id: int) -> bool:
        """删除笔记（同时删除数据库记录、关联边和对应的文件）"""
        # 先获取笔记信息，用于后续删除文件
        note = self.get(note_id)
        if note is None:
            return False

        # 删除关联的边
        self._delete_note_edges(note_id)

        # 删除数据库记录
        with self._cursor() as cursor:
            cursor.execute('DELETE FROM notes WHERE id = %s', (note_id,))
            deleted = cursor.rowcount > 0

        # 如果删除成功且笔记有 UUID，删除对应的文件
        if deleted and note.uuid:
            self._delete_note_file(note)

        return deleted

    def _delete_note_edges(self, note_id: int) -> None:
        """删除笔记关联的所有边"""
        try:
            from domains.mcp_core.edge.store import get_edge_store
            from domains.mcp_core.edge.models import EdgeEntityType

            edge_store = get_edge_store()
            deleted_count = edge_store.delete_edges_by_entity(
                EdgeEntityType.NOTE,
                str(note_id)
            )
            if deleted_count > 0:
                logger.info(f"deleted_note_edges: note_id={note_id}, count={deleted_count}")
        except Exception as e:
            # 边删除失败只记录日志，不影响主业务
            logger.warning(f"failed_to_delete_note_edges: {note_id}, {e}")

    def _delete_note_file(self, note: Note) -> None:
        """删除笔记对应的文件"""
        try:
            from domains.mcp_core.sync.note_sync import NoteSyncService
            from pathlib import Path
            import os

            # 获取私有数据目录
            private_dir = Path(os.environ.get('PRIVATE_DATA_DIR', 'private'))
            type_dir = NoteSyncService.TYPE_DIRS.get(note.note_type, 'observations')
            filepath = private_dir / "notes" / type_dir / f"{note.uuid}.md"

            if filepath.exists():
                filepath.unlink()
                logger.info(f"deleted_note_file: {filepath}")
        except Exception as e:
            # 文件删除失败只记录日志，不影响主业务
            logger.warning(f"failed_to_delete_note_file: {note.id}, {e}")

    # ==================== 查询操作 ====================

    def query(
        self,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        note_type: Optional[str] = None,
        is_archived: Optional[bool] = None,
        is_promoted: Optional[bool] = None,
        order_by: str = "updated_at DESC",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Note], int]:
        """
        条件查询笔记

        Args:
            search: 搜索关键词（标题和内容）
            tags: 标签筛选
            note_type: 笔记类型筛选
            is_archived: 归档状态筛选
            is_promoted: 是否已提炼为经验
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

        if note_type:
            builder.where("note_type", note_type)

        if is_archived is not None:
            builder.where("is_archived", is_archived)

        if is_promoted is not None:
            if is_promoted:
                builder.where_raw("promoted_to_experience_id IS NOT NULL", [])
            else:
                builder.where_raw("promoted_to_experience_id IS NULL", [])

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

    def get_tags(self, include_archived: bool = False) -> List[str]:
        """获取所有标签（去重）

        Args:
            include_archived: 是否包含已归档笔记的标签，默认 False
        """
        with self._cursor() as cursor:
            if include_archived:
                cursor.execute("SELECT DISTINCT tags FROM notes WHERE tags != ''")
            else:
                cursor.execute(
                    "SELECT DISTINCT tags FROM notes WHERE tags != '' AND is_archived = FALSE"
                )
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

    # ==================== 类型操作 ====================

    def get_by_type(
        self,
        note_type: str,
        limit: int = 50,
        include_archived: bool = False
    ) -> List[Note]:
        """
        按类型获取笔记

        Args:
            note_type: 笔记类型
            limit: 限制数量
            include_archived: 是否包含已归档的笔记

        Returns:
            笔记列表
        """
        with self._cursor() as cursor:
            if include_archived:
                cursor.execute(
                    '''SELECT * FROM notes
                    WHERE note_type = %s
                    ORDER BY updated_at DESC
                    LIMIT %s''',
                    (note_type, limit)
                )
            else:
                cursor.execute(
                    '''SELECT * FROM notes
                    WHERE note_type = %s AND is_archived = FALSE
                    ORDER BY updated_at DESC
                    LIMIT %s''',
                    (note_type, limit)
                )
            return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

    def archive(self, note_id: int) -> bool:
        """归档笔记"""
        return self.update(note_id, is_archived=True)

    def unarchive(self, note_id: int) -> bool:
        """取消归档笔记"""
        return self.update(note_id, is_archived=False)

    def set_promoted(self, note_id: int, experience_id: int) -> bool:
        """标记笔记已提炼为经验"""
        return self.update(note_id, promoted_to_experience_id=experience_id)

    def get_stats_extended(self) -> Dict[str, Any]:
        """
        获取扩展统计信息

        Returns:
            包含各类型笔记数量、归档数量等的统计字典
        """
        with self._cursor() as cursor:
            # 总数
            cursor.execute('SELECT COUNT(*) as count FROM notes')
            total = cursor.fetchone()['count']

            # 按类型统计
            cursor.execute('''
                SELECT note_type, COUNT(*) as count
                FROM notes
                GROUP BY note_type
            ''')
            type_counts = {row['note_type']: row['count'] for row in cursor.fetchall()}

            # 归档统计
            cursor.execute('''
                SELECT is_archived, COUNT(*) as count
                FROM notes
                GROUP BY is_archived
            ''')
            archive_rows = cursor.fetchall()
            archived_count = 0
            active_count = 0
            for row in archive_rows:
                if row['is_archived']:
                    archived_count = row['count']
                else:
                    active_count = row['count']

            # 已提炼为经验的笔记数
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM notes
                WHERE promoted_to_experience_id IS NOT NULL
            ''')
            promoted_count = cursor.fetchone()['count']

        return {
            "total": total,
            "active_count": active_count,
            "archived_count": archived_count,
            "promoted_count": promoted_count,
            "by_type": type_counts,
        }


# ==================== 单例管理 ====================

def get_note_store(database_url: Optional[str] = None) -> NoteStore:
    """获取笔记存储层单例"""
    return get_store_instance(NoteStore, "NoteStore", database_url=database_url)


def reset_note_store():
    """重置存储层单例（用于测试）"""
    reset_store_instance("NoteStore")
