/**
 * Log API client
 */

import { apiClient } from '@/lib/api/client'
import type {
  LogTopic,
  LogQueryParams,
  LogSQLQuery,
  LogQueryResult,
  LogFieldValues,
  LogStats,
} from './types'

const BASE_URL = '/logs'

export const logApi = {
  /**
   * Get all log topics
   */
  getTopics: async (): Promise<LogTopic[]> => {
    const { data } = await apiClient.get<LogTopic[]>(`${BASE_URL}/topics`)
    return data
  },

  /**
   * Query logs with simple filters
   */
  query: async (params: LogQueryParams = {}): Promise<LogQueryResult> => {
    // 将 advanced_filters 序列化为 JSON 字符串传递给后端
    const queryParams: Record<string, unknown> = { ...params }
    if (params.advanced_filters && params.advanced_filters.length > 0) {
      // 移除前端的 id 字段，只传递 field, operator, value
      const filters = params.advanced_filters.map(({ field, operator, value }) => ({
        field,
        operator,
        value,
      }))
      queryParams.advanced_filters = JSON.stringify(filters)
    } else {
      delete queryParams.advanced_filters
    }

    const { data } = await apiClient.get<LogQueryResult>(`${BASE_URL}/query`, {
      params: queryParams,
    })
    return data
  },

  /**
   * Query logs with SQL (expert mode)
   */
  querySQL: async (query: LogSQLQuery): Promise<LogQueryResult> => {
    const { data } = await apiClient.post<LogQueryResult>(`${BASE_URL}/query/sql`, query)
    return data
  },

  /**
   * Get field values for filtering
   */
  getFieldValues: async (
    fieldName: string,
    topic?: string,
    limit: number = 100
  ): Promise<LogFieldValues> => {
    const { data } = await apiClient.get<LogFieldValues>(
      `${BASE_URL}/fields/${fieldName}/values`,
      {
        params: { topic, limit },
      }
    )
    return data
  },

  /**
   * Get log statistics
   */
  getStats: async (params?: {
    topic?: string
    start_time?: string
    end_time?: string
  }): Promise<LogStats> => {
    const { data } = await apiClient.get<LogStats>(`${BASE_URL}/stats`, {
      params,
    })
    return data
  },
}
