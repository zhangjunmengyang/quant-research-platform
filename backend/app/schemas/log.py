"""Log-related Pydantic schemas."""

from datetime import datetime
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, Field


class LogTopic(BaseModel):
    """Log topic model."""

    id: int = Field(..., description="主题 ID")
    name: str = Field(..., description="主题标识符")
    display_name: str = Field(..., description="显示名称")
    description: str = Field("", description="描述")
    field_schema: Dict[str, Any] = Field(default_factory=dict, description="字段定义")
    retention_days: int = Field(30, description="保留天数")

    class Config:
        from_attributes = True


class LogEntry(BaseModel):
    """Log entry model for API responses."""

    id: int = Field(..., description="日志 ID")
    timestamp: str = Field(..., description="时间戳 (北京时间 YYYY-MM-DD HH:MM:SS.mmm)")
    topic: str = Field(..., description="日志主题")
    level: str = Field(..., description="日志级别")
    service: str = Field(..., description="服务名称")
    logger: str = Field("", description="日志器名称")
    trace_id: str = Field("", description="追踪 ID")
    message: str = Field(..., description="日志消息")
    data: Dict[str, Any] = Field(default_factory=dict, description="扩展数据")


class LogFilterCondition(BaseModel):
    """单个筛选条件。"""

    field: str = Field(..., description="字段名 (如 level, service, data.tool_name)")
    operator: str = Field(
        "=",
        description="操作符: =, !=, >, >=, <, <=, like, not_like, exist, not_exist"
    )
    value: Optional[str] = Field(None, description="筛选值 (exist/not_exist 操作符不需要)")


class LogQueryParams(BaseModel):
    """Log query parameters for simple mode."""

    topic: Optional[str] = Field(None, description="日志主题")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    level: Optional[str] = Field(None, description="日志级别 (debug, info, warning, error)")
    service: Optional[str] = Field(None, description="服务名称")
    trace_id: Optional[str] = Field(None, description="追踪 ID")
    search: Optional[str] = Field(None, description="全文搜索关键词")
    filters: Optional[Dict[str, Any]] = Field(None, description="JSONB 字段筛选 (旧版)")
    advanced_filters: Optional[List[LogFilterCondition]] = Field(
        None,
        description="高级筛选条件列表"
    )
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(50, ge=1, le=500, description="每页数量")


class LogSQLQuery(BaseModel):
    """Log SQL query for expert mode."""

    sql: str = Field(..., description="SQL 查询语句", min_length=1)
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(50, ge=1, le=500, description="每页数量")


class LogQueryResult(BaseModel):
    """Log query result."""

    logs: List[LogEntry] = Field(default_factory=list, description="日志列表")
    total: int = Field(0, description="总数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(50, description="每页数量")
    has_more: bool = Field(False, description="是否有更多")


class LogFieldValue(BaseModel):
    """Field value with count for filtering."""

    value: str = Field(..., description="字段值")
    count: int = Field(..., description="出现次数")


class LogFieldValues(BaseModel):
    """Field values response."""

    field: str = Field(..., description="字段名")
    values: List[LogFieldValue] = Field(default_factory=list, description="字段值列表")


class LogStats(BaseModel):
    """Log statistics."""

    total: int = Field(0, description="日志总数")
    by_level: Dict[str, int] = Field(default_factory=dict, description="按级别统计")
    by_service: Dict[str, int] = Field(default_factory=dict, description="按服务统计")
    by_topic: Dict[str, int] = Field(default_factory=dict, description="按主题统计")
    time_range: Optional[Dict[str, datetime]] = Field(None, description="时间范围")
