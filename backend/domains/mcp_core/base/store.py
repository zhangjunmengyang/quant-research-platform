"""
存储层基类

提供 PostgreSQL 存储层的通用功能：
- 连接管理
- 游标上下文管理器
- 单例模式支持
- SQL 安全验证
"""

import os
import logging
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, TypeVar, Generic
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

T = TypeVar('T')


def get_database_url() -> str:
    """获取数据库连接 URL"""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://quant:quant123@localhost:5432/quant"
    )


class ThreadSafeConnectionMixin:
    """
    线程安全的数据库连接管理 Mixin

    使用 threading.local() 让每个线程拥有独立的数据库连接，
    避免 asyncio.to_thread() 多线程环境下的连接竞争和死锁。

    使用方法：
        class MyStore(ThreadSafeConnectionMixin):
            def __init__(self, database_url=None):
                self._init_connection(database_url)
                # ... 其他初始化
    """

    def _init_connection(self, database_url: Optional[str] = None):
        """初始化连接管理"""
        self.database_url = database_url or get_database_url()
        self._local = threading.local()

    def _get_connection(self) -> psycopg2.extensions.connection:
        """获取当前线程的数据库连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None or self._local.conn.closed:
            self._local.conn = psycopg2.connect(self.database_url)
            self._local.conn.autocommit = False
        return self._local.conn

    @contextmanager
    def _cursor(self):
        """获取游标的上下文管理器"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def close(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn and not self._local.conn.closed:
            self._local.conn.close()
            self._local.conn = None


