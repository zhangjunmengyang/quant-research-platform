/**
 * MCP management module type definitions
 * Mirrors backend Pydantic models for type safety
 */

// MCP 服务器状态枚举
export type MCPServerStatus = 'running' | 'stopped' | 'error' | 'starting' | 'stopping' | 'unresponsive'

// MCP 服务器信息
export interface MCPServerInfo {
  name: string
  display_name: string
  description: string
  host: string
  port: number
  status: MCPServerStatus
  uptime_seconds?: number
  version?: string
  tools_count: number
  last_health_check?: string
  error_message?: string
}

// MCP 服务器健康状态
export interface MCPServerHealth {
  status: string
  uptime_seconds: number
  server_name: string
  version: string
}

// MCP 服务器统计信息
export interface MCPServerStats {
  name: string
  health?: MCPServerHealth
  ready: boolean
  tools_count: number
  logging_stats?: Record<string, unknown>
  cache_stats?: Record<string, unknown>
  rate_limiter?: Record<string, unknown>
}

// MCP 工具信息
export interface MCPToolInfo {
  name: string
  description: string
  category?: string
  input_schema?: Record<string, unknown>
  server: string
}

// MCP 工具调用请求
export interface MCPToolCallRequest {
  server: string
  tool: string
  arguments: Record<string, unknown>
}

// MCP 工具调用结果
export interface MCPToolCallResult {
  success: boolean
  content?: unknown
  error?: string
  duration_ms?: number
}

// MCP 服务器操作
export type MCPServerAction = 'start' | 'stop' | 'restart'

// MCP 服务器操作请求
export interface MCPServerActionRequest {
  action: MCPServerAction
}

// MCP 服务器操作结果
export interface MCPServerActionResult {
  success: boolean
  message: string
  server: string
  new_status: MCPServerStatus
}

// MCP 仪表盘统计
export interface MCPDashboardStats {
  total_servers: number
  running_servers: number
  total_tools: number
  servers: MCPServerInfo[]
}
