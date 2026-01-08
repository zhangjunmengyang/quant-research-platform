"""Log query API routes."""

from typing import Optional, List
from datetime import datetime
import json

from fastapi import APIRouter, HTTPException, Query, Body

from app.schemas.log import (
    LogTopic,
    LogEntry,
    LogQueryParams,
    LogFilterCondition,
    LogSQLQuery,
    LogQueryResult,
    LogFieldValues,
    LogStats,
)
from domains.mcp_core.logging import get_log_store, get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/topics", response_model=List[LogTopic])
async def list_topics():
    """
    获取所有日志主题列表。

    Returns:
        日志主题列表
    """
    store = get_log_store()
    if not store:
        raise HTTPException(status_code=503, detail="Log store not initialized")

    topics = await store.get_topics()
    return [
        LogTopic(
            id=t.id,
            name=t.name,
            display_name=t.display_name,
            description=t.description,
            field_schema=t.field_schema,
            retention_days=t.retention_days,
        )
        for t in topics
    ]


@router.get("/query", response_model=LogQueryResult)
async def query_logs(
    topic: Optional[str] = Query(None, description="日志主题"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    level: Optional[str] = Query(None, description="日志级别"),
    service: Optional[str] = Query(None, description="服务名称"),
    trace_id: Optional[str] = Query(None, description="追踪 ID"),
    search: Optional[str] = Query(None, description="全文搜索"),
    advanced_filters: Optional[str] = Query(None, description="高级筛选条件 (JSON 数组)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=500, description="每页数量"),
):
    """
    简单模式查询日志。

    支持按主题、时间范围、级别、服务等条件筛选。
    支持高级筛选条件 (JSON 数组格式)。

    Returns:
        日志查询结果
    """
    store = get_log_store()
    if not store:
        raise HTTPException(status_code=503, detail="Log store not initialized")

    # 解析高级筛选条件
    parsed_filters = None
    if advanced_filters:
        try:
            parsed_filters = json.loads(advanced_filters)
            # 验证格式
            for f in parsed_filters:
                if not isinstance(f, dict) or "field" not in f:
                    raise ValueError("Invalid filter format")
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid advanced_filters JSON: {e}")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    try:
        result = await store.query(
            topic=topic,
            start_time=start_time,
            end_time=end_time,
            level=level,
            service=service,
            trace_id=trace_id,
            search=search,
            advanced_filters=parsed_filters,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

        # result.logs 是字典列表
        logs = [
            LogEntry(
                id=log.get("id", 0),
                timestamp=log.get("timestamp", ""),
                topic=log.get("topic", ""),
                level=log.get("level", ""),
                service=log.get("service", ""),
                logger=log.get("logger", ""),
                trace_id=log.get("trace_id", ""),
                message=log.get("message", ""),
                data={k: v for k, v in log.items() if k not in ["id", "timestamp", "topic", "level", "service", "logger", "trace_id", "message"]},
            )
            for log in result.logs
        ]

        return LogQueryResult(
            logs=logs,
            total=result.total,
            page=page,
            page_size=page_size,
            has_more=result.has_more,
        )
    except Exception as e:
        logger.error("log_query_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/query/sql", response_model=LogQueryResult)
async def query_logs_sql(query: LogSQLQuery):
    """
    专家模式：使用 SQL 查询日志。

    允许执行自定义 SQL 查询日志表。
    注意：仅支持 SELECT 查询，不允许修改数据。

    Args:
        query: SQL 查询请求

    Returns:
        日志查询结果
    """
    store = get_log_store()
    if not store:
        raise HTTPException(status_code=503, detail="Log store not initialized")

    # 安全检查：只允许 SELECT 查询
    sql_lower = query.sql.strip().lower()
    if not sql_lower.startswith("select"):
        raise HTTPException(
            status_code=400,
            detail="Only SELECT queries are allowed",
        )

    # 禁止危险操作
    dangerous_keywords = ["insert", "update", "delete", "drop", "truncate", "alter", "create"]
    for keyword in dangerous_keywords:
        if keyword in sql_lower:
            raise HTTPException(
                status_code=400,
                detail=f"Dangerous keyword '{keyword}' is not allowed",
            )

    try:
        result = await store.query(
            sql=query.sql,
            limit=query.page_size,
            offset=(query.page - 1) * query.page_size,
        )

        # result.logs 是字典列表
        logs = [
            LogEntry(
                id=log.get("id", 0),
                timestamp=log.get("timestamp", ""),
                topic=log.get("topic", ""),
                level=log.get("level", ""),
                service=log.get("service", ""),
                logger=log.get("logger", ""),
                trace_id=log.get("trace_id", ""),
                message=log.get("message", ""),
                data={k: v for k, v in log.items() if k not in ["id", "timestamp", "topic", "level", "service", "logger", "trace_id", "message"]},
            )
            for log in result.logs
        ]

        return LogQueryResult(
            logs=logs,
            total=result.total,
            page=query.page,
            page_size=query.page_size,
            has_more=result.has_more,
        )
    except Exception as e:
        logger.error("log_sql_query_error", error=str(e), sql=query.sql)
        raise HTTPException(status_code=500, detail=f"SQL query failed: {str(e)}")


@router.get("/fields/{field_name}/values", response_model=LogFieldValues)
async def get_field_values(
    field_name: str,
    topic: Optional[str] = Query(None, description="日志主题"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
):
    """
    获取指定字段的所有可用值。

    用于前端筛选器的选项填充。

    Args:
        field_name: 字段名（如 level, service, 或 data 中的字段如 data.tool_name）
        topic: 可选的日志主题筛选
        limit: 返回数量限制

    Returns:
        字段值列表及其出现次数
    """
    store = get_log_store()
    if not store:
        raise HTTPException(status_code=503, detail="Log store not initialized")

    try:
        values = await store.get_field_values(topic=topic, field_name=field_name, limit=limit)
        # values 现在是 [{"value": "xxx", "count": 10}, ...] 格式
        return LogFieldValues(
            field=field_name,
            values=values,
        )
    except Exception as e:
        logger.error("log_field_values_error", error=str(e), field=field_name)
        raise HTTPException(status_code=500, detail=f"Failed to get field values: {str(e)}")


@router.get("/stats", response_model=LogStats)
async def get_stats(
    topic: Optional[str] = Query(None, description="日志主题"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
):
    """
    获取日志统计信息。

    Returns:
        日志统计数据
    """
    store = get_log_store()
    if not store:
        raise HTTPException(status_code=503, detail="Log store not initialized")

    try:
        stats = await store.get_stats(topic=topic, start_time=start_time, end_time=end_time)
        return LogStats(**stats)
    except Exception as e:
        logger.error("log_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
