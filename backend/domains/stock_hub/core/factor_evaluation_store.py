"""
因子评估存储层 - PostgreSQL 数据源

提供因子评估的持久化存储和查询功能。
继承 mcp_core.BaseStore，复用连接管理和通用 CRUD。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from domains.mcp_core.base.store import (
    BaseStore,
    get_store_instance,
    reset_store_instance,
)
from domains.mcp_core.database.query_builder import QueryBuilder

from .factor_evaluation_models import (
    FactorEvaluation,
    FactorEvaluationContent,
)

logger = logging.getLogger(__name__)


class FactorEvaluationStore(BaseStore[FactorEvaluation]):
    """
    因子评估存储层 - PostgreSQL 数据源

    继承 BaseStore，提供因子评估的 CRUD 操作和查询功能。
    """

    table_name = "factor_evaluations"

    allowed_columns = {
        'id', 'uuid', 'factor_name', 'title',
        'content', 'tags',
        'created_at', 'updated_at'
    }

    numeric_fields = {'id'}

    def _row_to_entity(self, row: dict[str, Any]) -> FactorEvaluation:
        """将数据库行转换为 FactorEvaluation 对象"""
        content = row.get('content')
        if isinstance(content, str):
            content = FactorEvaluationContent.from_json(content)
        elif isinstance(content, dict):
            content = FactorEvaluationContent.from_dict(content)
        else:
            content = FactorEvaluationContent()

        tags = row.get('tags')
        if isinstance(tags, str):
            tags = json.loads(tags)
        elif not isinstance(tags, list):
            tags = []

        return FactorEvaluation(
            id=row.get('id'),
            uuid=row.get('uuid', ''),
            factor_name=row.get('factor_name', ''),
            title=row.get('title', ''),
            content=content,
            tags=tags,
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

    def get(self, evaluation_id: int) -> FactorEvaluation | None:
        """获取单个因子评估（通过 ID）"""
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT * FROM factor_evaluations WHERE id = %s',
                (evaluation_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entity(dict(row))
        return None

    def get_by_uuid(self, uuid: str) -> FactorEvaluation | None:
        """获取单个因子评估（通过 UUID）"""
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT * FROM factor_evaluations WHERE uuid = %s',
                (uuid,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entity(dict(row))
        return None

    def add(self, evaluation: FactorEvaluation) -> int | None:
        """添加因子评估，返回新记录的 ID"""
        evaluation.created_at = datetime.now()
        evaluation.updated_at = datetime.now()

        content_json = evaluation.content.to_json() if isinstance(evaluation.content, FactorEvaluationContent) else json.dumps(evaluation.content)
        tags_json = json.dumps(evaluation.tags, ensure_ascii=False)

        try:
            with self._cursor() as cursor:
                cursor.execute('''
                    INSERT INTO factor_evaluations (
                        uuid, factor_name, title, content, tags,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    evaluation.uuid, evaluation.factor_name,
                    evaluation.title,
                    content_json, tags_json,
                    evaluation.created_at, evaluation.updated_at
                ))
                result = cursor.fetchone()
                return result['id'] if result else None
        except psycopg2.IntegrityError as e:
            logger.error(f"添加因子评估失败: {e}")
            return None

    def update(self, evaluation_id: int, **fields) -> bool:
        """更新因子评估字段"""
        if not fields:
            return False

        safe_fields = {k: v for k, v in fields.items() if k in self.allowed_columns}
        if not safe_fields:
            logger.warning(f"No valid fields to update: {list(fields.keys())}")
            return False

        if 'content' in safe_fields and isinstance(safe_fields['content'], FactorEvaluationContent):
            safe_fields['content'] = safe_fields['content'].to_json()
        if 'tags' in safe_fields and isinstance(safe_fields['tags'], list):
            safe_fields['tags'] = json.dumps(safe_fields['tags'], ensure_ascii=False)

        safe_fields['updated_at'] = datetime.now()

        set_clause = ', '.join(f'{k} = %s' for k in safe_fields)
        values = list(safe_fields.values()) + [evaluation_id]

        with self._cursor() as cursor:
            cursor.execute(
                f'UPDATE factor_evaluations SET {set_clause} WHERE id = %s',
                values
            )
            return cursor.rowcount > 0

    def delete(self, evaluation_id: int) -> bool:
        """删除因子评估"""
        with self._cursor() as cursor:
            cursor.execute(
                'DELETE FROM factor_evaluations WHERE id = %s',
                (evaluation_id,)
            )
            return cursor.rowcount > 0

    def delete_by_uuid(self, uuid: str) -> bool:
        """删除因子评估（通过 UUID）"""
        with self._cursor() as cursor:
            cursor.execute(
                'DELETE FROM factor_evaluations WHERE uuid = %s',
                (uuid,)
            )
            return cursor.rowcount > 0

    # ==================== 查询操作 ====================

    def query(
        self,
        factor_name: str | None = None,
        tags: list[str] | None = None,
        search: str | None = None,
        order_by: str = "updated_at DESC",
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[FactorEvaluation], int]:
        """
        条件查询因子评估

        Args:
            factor_name: 因子名称精确匹配
            tags: 标签筛选
            search: 搜索关键词（标题和内容）
            order_by: 排序
            limit: 限制数量
            offset: 偏移量

        Returns:
            (因子评估列表, 总数)
        """
        builder = self._create_query_builder()

        if factor_name:
            builder.where("factor_name", factor_name)

        if search:
            builder.where_raw(
                "(title ILIKE %s OR content::text ILIKE %s)",
                [f'%{search}%', f'%{search}%']
            )

        # 标签筛选（JSONB 查询）
        if tags:
            for tag in tags:
                builder.where_raw("tags ? %s", [tag])

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
            evaluations = [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

        return evaluations, total

    def get_all_tags(self) -> list[str]:
        """获取所有标签（去重）"""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT jsonb_array_elements_text(tags) as tag
                FROM factor_evaluations
                WHERE tags IS NOT NULL
                ORDER BY tag
            """)
            return [row['tag'] for row in cursor.fetchall()]

    def count(self) -> int:
        """统计因子评估总数"""
        with self._cursor() as cursor:
            cursor.execute('SELECT COUNT(*) as count FROM factor_evaluations')
            return cursor.fetchone()['count']

    # ==================== Schema 初始化 ====================

    def init_schema(self):
        """初始化数据库表结构"""
        schema_path = Path(__file__).parent / "factor_evaluation_schema.sql"
        if schema_path.exists():
            with self._cursor() as cursor:
                cursor.execute(schema_path.read_text(encoding="utf-8"))


# ==================== 单例管理 ====================

def get_factor_evaluation_store(database_url: str | None = None) -> FactorEvaluationStore:
    """获取因子评估存储层单例"""
    return get_store_instance(FactorEvaluationStore, "FactorEvaluationStore", database_url=database_url)


def reset_factor_evaluation_store():
    """重置存储层单例（用于测试）"""
    reset_store_instance("FactorEvaluationStore")
