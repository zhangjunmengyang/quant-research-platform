/**
 * Stock Hub React Query Hooks
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, keepPreviousData } from '@tanstack/react-query'
import { stockApi } from './api'
import type {
  AnalysisResult,
  AnalysisTaskStatus,
  AnalysisTaskSubmit,
  DualAnalysisResult,
  EnhancedAnalysisRequest,
  DualAnalysisRequest,
  StockFactorListParams,
} from './types'

const STALE_TIME = 5 * 60 * 1000

export const stockKeys = {
  all: ['stock'] as const,
  status: () => [...stockKeys.all, 'status'] as const,
  factors: () => [...stockKeys.all, 'factors'] as const,
  factorList: (params: StockFactorListParams) => [...stockKeys.factors(), 'list', params] as const,
  factorDetail: (name: string) => [...stockKeys.factors(), 'detail', name] as const,
  categories: () => [...stockKeys.factors(), 'categories'] as const,
  backtests: () => [...stockKeys.all, 'backtests'] as const,
  cachedFactors: (name?: string) => [...stockKeys.all, 'cached-factors', name] as const,
}

export function useStockStatus() {
  return useQuery({
    queryKey: stockKeys.status(),
    queryFn: stockApi.getStatus,
    staleTime: STALE_TIME,
  })
}

export function useStockFactors(params: StockFactorListParams = {}) {
  return useQuery({
    queryKey: stockKeys.factorList(params),
    queryFn: () => stockApi.listFactors(params),
    placeholderData: keepPreviousData,
    staleTime: STALE_TIME,
  })
}

export function useStockFactorDetail(name: string | null) {
  return useQuery({
    queryKey: stockKeys.factorDetail(name ?? ''),
    queryFn: () => stockApi.getFactorDetail(name!),
    enabled: !!name,
    staleTime: STALE_TIME,
  })
}

export function useStockCategories() {
  return useQuery({
    queryKey: stockKeys.categories(),
    queryFn: stockApi.getCategories,
    staleTime: STALE_TIME,
  })
}

export function useAvailableBacktests() {
  return useQuery({
    queryKey: stockKeys.backtests(),
    queryFn: stockApi.listAvailableBacktests,
    staleTime: STALE_TIME,
  })
}

export function useCachedFactors(backtestName?: string) {
  return useQuery({
    queryKey: stockKeys.cachedFactors(backtestName),
    queryFn: () => stockApi.listCachedFactors(backtestName),
    staleTime: STALE_TIME,
  })
}

function useStockAnalysisTask<TRequest, TResult extends AnalysisResult | DualAnalysisResult>(
  submitFn: (req: TRequest) => Promise<AnalysisTaskSubmit>
) {
  const [taskId, setTaskId] = useState<string | null>(null)
  const [status, setStatus] = useState<AnalysisTaskStatus | null>(null)
  const [result, setResult] = useState<TResult | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const submitMutation = useMutation({
    mutationFn: submitFn,
    onSuccess: (data) => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
      setTaskId(data.task_id)
      setStatus(null)
      setResult(null)
      setError(null)
    },
    onError: (err: Error) => {
      setError(err)
    },
  })

  const pollStatus = useCallback(async (currentTaskId: string) => {
    try {
      const nextStatus = await stockApi.getAnalysisTaskStatus(currentTaskId)
      setStatus(nextStatus)

      if (['completed', 'failed'].includes(nextStatus.status)) {
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }

        if (nextStatus.status === 'completed') {
          const taskResult = await stockApi.getAnalysisTaskResult<TResult>(currentTaskId)
          setResult(taskResult.result ?? null)
          setError(null)
        } else {
          setResult(null)
          setError(new Error(nextStatus.error_message || 'Analysis task failed'))
        }
      }
    } catch (err) {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
      setError(err instanceof Error ? err : new Error('Failed to get analysis task status'))
    }
  }, [])

  useEffect(() => {
    if (taskId && !pollingRef.current) {
      void pollStatus(taskId)
      pollingRef.current = setInterval(() => {
        void pollStatus(taskId)
      }, 2000)
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [taskId, pollStatus])

  const reset = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    setTaskId(null)
    setStatus(null)
    setResult(null)
    setError(null)
  }, [])

  return {
    submit: submitMutation.mutate,
    submitAsync: submitMutation.mutateAsync,
    reset,
    taskId,
    status,
    result,
    error,
    isSubmitting: submitMutation.isPending,
    isRunning: status?.status === 'pending' || status?.status === 'running',
    isCompleted: status?.status === 'completed',
    isFailed: status?.status === 'failed',
  }
}

export function useEnhancedAnalysis() {
  return useStockAnalysisTask<EnhancedAnalysisRequest, AnalysisResult>((req) =>
    stockApi.runEnhancedAnalysis(req)
  )
}

export function useDualAnalysis() {
  return useStockAnalysisTask<DualAnalysisRequest, DualAnalysisResult>((req) =>
    stockApi.runDualAnalysis(req)
  )
}
