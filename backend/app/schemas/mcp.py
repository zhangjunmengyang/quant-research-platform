"""MCP management schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MCPServerStatus(str, Enum):
    """MCP 服务器状态"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"
    UNRESPONSIVE = "unresponsive"  # 进程存在但不响应健康检查


class MCPServerInfo(BaseModel):
    """MCP 服务器信息"""
    name: str = Field(..., description="服务器名称")
    display_name: str = Field(..., description="显示名称")
    description: str = Field("", description="服务器描述")
    host: str = Field("localhost", description="监听地址")
    port: int = Field(..., description="监听端口")
    status: MCPServerStatus = Field(MCPServerStatus.STOPPED, description="运行状态")
    uptime_seconds: Optional[float] = Field(None, description="运行时长(秒)")
    version: Optional[str] = Field(None, description="版本号")
    tools_count: int = Field(0, description="工具数量")
    resources_count: int = Field(0, description="资源数量")
    last_health_check: Optional[datetime] = Field(None, description="最后健康检查时间")
    error_message: Optional[str] = Field(None, description="错误信息")


class MCPServerHealth(BaseModel):
    """MCP 服务器健康状态"""
    status: str = Field(..., description="健康状态")
    uptime_seconds: float = Field(0, description="运行时长")
    server_name: str = Field(..., description="服务器名称")
    version: str = Field("", description="版本号")


class MCPServerStats(BaseModel):
    """MCP 服务器统计信息"""
    name: str
    health: Optional[MCPServerHealth] = None
    ready: bool = False
    tools_count: int = 0
    logging_stats: Optional[Dict[str, Any]] = None
    cache_stats: Optional[Dict[str, Any]] = None
    rate_limiter: Optional[Dict[str, Any]] = None


class MCPToolInfo(BaseModel):
    """MCP 工具信息"""
    name: str = Field(..., description="工具名称")
    description: str = Field("", description="工具描述")
    category: Optional[str] = Field(None, description="工具分类")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="输入参数 Schema")
    server: str = Field(..., description="所属服务器")


class MCPResourceInfo(BaseModel):
    """MCP 资源信息"""
    uri: str = Field(..., description="资源 URI")
    name: str = Field(..., description="资源名称")
    description: str = Field("", description="资源描述")
    mime_type: Optional[str] = Field(None, description="MIME 类型")
    server: str = Field(..., description="所属服务器")


class MCPToolCallRequest(BaseModel):
    """MCP 工具调用请求"""
    server: str = Field(..., description="服务器名称")
    tool: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="调用参数")


class MCPToolCallResult(BaseModel):
    """MCP 工具调用结果"""
    success: bool = Field(..., description="是否成功")
    content: Optional[Any] = Field(None, description="返回内容")
    error: Optional[str] = Field(None, description="错误信息")
    duration_ms: Optional[float] = Field(None, description="执行耗时(毫秒)")


class MCPServerAction(str, Enum):
    """MCP 服务器操作"""
    START = "start"
    STOP = "stop"
    RESTART = "restart"


class MCPServerActionRequest(BaseModel):
    """MCP 服务器操作请求"""
    action: MCPServerAction = Field(..., description="操作类型")


class MCPServerActionResult(BaseModel):
    """MCP 服务器操作结果"""
    success: bool = Field(..., description="是否成功")
    message: str = Field("", description="结果消息")
    server: str = Field(..., description="服务器名称")
    new_status: MCPServerStatus = Field(..., description="新状态")


class MCPDashboardStats(BaseModel):
    """MCP 仪表盘统计"""
    total_servers: int = Field(0, description="服务器总数")
    running_servers: int = Field(0, description="运行中的服务器数")
    total_tools: int = Field(0, description="工具总数")
    total_resources: int = Field(0, description="资源总数")
    servers: List[MCPServerInfo] = Field(default_factory=list, description="服务器列表")
