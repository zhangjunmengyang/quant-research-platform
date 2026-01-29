"""
日志存储服务

提供日志写入和查询功能，支持:
- 异步批量写入 PostgreSQL
- SQL 和简单模式查询
- 字段动态发现

内存安全:
- 缓冲区大小限制，防止内存溢出
- 数据库操作超时保护
- 连接池健康检查
"""

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import asyncpg

from .config import get_logger

logger = get_logger(__name__)

# 配置常量
DB_COMMAND_TIMEOUT = 10  # 数据库命令超时（秒）
DB_CONNECT_TIMEOUT = 5  # 数据库连接超时（秒）
MAX_BUFFER_SIZE = 10000  # 最大缓冲区大小，防止内存溢出
FLUSH_TIMEOUT = 30  # flush 操作超时（秒）

# 北京时区 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))

# 安全字段名正则表达式（只允许字母、数字、下划线，且不能以数字开头）
SAFE_FIELD_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def validate_field_name(field_name: str) -> bool:
    """验证字段名是否安全（防止 SQL 注入）"""
    return bool(SAFE_FIELD_NAME_PATTERN.match(field_name))


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    topic: str  # 主题名称
    level: str
    service: str
    message: str
    logger_name: str = ""
    trace_id: str = ""
    data: dict = field(default_factory=dict)
    raw_line: str = ""


@dataclass
class LogTopic:
    """日志主题"""
    id: int
    name: str
    display_name: str
    description: str
    field_schema: dict
    retention_days: int


@dataclass
class LogQueryResult:
    """日志查询结果"""
    logs: list[dict]
    total: int
    fields: list[str]  # 发现的字段列表
    has_more: bool