class BaseStore(ThreadSafeConnectionMixin, ABC, Generic[T]):
    """
    存储层基类

    提供 PostgreSQL 数据库操作的通用功能，子类需要实现：
    - table_name: 表名
    - allowed_columns: 允许的列名白名单
    - _row_to_entity: 行数据转实体的方法

    使用示例:
        class FactorStore(BaseStore[Factor]):
            table_name = "factors"
            allowed_columns = {"filename", "style", ...}

            def _row_to_entity(self, row: Dict) -> Factor:
                return Factor(**row)
    """

    # 子类必须定义
    table_name: str = ""
    allowed_columns: Set[str] = set()

    # 数值类型字段（用于 empty/not_empty 查询时区分 NULL 检查逻辑）
    numeric_fields: Set[str] = set()

    def __init__(self, database_url: Optional[str] = None):
        """
        初始化存储层

        Args:
            database_url: PostgreSQL 连接 URL，默认从环境变量获取
        """
        self._init_connection(database_url)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== 抽象方法 ====================

    @abstractmethod
    def _row_to_entity(self, row: Dict[str, Any]) -> T:
        """
        将数据库行转换为实体对象

        Args:
            row: 数据库行（字典格式）

        Returns:
            实体对象
        """
        pass

    # ==================== 通用 CRUD ====================

    def get_by_id(self, id_field: str, id_value: Any) -> Optional[T]:
        """
        通过 ID 获取单个实体

        Args:
            id_field: ID 字段名
            id_value: ID 值

        Returns:
            实体对象或 None
        """
        if id_field not in self.allowed_columns:
            logger.warning(f"Invalid id field: {id_field}")
            return None

        with self._cursor() as cursor:
            cursor.execute(
                f'SELECT * FROM {self.table_name} WHERE {id_field} = %s',
                (id_value,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entity(dict(row))
        return None

    def get_all(
        self,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[T]:
        """
        获取所有实体

        Args:
            order_by: 排序字段
            limit: 限制数量
            offset: 偏移量

        Returns:
            实体列表
        """
        sql = f'SELECT * FROM {self.table_name}'

        if order_by:
            safe_order = self._validate_order_by(order_by)
            if safe_order:
                sql += f' ORDER BY {safe_order}'

        params = []
        if limit is not None:
            sql += ' LIMIT %s'
            params.append(limit)
        if offset is not None:
            sql += ' OFFSET %s'
            params.append(offset)

        with self._cursor() as cursor:
            cursor.execute(sql, params)
            return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]

    def delete_by_id(self, id_field: str, id_value: Any) -> bool:
        """
        通过 ID 删除实体

        Args:
            id_field: ID 字段名
            id_value: ID 值

        Returns:
            是否删除成功
        """
        if id_field not in self.allowed_columns:
            logger.warning(f"Invalid id field: {id_field}")
            return False

        with self._cursor() as cursor:
            cursor.execute(
                f'DELETE FROM {self.table_name} WHERE {id_field} = %s',
                (id_value,)
            )
            return cursor.rowcount > 0

    def update_by_id(self, id_field: str, id_value: Any, **fields) -> bool:
        """
        通过 ID 更新实体字段

        Args:
            id_field: ID 字段名
            id_value: ID 值
            **fields: 要更新的字段

        Returns:
            是否更新成功
        """
        if not fields:
            return False

        if id_field not in self.allowed_columns:
            logger.warning(f"Invalid id field: {id_field}")
            return False

        # 安全验证字段名
        safe_fields = {k: v for k, v in fields.items() if k in self.allowed_columns}
        if not safe_fields:
            logger.warning(f"No valid fields to update: {list(fields.keys())}")
            return False

        # 自动更新 updated_at
        if 'updated_at' in self.allowed_columns:
            safe_fields['updated_at'] = datetime.now()

        set_clause = ', '.join(f'{k} = %s' for k in safe_fields.keys())
        values = list(safe_fields.values()) + [id_value]

        with self._cursor() as cursor:
            cursor.execute(
                f'UPDATE {self.table_name} SET {set_clause} WHERE {id_field} = %s',
                values
            )
            return cursor.rowcount > 0

    def count(self, where_clause: str = "", params: List[Any] = None) -> int:
        """
        统计实体数量

        Args:
            where_clause: WHERE 子句（不含 WHERE 关键字）
            params: 参数列表

        Returns:
            数量
        """
        sql = f'SELECT COUNT(*) as count FROM {self.table_name}'
        if where_clause:
            sql += f' WHERE {where_clause}'

        with self._cursor() as cursor:
            cursor.execute(sql, params or [])
            return cursor.fetchone()['count']

    # ==================== 安全验证 ====================

    def _validate_order_by(self, order_by: str) -> Optional[str]:
        """
        验证并返回安全的 ORDER BY 子句

        Args:
            order_by: 排序参数，格式 "column_name [ASC|DESC]"

        Returns:
            安全的排序子句，无效时返回 None
        """
        order_parts = order_by.strip().split()
        if not order_parts:
            return None

        column = order_parts[0].lower()
        direction = order_parts[1].upper() if len(order_parts) > 1 else 'ASC'

        if column not in self.allowed_columns:
            logger.warning(f"Invalid order column: {column}")
            return None

        if direction not in ('ASC', 'DESC'):
            logger.warning(f"Invalid order direction: {direction}")
            return None

        return f'{column} {direction}'

    def _validate_columns(self, columns: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证并过滤有效的列

        Args:
            columns: 列名到值的映射

        Returns:
            过滤后的有效列
        """
        return {k: v for k, v in columns.items() if k in self.allowed_columns}

    def _is_numeric_field(self, field: str) -> bool:
        """判断字段是否为数值类型"""
        return field in self.numeric_fields


# ==================== 单例工厂 ====================

_store_instances: Dict[str, Any] = {}


def get_store_instance(store_class: type, key: str = None, **kwargs) -> Any:
    """
    获取存储层单例实例

    Args:
        store_class: 存储类
        key: 实例键名，默认使用类名
        **kwargs: 传递给构造函数的参数

    Returns:
        存储层实例
    """
    key = key or store_class.__name__
    if key not in _store_instances:
        _store_instances[key] = store_class(**kwargs)
    return _store_instances[key]


def reset_store_instance(key: str) -> None:
    """
    重置存储层单例（用于测试）

    Args:
        key: 实例键名
    """
    if key in _store_instances:
        instance = _store_instances[key]
        if hasattr(instance, 'close'):
            instance.close()
        del _store_instances[key]


def reset_all_stores() -> None:
    """重置所有存储层单例"""
    for key in list(_store_instances.keys()):
        reset_store_instance(key)
