/**
 * Log query hooks using TanStack Query
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { logApi } from './api'
import type { LogQueryParams, LogSQLQuery } from './types'

// Query keys
export const logKeys = {
  all: ['logs'] as const,
  topics: () => [...logKeys.all, 'topics'] as const,
  query: (params: LogQueryParams) => [...logKeys.all, 'query', params] as const,
  sql: (query: LogSQLQuery) => [...logKeys.all, 'sql', query] as const,
  fieldValues: (field: string, topic?: string) =>
    [...logKeys.all, 'fieldValues', field, topic] as const,
  stats: (params?: { topic?: string; start_time?: string; end_time?: string }) =>
    [...logKeys.all, 'stats', params] as const,
}

/**
 * Hook to fetch log topics
 */
export function useLogTopics() {
  return useQuery({
    queryKey: logKeys.topics(),
    queryFn: () => logApi.getTopics(),
    staleTime: 5 * 60 * 1000, // Topics are relatively stable
  })
}

/**
 * Hook to query logs with simple filters
 * @param autoRefresh - 是否启用自动刷新（默认 false，用户可手动刷新）
 */
export function useLogQuery(params: LogQueryParams, enabled = true, autoRefresh = false) {
  return useQuery({
    queryKey: logKeys.query(params),
    queryFn: () => logApi.query(params),
    enabled,
    staleTime: 30 * 1000, // 30 秒缓存
    refetchInterval: autoRefresh ? 30000 : false, // 30 秒自动刷新（仅启用时）
  })
}

/**
 * Hook for SQL query (expert mode)
 */
export function useLogSQLQuery() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (query: LogSQLQuery) => logApi.querySQL(query),
    onSuccess: () => {
      // Invalidate log queries on success
      queryClient.invalidateQueries({ queryKey: logKeys.all })
    },
  })
}

/**
 * Hook to fetch field values for filtering
 */
export function useLogFieldValues(field: string, topic?: string, enabled = true) {
  return useQuery({
    queryKey: logKeys.fieldValues(field, topic),
    queryFn: () => logApi.getFieldValues(field, topic),
    enabled: enabled && !!field,
    staleTime: 30 * 1000, // Cache for 30 seconds
  })
}

/**
 * Hook to fetch log statistics
 */
export function useLogStats(params?: {
  topic?: string
  start_time?: string
  end_time?: string
}) {
  return useQuery({
    queryKey: logKeys.stats(params),
    queryFn: () => logApi.getStats(params),
    staleTime: 30 * 1000,
  })
}
