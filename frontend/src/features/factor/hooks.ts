/**
 * Factor React Query Hooks
 */

import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { factorApi } from './api'
import type {
  FactorUpdate,
  FactorListParams,
  FactorVerifyRequest,
  FactorGroupAnalysisRequest,
} from './types'
import type { FillProgress, FillLog, FillProgressData } from './pipeline-api'

// Query Keys
export const factorKeys = {
  all: ['factors'] as const,
  lists: () => [...factorKeys.all, 'list'] as const,
  list: (params: FactorListParams) => [...factorKeys.lists(), params] as const,
  details: () => [...factorKeys.all, 'detail'] as const,
  detail: (filename: string) => [...factorKeys.details(), filename] as const,
  stats: () => [...factorKeys.all, 'stats'] as const,
  styles: () => [...factorKeys.all, 'styles'] as const,
}

// 默认缓存时间: 5 分钟
const DEFAULT_STALE_TIME = 5 * 60 * 1000

/**
 * Hook to fetch paginated factor list
 */
export function useFactors(params: FactorListParams = {}) {
  return useQuery({
    queryKey: factorKeys.list(params),
    queryFn: () => factorApi.list(params),
    placeholderData: keepPreviousData,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch a single factor by filename
 */
export function useFactor(filename: string) {
  return useQuery({
    queryKey: factorKeys.detail(filename),
    queryFn: () => factorApi.get(filename),
    enabled: !!filename,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch factor statistics
 */
export function useFactorStats() {
  return useQuery({
    queryKey: factorKeys.stats(),
    queryFn: factorApi.getStats,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch available styles
 */
export function useFactorStyles() {
  return useQuery({
    queryKey: factorKeys.styles(),
    queryFn: factorApi.getStyles,
    staleTime: 10 * 60 * 1000, // 样式列表很少变化，缓存 10 分钟
  })
}

/**
 * Hook for factor mutations (update, delete, verify, etc.)
 */
export function useFactorMutations() {
  const queryClient = useQueryClient()

  // 只失效列表和统计，不失效详情（详情通过 setQueryData 更新）
  const invalidateListAndStats = () => {
    queryClient.invalidateQueries({ queryKey: factorKeys.lists() })
    queryClient.invalidateQueries({ queryKey: factorKeys.stats() })
  }

  // 删除操作需要失效所有（包括详情）
  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: factorKeys.all })
  }

  const updateMutation = useMutation({
    mutationFn: ({ filename, update }: { filename: string; update: FactorUpdate }) =>
      factorApi.update(filename, update),
    onSuccess: (data) => {
      queryClient.setQueryData(factorKeys.detail(data.filename), data)
      invalidateListAndStats()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (filename: string) => factorApi.delete(filename),
    onSuccess: () => {
      invalidateAll()
    },
  })

  const verifyMutation = useMutation({
    mutationFn: ({ filename, request }: { filename: string; request?: FactorVerifyRequest }) =>
      factorApi.verify(filename, request),
    onSuccess: (data) => {
      queryClient.setQueryData(factorKeys.detail(data.filename), data)
      invalidateListAndStats()
    },
  })

  const unverifyMutation = useMutation({
    mutationFn: (filename: string) => factorApi.unverify(filename),
    onSuccess: (data) => {
      queryClient.setQueryData(factorKeys.detail(data.filename), data)
      invalidateListAndStats()
    },
  })

  const markFailedMutation = useMutation({
    mutationFn: ({ filename, request }: { filename: string; request?: FactorVerifyRequest }) =>
      factorApi.markFailed(filename, request),
    onSuccess: (data) => {
      queryClient.setQueryData(factorKeys.detail(data.filename), data)
      invalidateListAndStats()
    },
  })

  const excludeMutation = useMutation({
    mutationFn: ({ filename, reason }: { filename: string; reason?: string }) =>
      factorApi.exclude(filename, reason),
    onSuccess: (data) => {
      queryClient.setQueryData(factorKeys.detail(data.filename), data)
      invalidateListAndStats()
    },
  })

  const unexcludeMutation = useMutation({
    mutationFn: (filename: string) => factorApi.unexclude(filename),
    onSuccess: (data) => {
      queryClient.setQueryData(factorKeys.detail(data.filename), data)
      invalidateListAndStats()
    },
  })

  return {
    updateFactor: updateMutation,
    deleteFactor: deleteMutation,
    verifyFactor: verifyMutation,
    unverifyFactor: unverifyMutation,
    markFailedFactor: markFailedMutation,
    excludeFactor: excludeMutation,
    unexcludeFactor: unexcludeMutation,
  }
}

/**
 * Hook to get factor by filename with refetch capability
 */
export function useFactorDetail(filename: string | null) {
  const query = useFactor(filename || '')
  const mutations = useFactorMutations()

  return {
    factor: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    ...mutations,
  }
}

/**
 * Hook for factor group analysis
 */
export function useFactorGroupAnalysis() {
  return useMutation({
    mutationFn: (request: FactorGroupAnalysisRequest) => factorApi.analyzeGroups(request),
  })
}

/**
 * Hook for updating a single factor
 * Convenience wrapper that returns just the update mutation
 */
export function useUpdateFactor() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ filename, updates }: { filename: string; updates: FactorUpdate }) =>
      factorApi.update(filename, updates),
    onSuccess: (data) => {
      queryClient.setQueryData(factorKeys.detail(data.filename), data)
      queryClient.invalidateQueries({ queryKey: factorKeys.all })
    },
  })
}

/**
 * Hook for subscribing to fill task progress via SSE
 */
export function useFillProgress(taskId: string | null) {
  const [progress, setProgress] = useState<FillProgress | null>(null)
  const [logs, setLogs] = useState<FillLog[]>([])
  const [isConnected, setIsConnected] = useState(false)

  const reset = useCallback(() => {
    setProgress(null)
    setLogs([])
    setIsConnected(false)
  }, [])

  useEffect(() => {
    if (!taskId) {
      reset()
      return
    }

    const eventSource = new EventSource(`/api/v1/pipeline/fill/${taskId}/progress`)

    eventSource.addEventListener('progress', (event) => {
      try {
        const data: FillProgress = JSON.parse(event.data)
        setProgress(data)

        // 收集日志
        if (data.data?.type === 'factor_completed') {
          const progressData = data.data as FillProgressData
          setLogs((prev) => [
            ...prev,
            {
              factor: progressData.factor || '',
              field: progressData.field || '',
              success: progressData.success || false,
              value: progressData.value,
              error: progressData.error,
              timestamp: new Date(),
            },
          ])
        }
      } catch {
        // ignore parse errors
      }
    })

    eventSource.onopen = () => {
      setIsConnected(true)
    }

    eventSource.onerror = () => {
      setIsConnected(false)
      eventSource.close()
    }

    return () => {
      eventSource.close()
      setIsConnected(false)
    }
  }, [taskId, reset])

  const isRunning = progress?.status === 'running' || progress?.status === 'pending'
  const isCompleted = progress?.status === 'completed'
  const isFailed = progress?.status === 'failed'

  return {
    progress,
    logs,
    isConnected,
    isRunning,
    isCompleted,
    isFailed,
    reset,
  }
}
