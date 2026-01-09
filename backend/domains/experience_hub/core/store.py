"""
经验存储层 - PostgreSQL 数据源

提供经验的持久化存储和查询功能。
继承 mcp_core.BaseStore，复用连接管理和通用 CRUD。
支持向量检索（通过 pgvector）。
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
    ExperienceLevel,
    ExperienceStatus,
)

logger = logging.getLogger(__name__)


class ExperienceStore(BaseStore[Experience]):
    """
    经验存储层 - PostgreSQL 数据源

    继承 BaseStore，提供经验的 CRUD 操作、查询和向量检索功能。
    """

    # BaseStore 配置
    table_name = "experiences"

    allowed_columns = {
        'id', 'uuid', 'title', 'experience_level', 'category',
        'content', 'context', 'source_type', 'source_ref',
        'confidence', 'validation_count', 'last_validated',
        'status', 'deprecated_reason',
        'created_at', 'updated_at'
    }

    numeric_fields = {'id', 'confidence', 'validation_count'}

    # 向后兼容别名
    ALLOWED_COLUMNS = allowed_columns

    def _row_to_entity(self, row: Dict[str, Any]) -> Experience:
        """将数据库行转换为 Experience 对象"""
        # 处理 JSONB 字段
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
            experience_level=row.get('experience_level', ExperienceLevel.OPERATIONAL.value),
            category=row.get('category', ''),
            content=content,
            context=context,
            source_type=row.get('source_type', ''),
            source_ref=row.get('source_ref', ''),
            confidence=row.get('confidence', 0.5),
            validation_count=row.get('validation_count', 0),
            last_validated=row.get('last_validated'),
            status=row.get('status', ExperienceStatus.DRAFT.value),
            deprecated_reason=row.get('deprecated_reason', ''),
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

        # 序列化 JSONB 字段
        content_json = experience.content.to_json() if isinstance(experience.content, ExperienceContent) else json.dumps(experience.content)
        context_json = experience.context.to_json() if isinstance(experience.context, ExperienceContext) else json.dumps(experience.context)

        try:
            with self._cursor() as cursor:
                cursor.execute('''
                    INSERT INTO experiences (
                        uuid, title, experience_level, category,
                        content, context, source_type, source_ref,
                        confidence, validation_count, last_validated,
                        status, deprecated_reason,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    experience.uuid, experience.title, experience.experience_level,
                    experience.category, content_json, context_json,
                    experience.source_type, experience.source_ref,
                    experience.confidence, experience.validation_count, experience.last_validated,
                    experience.status, experience.deprecated_reason,
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

        # 安全验证字段名，防止 SQL 注入
        safe_fields = {k: v for k, v in fields.items() if k in self.allowed_columns}
        if not safe_fields:
            logger.warning(f"No valid fields to update: {list(fields.keys())}")
            return False

        # 处理 JSONB 字段
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
            # 先删除关联
            cursor.execute(
                'DELETE FROM experience_links WHERE experience_id = %s',
                (experience_id,)
            )
            # 再删除经验
            cursor.execute(
                'DELETE FROM experiences WHERE id = %s',
                (experience_id,)
            )
            return cursor.rowcount > 0

    # ==================== 查询操作 ====================

    def query(
        self,
        search: Optional[str] = None,
        experience_level: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        market_regime: Optional[str] = None,
        factor_styles: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        include_deprecated: bool = False,
        order_by: str = "updated_at DESC",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Experience], int]:
        """
        条件查询经验

        Args:
            search: 搜索关键词（标题和内容）
            experience_level: 经验层级筛选
            category: 分类筛选
            status: 状态筛选
            source_type: 来源类型筛选
            market_regime: 市场环境筛选
            factor_styles: 因子风格筛选
            min_confidence: 最低置信度
            include_deprecated: 是否包含已废弃
            order_by: 排序
            limit: 限制数量
            offset: 偏移量

        Returns:
            (经验列表, 总数)
        """
        builder = self._create_query_builder()

        # 文本搜索
        if search:
            builder.where_raw(
                "(title ILIKE %s OR content::text ILIKE %s)",
                [f'%{search}%', f'%{search}%']
            )

        # 筛选条件
        if experience_level:
            builder.where("experience_level", experience_level)

        if category:
            builder.where("category", category)

        if status:
            builder.where("status", status)
        elif not include_deprecated:
            builder.where_raw("status != %s", [ExperienceStatus.DEPRECATED.value])

        if source_type:
            builder.where("source_type", source_type)

        if min_confidence > 0:
            builder.where_raw("confidence >= %s", [min_confidence])

        # 上下文筛选（JSONB 查询）
        if market_regime:
            builder.where_raw("context->>'market_regime' = %s", [market_regime])

        if factor_styles:
            for style in factor_styles:
                builder.where_raw("context->'factor_styles' ? %s", [style])

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
            experiences = [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

        return experiences, total

    def search(self, keyword: str, limit: int = 20) -> List[Experience]:
        """全文搜索经验"""
        experiences, _ = self.query(search=keyword, limit=limit)
        return experiences

    def get_by_level(
        self,
        level: str,
        include_deprecated: bool = False,
        limit: int = 50
    ) -> List[Experience]:
        """根据层级获取经验"""
        experiences, _ = self.query(
            experience_level=level,
            include_deprecated=include_deprecated,
            limit=limit
        )
        return experiences

    def get_by_source(self, source_type: str, source_ref: str) -> List[Experience]:
        """根据来源获取经验"""
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT * FROM experiences WHERE source_type = %s AND source_ref = %s ORDER BY updated_at DESC',
                (source_type, source_ref)
            )
            return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

    def get_categories(self) -> List[str]:
        """获取所有分类（去重）"""
        with self._cursor() as cursor:
            cursor.execute("SELECT DISTINCT category FROM experiences WHERE category != ''")
            return [row['category'] for row in cursor.fetchall()]

    def count(self) -> int:
        """统计经验总数"""
        with self._cursor() as cursor:
            cursor.execute('SELECT COUNT(*) as count FROM experiences')
            return cursor.fetchone()['count']

    def count_by_status(self) -> Dict[str, int]:
        """按状态统计经验数量"""
        with self._cursor() as cursor:
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM experiences
                GROUP BY status
            ''')
            return {row['status']: row['count'] for row in cursor.fetchall()}

    def count_by_level(self) -> Dict[str, int]:
        """按层级统计经验数量"""
        with self._cursor() as cursor:
            cursor.execute('''
                SELECT experience_level, COUNT(*) as count
                FROM experiences
                GROUP BY experience_level
            ''')
            return {row['experience_level']: row['count'] for row in cursor.fetchall()}

    # ==================== 验证与废弃 ====================

    def validate(
        self,
        experience_id: int,
        confidence_delta: float = 0.1
    ) -> Optional[Experience]:
        """
        验证经验

        增加验证次数，提升置信度，更新状态为 validated。
        """
        experience = self.get(experience_id)
        if experience is None:
            return None

        new_confidence = min(1.0, experience.confidence + confidence_delta)
        now = datetime.now()

        with self._cursor() as cursor:
            cursor.execute('''
                UPDATE experiences
                SET validation_count = validation_count + 1,
                    last_validated = %s,
                    confidence = %s,
                    status = %s,
                    updated_at = %s
                WHERE id = %s
            ''', (now, new_confidence, ExperienceStatus.VALIDATED.value, now, experience_id))

        return self.get(experience_id)

    def deprecate(self, experience_id: int, reason: str) -> Optional[Experience]:
        """
        废弃经验

        将状态更新为 deprecated，记录废弃原因。
        """
        experience = self.get(experience_id)
        if experience is None:
            return None

        now = datetime.now()

        with self._cursor() as cursor:
            cursor.execute('''
                UPDATE experiences
                SET status = %s,
                    deprecated_reason = %s,
                    updated_at = %s
                WHERE id = %s
            ''', (ExperienceStatus.DEPRECATED.value, reason, now, experience_id))

        return self.get(experience_id)

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

    # ==================== 向量检索 ====================

    def vector_search(
        self,
        embedding: List[float],
        top_k: int = 10,
        min_confidence: float = 0.0,
        include_deprecated: bool = False
    ) -> List[Tuple[Experience, float]]:
        """
        向量相似度检索

        Args:
            embedding: 查询向量
            top_k: 返回数量
            min_confidence: 最低置信度
            include_deprecated: 是否包含已废弃

        Returns:
            [(经验, 相似度分数), ...]
        """
        # 构建过滤条件
        conditions = ["1=1"]
        params: List[Any] = []

        if min_confidence > 0:
            conditions.append("e.confidence >= %s")
            params.append(min_confidence)

        if not include_deprecated:
            conditions.append("e.status != %s")
            params.append(ExperienceStatus.DEPRECATED.value)

        where_clause = " AND ".join(conditions)

        # 向量相似度查询（使用 pgvector）
        # 假设 embedding 存储在 experience_embeddings 表中
        sql = f'''
            SELECT e.*, 1 - (ee.embedding <=> %s::vector) as similarity
            FROM experiences e
            JOIN experience_embeddings ee ON e.id = ee.experience_id
            WHERE {where_clause}
            ORDER BY ee.embedding <=> %s::vector
            LIMIT %s
        '''

        params = [embedding] + params + [embedding, top_k]

        try:
            with self._cursor() as cursor:
                cursor.execute(sql, params)
                results = []
                for row in cursor.fetchall():
                    experience = self._row_to_entity(dict(row))
                    similarity = row.get('similarity', 0)
                    results.append((experience, similarity))
                return results
        except Exception as e:
            logger.warning(f"向量检索失败（可能表不存在）: {e}")
            return []

    def store_embedding(self, experience_id: int, embedding: List[float], model: str = ""):
        """存储经验的向量表示"""
        try:
            with self._cursor() as cursor:
                cursor.execute('''
                    INSERT INTO experience_embeddings (experience_id, embedding, model, created_at)
                    VALUES (%s, %s::vector, %s, %s)
                    ON CONFLICT (experience_id) DO UPDATE
                    SET embedding = EXCLUDED.embedding,
                        model = EXCLUDED.model,
                        created_at = EXCLUDED.created_at
                ''', (experience_id, embedding, model, datetime.now()))
                return True
        except Exception as e:
            logger.error(f"存储向量失败: {e}")
            return False


# ==================== 单例管理 ====================

def get_experience_store(database_url: Optional[str] = None) -> ExperienceStore:
    """获取经验存储层单例"""
    return get_store_instance(ExperienceStore, "ExperienceStore", database_url=database_url)


def reset_experience_store():
    """重置存储层单例（用于测试）"""
    reset_store_instance("ExperienceStore")