class LogStore:
    """日志存储服务"""

    def __init__(
        self,
        database_url: str | None = None,
        batch_size: int = 100,
        flush_interval: float = 1.0,
    ):
        """
        初始化日志存储

        Args:
            database_url: PostgreSQL 连接 URL
            batch_size: 批量写入大小
            flush_interval: 刷新间隔（秒）
        """
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://quant:quant123@localhost:5432/quant"
        )
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self._pool: asyncpg.Pool | None = None
        self._buffer: list[LogEntry] = []
        self._buffer_lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None
        self._topic_cache: dict[str, int] = {}  # name -> id
        self._running = False

    async def start(self):
        """启动日志存储服务"""
        if self._running:
            return

        try:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=DB_COMMAND_TIMEOUT,
                timeout=DB_CONNECT_TIMEOUT,
            )
            self._running = True
            # 预加载主题缓存
            await asyncio.wait_for(self._load_topics(), timeout=DB_COMMAND_TIMEOUT)
            # 启动后台刷新任务
            self._flush_task = asyncio.create_task(self._flush_loop())
            logger.info("log_store_started", database_url=self.database_url[:50] + "...")
        except TimeoutError:
            logger.error("log_store_start_timeout")
            raise
        except Exception as e:
            logger.error("log_store_start_failed", error=str(e))
            raise

    async def stop(self):
        """停止日志存储服务"""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        # 刷新剩余日志
        await self._flush()
        if self._pool:
            await self._pool.close()
        logger.info("log_store_stopped")

    async def _load_topics(self):
        """加载日志主题到缓存"""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, name FROM log_topics")
            self._topic_cache = {row["name"]: row["id"] for row in rows}

    async def _get_topic_id(self, topic_name: str) -> int | None:
        """获取主题 ID，如果不存在则创建"""
        if topic_name in self._topic_cache:
            return self._topic_cache[topic_name]

        # 尝试创建新主题
        async with self._pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO log_topics (name, display_name, description)
                    VALUES ($1, $1, '')
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    topic_name
                )
                topic_id = row["id"]
                self._topic_cache[topic_name] = topic_id
                return topic_id
            except Exception as e:
                logger.warning("create_topic_failed", topic=topic_name, error=str(e))
                return None

    async def write(self, entry: LogEntry):
        """
        写入单条日志（异步缓冲）

        Args:
            entry: 日志条目
        """
        should_flush = False
        async with self._buffer_lock:
            # 防止缓冲区无限增长
            if len(self._buffer) >= MAX_BUFFER_SIZE:
                # 丢弃最旧的日志
                self._buffer = self._buffer[-(MAX_BUFFER_SIZE // 2):]
                logger.warning("log_buffer_overflow", dropped=MAX_BUFFER_SIZE // 2)

            self._buffer.append(entry)
            should_flush = len(self._buffer) >= self.batch_size

        # 在锁外触发 flush，避免死锁
        if should_flush:
            await self._flush()

    async def write_batch(self, entries: list[LogEntry]):
        """
        批量写入日志

        Args:
            entries: 日志条目列表
        """
        should_flush = False
        async with self._buffer_lock:
            # 防止缓冲区无限增长
            remaining_capacity = MAX_BUFFER_SIZE - len(self._buffer)
            if len(entries) > remaining_capacity:
                entries = entries[-remaining_capacity:]
                logger.warning("log_batch_truncated", kept=len(entries))

            self._buffer.extend(entries)
            should_flush = len(self._buffer) >= self.batch_size

        # 在锁外触发 flush，避免死锁
        if should_flush:
            await self._flush()

    async def _flush_loop(self):
        """后台刷新循环"""
        while self._running:
            await asyncio.sleep(self.flush_interval)
            if self._buffer:
                try:
                    # 添加超时保护，防止 flush 操作阻塞事件循环
                    await asyncio.wait_for(self._flush(), timeout=FLUSH_TIMEOUT)
                except TimeoutError:
                    logger.error("log_flush_timeout", buffer_size=len(self._buffer))
                except Exception as e:
                    logger.error("log_flush_loop_error", error=str(e))

    async def _flush(self):
        """刷新缓冲区到数据库"""
        async with self._buffer_lock:
            if not self._buffer:
                return

            entries = self._buffer
            self._buffer = []

        if not self._pool:
            return

        try:
            # 添加连接获取超时
            conn = await asyncio.wait_for(
                self._pool.acquire(),
                timeout=DB_CONNECT_TIMEOUT
            )

            try:
                # 批量插入
                records = []
                for entry in entries:
                    topic_id = await self._get_topic_id(entry.topic)
                    if topic_id is None:
                        continue
                    records.append((
                        entry.timestamp,
                        topic_id,
                        entry.level,
                        entry.service,
                        entry.logger_name,
                        entry.trace_id,
                        entry.message,
                        json.dumps(entry.data, ensure_ascii=False),
                        entry.raw_line,
                    ))

                if records:
                    await conn.executemany(
                        """
                        INSERT INTO logs (timestamp, topic_id, level, service, logger, trace_id, message, data, raw_line)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                        records
                    )
                    logger.debug("logs_flushed", count=len(records))
            finally:
                await self._pool.release(conn)

        except TimeoutError:
            logger.error("log_flush_acquire_timeout", count=len(entries))
        except Exception as e:
            logger.error("log_flush_failed", error=str(e), count=len(entries))

    # ========================================
    # 查询方法
    # ========================================

    async def get_topics(self) -> list[LogTopic]:
        """获取所有日志主题"""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, display_name, description, field_schema, retention_days
                FROM log_topics
                ORDER BY name
                """
            )
            return [
                LogTopic(
                    id=row["id"],
                    name=row["name"],
                    display_name=row["display_name"],
                    description=row["description"],
                    field_schema=json.loads(row["field_schema"]) if row["field_schema"] else {},
                    retention_days=row["retention_days"],
                )
                for row in rows
            ]

    async def query(
        self,
        topic: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        level: str | None = None,
        service: str | None = None,
        trace_id: str | None = None,
        filters: dict[str, Any] | None = None,
        advanced_filters: list[dict[str, Any]] | None = None,
        search: str | None = None,
        sql: str | None = None,
        limit: int = 100,
        offset: int = 0,
        order_desc: bool = True,
    ) -> LogQueryResult:
        """
        查询日志

        Args:
            topic: 日志主题
            start_time: 开始时间
            end_time: 结束时间
            level: 日志级别
            service: 服务名称
            trace_id: 追踪 ID
            filters: JSONB 字段过滤 {"field": "value"} (旧版)
            advanced_filters: 高级筛选条件列表
            search: 全文搜索
            sql: 原始 SQL（专家模式）
            limit: 返回数量限制
            offset: 偏移量
            order_desc: 是否降序（默认最新在前）

        Returns:
            LogQueryResult
        """
        # 专家模式：直接执行 SQL
        if sql:
            return await self._query_sql(sql, limit, offset)

        # 简单模式：构建查询
        return await self._query_simple(
            topic=topic,
            start_time=start_time,
            end_time=end_time,
            level=level,
            service=service,
            trace_id=trace_id,
            filters=filters,
            advanced_filters=advanced_filters,
            search=search,
            limit=limit,
            offset=offset,
            order_desc=order_desc,
        )

    async def _query_simple(
        self,
        topic: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        level: str | None,
        service: str | None,
        trace_id: str | None,
        filters: dict[str, Any] | None,
        advanced_filters: list[dict[str, Any]] | None,
        search: str | None,
        limit: int,
        offset: int,
        order_desc: bool,
    ) -> LogQueryResult:
        """简单模式查询"""
        conditions = []
        params = []
        param_idx = 1

        # 主题过滤
        if topic:
            topic_id = self._topic_cache.get(topic)
            if topic_id:
                conditions.append(f"l.topic_id = ${param_idx}")
                params.append(topic_id)
                param_idx += 1

        # 时间范围
        if start_time:
            conditions.append(f"l.timestamp >= ${param_idx}")
            params.append(start_time)
            param_idx += 1
        if end_time:
            conditions.append(f"l.timestamp <= ${param_idx}")
            params.append(end_time)
            param_idx += 1

        # 级别过滤
        if level:
            if "," in level:
                levels = [l.strip() for l in level.split(",")]
                conditions.append(f"l.level = ANY(${param_idx})")
                params.append(levels)
            else:
                conditions.append(f"l.level = ${param_idx}")
                params.append(level)
            param_idx += 1

        # 服务过滤
        if service:
            conditions.append(f"l.service = ${param_idx}")
            params.append(service)
            param_idx += 1

        # Trace ID 过滤
        if trace_id:
            conditions.append(f"l.trace_id = ${param_idx}")
            params.append(trace_id)
            param_idx += 1

        # JSONB 字段过滤 (旧版兼容)
        if filters:
            for key, value in filters.items():
                if value is not None and value != "":
                    # 验证字段名安全性
                    if not validate_field_name(key):
                        logger.warning("invalid_filter_field", field=key)
                        continue
                    conditions.append(f"l.data->>'{key}' = ${param_idx}")
                    params.append(str(value))
                    param_idx += 1

        # 高级筛选条件
        if advanced_filters:
            # 基础字段映射
            base_fields = {
                "timestamp": "l.timestamp",
                "topic": "t.name",
                "level": "l.level",
                "service": "l.service",
                "logger": "l.logger",
                "trace_id": "l.trace_id",
                "message": "l.message",
            }

            for f in advanced_filters:
                field = f.get("field", "")
                operator = f.get("operator", "=")
                value = f.get("value")

                if not field:
                    continue

                # 确定是基础字段还是 JSONB 字段
                if field in base_fields:
                    column = base_fields[field]
                elif field.startswith("data."):
                    json_key = field[5:]  # 去掉 "data." 前缀
                    # 验证字段名安全性
                    if not validate_field_name(json_key):
                        logger.warning("invalid_filter_field", field=field)
                        continue
                    column = f"l.data->>'{json_key}'"
                else:
                    # 验证字段名安全性
                    if not validate_field_name(field):
                        logger.warning("invalid_filter_field", field=field)
                        continue
                    # 假设是 data 字段
                    column = f"l.data->>'{field}'"

                # 根据操作符构建条件
                if operator == "=":
                    conditions.append(f"{column} = ${param_idx}")
                    params.append(str(value) if value is not None else "")
                    param_idx += 1
                elif operator == "!=":
                    conditions.append(f"({column} IS NULL OR {column} != ${param_idx})")
                    params.append(str(value) if value is not None else "")
                    param_idx += 1
                elif operator == ">":
                    conditions.append(f"{column} > ${param_idx}")
                    params.append(str(value) if value is not None else "")
                    param_idx += 1
                elif operator == ">=":
                    conditions.append(f"{column} >= ${param_idx}")
                    params.append(str(value) if value is not None else "")
                    param_idx += 1
                elif operator == "<":
                    conditions.append(f"{column} < ${param_idx}")
                    params.append(str(value) if value is not None else "")
                    param_idx += 1
                elif operator == "<=":
                    conditions.append(f"{column} <= ${param_idx}")
                    params.append(str(value) if value is not None else "")
                    param_idx += 1
                elif operator == "like":
                    conditions.append(f"{column} ILIKE ${param_idx}")
                    # 添加通配符
                    search_value = f"%{value}%" if value else "%%"
                    params.append(search_value)
                    param_idx += 1
                elif operator == "not_like":
                    conditions.append(f"({column} IS NULL OR {column} NOT ILIKE ${param_idx})")
                    search_value = f"%{value}%" if value else "%%"
                    params.append(search_value)
                    param_idx += 1
                elif operator == "exist":
                    # 字段存在且非空
                    if field in base_fields:
                        conditions.append(f"{column} IS NOT NULL AND {column} != ''")
                    else:
                        json_key = field[5:] if field.startswith("data.") else field
                        # 验证字段名安全性
                        if not validate_field_name(json_key):
                            logger.warning("invalid_filter_field", field=field)
                            continue
                        conditions.append(f"l.data ? '{json_key}'")
                elif operator == "not_exist":
                    # 字段不存在或为空
                    if field in base_fields:
                        conditions.append(f"({column} IS NULL OR {column} = '')")
                    else:
                        json_key = field[5:] if field.startswith("data.") else field
                        # 验证字段名安全性
                        if not validate_field_name(json_key):
                            logger.warning("invalid_filter_field", field=field)
                            continue
                        conditions.append(f"NOT (l.data ? '{json_key}')")

        # 全文搜索
        if search:
            conditions.append(f"to_tsvector('simple', l.message) @@ plainto_tsquery('simple', ${param_idx})")
            params.append(search)
            param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        order_dir = "DESC" if order_desc else "ASC"

        # 查询总数
        count_sql = f"""
            SELECT COUNT(*) FROM logs l
            WHERE {where_clause}
        """

        # 查询数据
        data_sql = f"""
            SELECT
                l.id,
                l.timestamp,
                t.name as topic,
                l.level,
                l.service,
                l.logger,
                l.trace_id,
                l.message,
                l.data
            FROM logs l
            JOIN log_topics t ON l.topic_id = t.id
            WHERE {where_clause}
            ORDER BY l.timestamp {order_dir}
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit + 1, offset])  # +1 用于判断是否有更多

        async with self._pool.acquire() as conn:
            total = await conn.fetchval(count_sql, *params[:-2])
            rows = await conn.fetch(data_sql, *params)

        # 处理结果
        logs = []
        discovered_fields = set()

        for row in rows[:limit]:
            data = json.loads(row["data"]) if row["data"] else {}
            discovered_fields.update(data.keys())

            # 转换时间戳到北京时间 (UTC+8)
            ts = row["timestamp"]
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            ts_beijing = ts.astimezone(BEIJING_TZ)

            logs.append({
                "id": row["id"],
                "timestamp": ts_beijing.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "topic": row["topic"],
                "level": row["level"],
                "service": row["service"],
                "logger": row["logger"],
                "trace_id": row["trace_id"],
                "message": row["message"],
                **data,  # 展开 JSONB 字段
            })

        return LogQueryResult(
            logs=logs,
            total=total,
            fields=sorted(discovered_fields),
            has_more=len(rows) > limit,
        )

    async def _query_sql(self, sql: str, limit: int, offset: int) -> LogQueryResult:
        """
        专家模式：执行原始 SQL

        注意：为安全起见，只允许 SELECT 语句
        """
        sql = sql.strip()
        if not sql.upper().startswith("SELECT"):
            raise ValueError("Only SELECT statements are allowed")

        # 禁止危险操作
        forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "CREATE", "GRANT"]
        sql_upper = sql.upper()
        for word in forbidden:
            if word in sql_upper:
                raise ValueError(f"Forbidden keyword: {word}")

        # 添加 LIMIT 如果没有
        if "LIMIT" not in sql_upper:
            sql = f"{sql} LIMIT {limit} OFFSET {offset}"

        async with self._pool.acquire() as conn:
            try:
                rows = await conn.fetch(sql)
            except Exception as e:
                raise ValueError(f"SQL execution error: {e}")

        # 转换结果
        logs = []
        fields = set()

        for row in rows:
            record = dict(row)
            fields.update(record.keys())
            # 处理特殊类型
            for key, value in record.items():
                if isinstance(value, datetime):
                    # 转换时间戳到北京时间 (UTC+8)
                    if value.tzinfo is None:
                        value = value.replace(tzinfo=UTC)
                    value_beijing = value.astimezone(BEIJING_TZ)
                    record[key] = value_beijing.strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(value, (dict, list)):
                    pass  # 保持原样
                elif value is None:
                    record[key] = None
                else:
                    record[key] = str(value) if not isinstance(value, (int, float, bool)) else value
            logs.append(record)

        return LogQueryResult(
            logs=logs,
            total=len(logs),
            fields=sorted(fields),
            has_more=False,
        )

    async def get_field_values(
        self,
        topic: str | None,
        field_name: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        获取字段的可选值及其出现次数（用于筛选器下拉框）

        Args:
            topic: 日志主题
            field_name: 字段名
            limit: 返回数量限制

        Returns:
            字段值和计数列表 [{"value": "xxx", "count": 10}, ...]
        """
        # 基础字段
        base_fields = ["level", "service", "logger", "trace_id"]

        params = []
        param_idx = 1

        if field_name in base_fields:
            topic_filter = ""
            if topic and topic in self._topic_cache:
                topic_filter = f"AND l.topic_id = ${param_idx}"
                params.append(self._topic_cache[topic])
                param_idx += 1

            sql = f"""
                SELECT {field_name} as value, COUNT(*) as count
                FROM logs l
                WHERE {field_name} IS NOT NULL AND {field_name} != ''
                {topic_filter}
                GROUP BY {field_name}
                ORDER BY count DESC
                LIMIT ${param_idx}
            """
            params.append(limit)
        else:
            # JSONB 字段 - 验证字段名安全性
            if not validate_field_name(field_name):
                logger.warning("invalid_field_name", field=field_name)
                return []

            topic_filter = ""
            if topic and topic in self._topic_cache:
                topic_filter = f"AND l.topic_id = ${param_idx}"
                params.append(self._topic_cache[topic])
                param_idx += 1

            sql = f"""
                SELECT l.data->>'{field_name}' as value, COUNT(*) as count
                FROM logs l
                WHERE l.data->>'{field_name}' IS NOT NULL
                {topic_filter}
                GROUP BY l.data->>'{field_name}'
                ORDER BY count DESC
                LIMIT ${param_idx}
            """
            params.append(limit)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [{"value": row["value"], "count": row["count"]} for row in rows if row["value"]]

    async def get_stats(
        self,
        topic: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict:
        """
        获取日志统计信息

        Returns:
            统计数据，包含：
            - total: 总日志数
            - by_level: 按级别分组统计
            - by_service: 按服务分组统计
            - by_topic: 按主题分组统计
            - time_range: 时间范围
        """
        conditions = []
        params = []
        param_idx = 1

        if topic and topic in self._topic_cache:
            conditions.append(f"l.topic_id = ${param_idx}")
            params.append(self._topic_cache[topic])
            param_idx += 1

        if start_time:
            conditions.append(f"l.timestamp >= ${param_idx}")
            params.append(start_time)
            param_idx += 1

        if end_time:
            conditions.append(f"l.timestamp <= ${param_idx}")
            params.append(end_time)
            param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 总数和时间范围
        total_sql = f"""
            SELECT
                COUNT(*) as total,
                MIN(l.timestamp) as earliest,
                MAX(l.timestamp) as latest
            FROM logs l
            WHERE {where_clause}
        """

        # 按级别分组
        by_level_sql = f"""
            SELECT l.level, COUNT(*) as count
            FROM logs l
            WHERE {where_clause} AND l.level IS NOT NULL
            GROUP BY l.level
            ORDER BY count DESC
        """

        # 按服务分组
        by_service_sql = f"""
            SELECT l.service, COUNT(*) as count
            FROM logs l
            WHERE {where_clause} AND l.service IS NOT NULL AND l.service != ''
            GROUP BY l.service
            ORDER BY count DESC
            LIMIT 20
        """

        # 按主题分组
        by_topic_sql = f"""
            SELECT t.name as topic, COUNT(*) as count
            FROM logs l
            JOIN log_topics t ON l.topic_id = t.id
            WHERE {where_clause}
            GROUP BY t.name
            ORDER BY count DESC
        """

        async with self._pool.acquire() as conn:
            total_row = await conn.fetchrow(total_sql, *params)
            level_rows = await conn.fetch(by_level_sql, *params)
            service_rows = await conn.fetch(by_service_sql, *params)
            topic_rows = await conn.fetch(by_topic_sql, *params)

        # 转换时间戳到北京时间
        def format_ts(ts):
            if ts is None:
                return None
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            return ts.astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")

        return {
            "total": total_row["total"],
            "by_level": {row["level"]: row["count"] for row in level_rows},
            "by_service": {row["service"]: row["count"] for row in service_rows},
            "by_topic": {row["topic"]: row["count"] for row in topic_rows},
            "time_range": {
                "min": format_ts(total_row["earliest"]),
                "max": format_ts(total_row["latest"]),
            } if total_row["earliest"] else None,
        }
