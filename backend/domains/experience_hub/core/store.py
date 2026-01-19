"""
经验存储层 - PostgreSQL 数据源

提供经验的持久化存储和查询功能。
继承 mcp_core.BaseStore，复用连接管理和通用 CRUD。
"""

import json
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
    Experience,
    ExperienceContent,
    ExperienceContext,
    ExperienceLink,
)

logger = logging.getLogger(__name__)


class ExperienceStore(BaseStore[Experience]):
    """
    经验存储层 - PostgreSQL 数据源

    继承 BaseStore，提供经验的 CRUD 操作和查询功能。
    """

    table_name = "experiences"

    allowed_columns = {
        'id', 'uuid', 'title',
        'content', 'context',
        'source_type', 'source_ref',
        'created_at', 'updated_at'
    }

    numeric_fields = {'id'}

    def _row_to_entity(self, row: Dict[str, Any]) -> Experience:
        """将数据库行转换为 Experience 对象"""
        content = row.get('content')
        if isinstance(content, str):
            content = ExperienceContent.from_json(content)
        elif isinstance(content, dict):
            content = ExperienceContent.from_dict(content)
        else:
            content = ExperienceContent()

        context = row.get('context')
        if isinstance(context, str):
            context = ExperienceContext.from_json(context)
        elif isinstance(context, dict):
            context = ExperienceContext.from_dict(context)
        else:
            context = ExperienceContext()

        return Experience(
            id=row.get('id'),
            uuid=row.get('uuid', ''),
            title=row.get('title', ''),
            content=content,
            context=context,
            source_type=row.get('source_type', ''),
            source_ref=row.get('source_ref', ''),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
        )

    def _create_query_builder(self) -> QueryBuilder:
        """创建查询构建器"""
        return QueryBuilder(
            table=self.table_name,
            allowed_columns=self.allowed_columns,
            numeric_fields=self.numeric_fields
        )

    # ==================== 基本 CRUD ====================

    def get(self, experience_id: int) -> Optional[Experience]:
        """获取单个经验（通过 ID）"""
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT * FROM experiences WHERE id = %s',
                (experience_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entity(dict(row))
        return None

    def get_by_uuid(self, uuid: str) -> Optional[Experience]:
        """获取单个经验（通过 UUID）"""
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT * FROM experiences WHERE uuid = %s',
                (uuid,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entity(dict(row))
        return None

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Experience]:
        """获取所有经验"""
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT * FROM experiences ORDER BY updated_at DESC LIMIT %s OFFSET %s',
                (limit, offset)
            )
            return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

    def add(self, experience: Experience) -> Optional[int]:
        """添加经验，返回新经验的 ID"""
        experience.created_at = datetime.now()
        experience.updated_at = datetime.now()

        content_json = experience.content.to_json() if isinstance(experience.content, ExperienceContent) else json.dumps(experience.content)
        context_json = experience.context.to_json() if isinstance(experience.context, ExperienceContext) else json.dumps(experience.context)

        try:
            with self._cursor() as cursor:
                cursor.execute('''
                    INSERT INTO experiences (
                        uuid, title, content, context,
                        source_type, source_ref,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    experience.uuid, experience.title,
                    content_json, context_json,
                    experience.source_type, experience.source_ref,
                    experience.created_at, experience.updated_at
                ))
                result = cursor.fetchone()
                return result['id'] if result else None
        except psycopg2.IntegrityError as e:
            logger.error(f"添加经验失败: {e}")
            return None

    def update(self, experience_id: int, **fields) -> bool:
        """更新经验字段"""
        if not fields:
            return False

        safe_fields = {k: v for k, v in fields.items() if k in self.allowed_columns}
        if not safe_fields:
            logger.warning(f"No valid fields to update: {list(fields.keys())}")
            return False

        if 'content' in safe_fields and isinstance(safe_fields['content'], ExperienceContent):
            safe_fields['content'] = safe_fields['content'].to_json()
        if 'context' in safe_fields and isinstance(safe_fields['context'], ExperienceContext):
            safe_fields['context'] = safe_fields['context'].to_json()

        safe_fields['updated_at'] = datetime.now()

        set_clause = ', '.join(f'{k} = %s' for k in safe_fields.keys())
        values = list(safe_fields.values()) + [experience_id]

        with self._cursor() as cursor:
            cursor.execute(
                f'UPDATE experiences SET {set_clause} WHERE id = %s',
                values
            )
            return cursor.rowcount > 0

    def delete(self, experience_id: int) -> bool:
        """删除经验"""
        with self._cursor() as cursor:
            cursor.execute(
                'DELETE FROM experience_links WHERE experience_id = %s',
                (experience_id,)
            )
            cursor.execute(
                'DELETE FROM experiences WHERE id = %s',
                (experience_id,)
            )
            return cursor.rowcount > 0

    # ==================== 查询操作 ====================

    def query(
        self,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source_type: Optional[str] = None,
        market_regime: Optional[str] = None,
        factor_styles: Optional[List[str]] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        updated_after: Optional[datetime] = None,
        updated_before: Optional[datetime] = None,
        order_by: str = "updated_at DESC",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Experience], int]:
        """
        条件查询经验

        Args:
            search: 搜索关键词（标题和内容）
            tags: 标签筛选
            source_type: 来源类型筛选
            market_regime: 市场环境筛选
            factor_styles: 因子风格筛选
            created_after: 创建时间起始
            created_before: 创建时间截止
            updated_after: 更新时间起始
            updated_before: 更新时间截止
            order_by: 排序
            limit: 限制数量
            offset: 偏移量

        Returns:
            (经验列表, 总数)
        """
        builder = self._create_query_builder()

        if search:
            builder.where_raw(
                "(title ILIKE %s OR content::text ILIKE %s)",
                [f'%{search}%', f'%{search}%']
            )

        if source_type:
            builder.where("source_type", source_type)

        # 标签筛选（JSONB 查询）
        if tags:
            for tag in tags:
                builder.where_raw("context->'tags' ? %s", [tag])

        if market_regime:
            builder.where_raw("context->>'market_regime' = %s", [market_regime])

        if factor_styles:
            for style in factor_styles:
                builder.where_raw("context->'factor_styles' ? %s", [style])

        # 时间筛选
        if created_after:
            builder.where_raw("created_at >= %s", [created_after])
        if created_before:
            builder.where_raw("created_at <= %s", [created_before])
        if updated_after:
            builder.where_raw("updated_at >= %s", [updated_after])
        if updated_before:
            builder.where_raw("updated_at <= %s", [updated_before])

        count_sql, count_params = builder.build_count()
        with self._cursor() as cursor:
            cursor.execute(count_sql, count_params)
            total = cursor.fetchone()['count']

        builder.order_by(order_by)
        builder.limit(limit)
        builder.offset(offset)

        sql, params = builder.build()

        with self._cursor() as cursor:
            cursor.execute(sql, params)
            experiences = [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

        return experiences, total

    def search(self, keyword: str, limit: int = 20) -> List[Experience]:
        """全文搜索经验"""
        experiences, _ = self.query(search=keyword, limit=limit)
        return experiences

    def get_by_source(self, source_type: str, source_ref: str) -> List[Experience]:
        """根据来源获取经验"""
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT * FROM experiences WHERE source_type = %s AND source_ref = %s ORDER BY updated_at DESC',
                (source_type, source_ref)
            )
            return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

    def get_all_tags(self) -> List[str]:
        """获取所有标签（去重）"""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT jsonb_array_elements_text(context->'tags') as tag
                FROM experiences
                WHERE context->'tags' IS NOT NULL
                ORDER BY tag
            """)
            return [row['tag'] for row in cursor.fetchall()]

    def count(self) -> int:
        """统计经验总数"""
        with self._cursor() as cursor:
            cursor.execute('SELECT COUNT(*) as count FROM experiences')
            return cursor.fetchone()['count']

    # ==================== 关联管理 ====================

    def add_link(self, link: ExperienceLink) -> Optional[int]:
        """添加经验关联"""
        link.created_at = datetime.now()

        try:
            with self._cursor() as cursor:
                cursor.execute('''
                    INSERT INTO experience_links (
                        experience_id, experience_uuid, entity_type, entity_id, relation, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    link.experience_id, link.experience_uuid,
                    link.entity_type, link.entity_id, link.relation, link.created_at
                ))
                result = cursor.fetchone()
                return result['id'] if result else None
        except psycopg2.IntegrityError as e:
            logger.error(f"添加经验关联失败: {e}")
            return None

    def get_links(self, experience_id: int) -> List[ExperienceLink]:
        """获取经验的所有关联"""
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT * FROM experience_links WHERE experience_id = %s',
                (experience_id,)
            )
            return [ExperienceLink.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_experiences_by_entity(
        self,
        entity_type: str,
        entity_id: str
    ) -> List[Experience]:
        """根据关联实体获取经验"""
        with self._cursor() as cursor:
            cursor.execute('''
                SELECT e.* FROM experiences e
                JOIN experience_links l ON e.id = l.experience_id
                WHERE l.entity_type = %s AND l.entity_id = %s
                ORDER BY e.updated_at DESC
            ''', (entity_type, entity_id))
            return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

    def delete_link(self, link_id: int) -> bool:
        """删除经验关联"""
        with self._cursor() as cursor:
            cursor.execute(
                'DELETE FROM experience_links WHERE id = %s',
                (link_id,)
            )
            return cursor.rowcount > 0


# ==================== 单例管理 ====================

def get_experience_store(database_url: Optional[str] = None) -> ExperienceStore:
    """获取经验存储层单例"""
    return get_store_instance(ExperienceStore, "ExperienceStore", database_url=database_url)


def reset_experience_store():
    """重置存储层单例（用于测试）"""
    reset_store_instance("ExperienceStore")
