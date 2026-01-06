/**
 * Log module type definitions
 * Mirrors backend Pydantic models for type safety
 */

export interface LogTopic {
  id: number
  name: string
  display_name: string
  description: string
  field_schema: Record<string, unknown>
  retention_days: number
}

export interface LogEntry {
  id: number
  timestamp: string
  topic: string
  level: string
  service: string
  logger: string
  trace_id: string
  message: string
  data: Record<string, unknown>
}

/**
 * 筛选操作符类型
 */
export type FilterOperator =
  | '='
  | '!='
  | '>'
  | '>='
  | '<'
  | '<='
  | 'like'
  | 'not_like'
  | 'exist'
  | 'not_exist'

/**
 * 单个筛选条件
 */
export interface LogFilterCondition {
  id: string // 前端用于唯一标识
  field: string
  operator: FilterOperator
  value?: string
}

export interface LogQueryParams {
  topic?: string
  start_time?: string
  end_time?: string
  level?: string
  service?: string
  trace_id?: string
  search?: string
  advanced_filters?: LogFilterCondition[]
  page?: number
  page_size?: number
}

export interface LogSQLQuery {
  sql: string
  page?: number
  page_size?: number
}

export interface LogQueryResult {
  logs: LogEntry[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface LogFieldValue {
  value: string
  count: number
}

export interface LogFieldValues {
  field: string
  values: LogFieldValue[]
}

export interface LogStats {
  total: number
  by_level: Record<string, number>
  by_service: Record<string, number>
  by_topic: Record<string, number>
  time_range?: {
    min: string
    max: string
  }
}

// Log level colors
export const LOG_LEVEL_COLORS: Record<string, string> = {
  debug: 'text-gray-500',
  info: 'text-blue-500',
  warning: 'text-yellow-500',
  error: 'text-red-500',
}

// Log level badges
export const LOG_LEVEL_BADGES: Record<string, string> = {
  debug: 'bg-gray-100 text-gray-700',
  info: 'bg-blue-100 text-blue-700',
  warning: 'bg-yellow-100 text-yellow-700',
  error: 'bg-red-100 text-red-700',
}

// Display format types
export type LogDisplayFormat = 'table' | 'raw' | 'json'

// Query mode types
export type LogQueryMode = 'simple' | 'sql'
