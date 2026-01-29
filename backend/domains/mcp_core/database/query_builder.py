"""
SQL 查询构建器

提供安全、可组合的 SQL 查询构建功能：
- WHERE 条件构建（支持比较、空值、包含等）
- 分页处理
- 排序验证
- 参数安全
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QueryBuilder:
    """
    SQL 查询构建器

    使用示例:
        builder = QueryBuilder(
            table="factors",
            allowed_columns={"filename", "style", "llm_score"},
            numeric_fields={"llm_score"}
        )

        sql, params = (
            builder
            .where("style", "动量")
            .where("llm_score", ">=4.0")
            .order_by("llm_score DESC")
            .paginate(page=1, page_size=20)
            .build()
        )
    """

    table: str
    allowed_columns: set[str]
    numeric_fields: set[str] = field(default_factory=set)

    # 内部状态
    _select: str = "*"
    _where_clauses: list[str] = field(default_factory=list)
    _params: list[Any] = field(default_factory=list)
    _order_by: str | None = None
    _limit: int | None = None
    _offset: int | None = None

    def __post_init__(self):
        # 确保使用新列表，避免共享状态
        self._where_clauses = []
        self._params = []

    def select(self, columns: str = "*") -> 'QueryBuilder':
        """设置 SELECT 列"""
        self._select = columns
        return self

    def where(self, field_name: str, value: Any) -> 'QueryBuilder':
        """
        添加 WHERE 条件

        支持的值格式:
        - 普通值: 等于比较
        - ">=value", "<=value", ">value", "<value": 比较运算
        - "empty": 空值检查
        - "not_empty": 非空检查
        - "contains:keyword": 包含（ILIKE）
        - 列表: 多个条件 AND 组合

        Args:
            field_name: 字段名
            value: 值或条件表达式

        Returns:
            self（链式调用）
        """
        if field_name not in self.allowed_columns:
            logger.warning(f"Invalid filter field ignored: {field_name}")
            return self

        # 支持列表形式的多条件
        values = value if isinstance(value, list) else [value]

        for v in values:
            clause, params = self._parse_condition(field_name, v)
            if clause:
                self._where_clauses.append(clause)
                self._params.extend(params)

        return self

    def where_raw(self, clause: str, params: list[Any] = None) -> 'QueryBuilder':
        """
        添加原始 WHERE 条件（谨慎使用）

        Args:
            clause: SQL 条件子句
            params: 参数列表

        Returns:
            self
        """
        self._where_clauses.append(clause)
        if params:
            self._params.extend(params)
        return self

    def order_by(self, order: str) -> 'QueryBuilder':
        """
        设置排序

        Args:
            order: 排序表达式，如 "llm_score DESC"

        Returns:
            self
        """
        order_parts = order.strip().split()
        if not order_parts:
            return self

        column = order_parts[0].lower()
        direction = order_parts[1].upper() if len(order_parts) > 1 else 'ASC'

        if column not in self.allowed_columns:
            logger.warning(f"Invalid order column ignored: {column}")
            return self

        if direction not in ('ASC', 'DESC'):
            logger.warning(f"Invalid order direction ignored: {direction}")
            return self

        self._order_by = f'{column} {direction}'
        return self

    def paginate(self, page: int = 1, page_size: int = 20) -> 'QueryBuilder':
        """
        设置分页

        Args:
            page: 页码（从1开始）
            page_size: 每页数量

        Returns:
            self
        """
        self._limit = page_size
        self._offset = (page - 1) * page_size
        return self

    def limit(self, limit: int) -> 'QueryBuilder':
        """设置 LIMIT"""
        self._limit = limit
        return self

    def offset(self, offset: int) -> 'QueryBuilder':
        """设置 OFFSET"""
        self._offset = offset
        return self

    def build(self) -> tuple[str, list[Any]]:
        """
        构建 SQL 查询

        Returns:
            (sql, params) 元组
        """
        sql = f'SELECT {self._select} FROM {self.table}'

        if self._where_clauses:
            sql += ' WHERE ' + ' AND '.join(self._where_clauses)

        if self._order_by:
            sql += f' ORDER BY {self._order_by}'

        params = list(self._params)

        if self._limit is not None:
            sql += ' LIMIT %s'
            params.append(self._limit)

        if self._offset is not None:
            sql += ' OFFSET %s'
            params.append(self._offset)

        return sql, params

    def build_count(self) -> tuple[str, list[Any]]:
        """
        构建 COUNT 查询

        Returns:
            (sql, params) 元组
        """
        sql = f'SELECT COUNT(*) as count FROM {self.table}'

        if self._where_clauses:
            sql += ' WHERE ' + ' AND '.join(self._where_clauses)

        return sql, list(self._params)

    def reset(self) -> 'QueryBuilder':
        """重置构建器状态"""
        self._select = "*"
        self._where_clauses = []
        self._params = []
        self._order_by = None
        self._limit = None
        self._offset = None
        return self

    def _parse_condition(
        self,
        field_name: str,
        value: Any
    ) -> tuple[str | None, list[Any]]:
        """
        解析条件值，返回 SQL 子句和参数

        Args:
            field_name: 字段名
            value: 条件值

        Returns:
            (clause, params) 元组
        """
        if not isinstance(value, str):
            # 非字符串值，直接等于比较
            if isinstance(value, bool):
                return f'{field_name} = %s', [value]
            return f'{field_name} = %s', [value]

        # 比较运算符
        if value.startswith('>='):
            return f'{field_name} >= %s', [self._parse_number(value[2:])]
        if value.startswith('<='):
            return f'{field_name} <= %s', [self._parse_number(value[2:])]
        if value.startswith('>'):
            return f'{field_name} > %s', [self._parse_number(value[1:])]
        if value.startswith('<'):
            return f'{field_name} < %s', [self._parse_number(value[1:])]

        # 空值检查
        if value == 'empty':
            if field_name in self.numeric_fields:
                return f'{field_name} IS NULL', []
            return f"({field_name} IS NULL OR {field_name} = '')", []

        if value == 'not_empty':
            if field_name in self.numeric_fields:
                return f'{field_name} IS NOT NULL', []
            return f"({field_name} IS NOT NULL AND {field_name} != '')", []

        # 包含搜索
        if value.startswith('contains:'):
            keyword = value[9:]
            return f'{field_name} ILIKE %s', [f'%{keyword}%']

        # 普通等于
        return f'{field_name} = %s', [value]

    def _parse_number(self, value: str) -> int | float:
        """解析数值"""
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            return float(value)


def create_query_builder(
    table: str,
    allowed_columns: set[str],
    numeric_fields: set[str] = None
) -> QueryBuilder:
    """
    创建查询构建器的工厂函数

    Args:
        table: 表名
        allowed_columns: 允许的列名集合
        numeric_fields: 数值类型字段集合

    Returns:
        QueryBuilder 实例
    """
    return QueryBuilder(
        table=table,
        allowed_columns=allowed_columns,
        numeric_fields=numeric_fields or set()
    )
