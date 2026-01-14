/**
 * Strategy React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState, useCallback } from 'react'
import { strategyApi, backtestApi, taskApi, analysisApi } from './api'
import type {
  StrategyCreate,
  StrategyUpdate,
  StrategyListParams,
  BacktestRequest,
  BacktestStatus,
  BacktestResult,
  BatchBacktestRequest,
  BatchBacktestStatus,
  TaskExecution,
  CreateTaskRequest,
  UpdateTaskRequest,
  DuplicateTaskRequest,
  TaskListParams,
  ExecutionListParams,
  ExportToStrategyRequest,
  // 策略分析类型
  ParamSearchRequest,
  ParamAnalysisRequest,
  BacktestComparisonRequest,
  FactorComparisonRequest,
  StrategyComparisonRequest,
} from './types'

// Query Keys
export const strategyKeys = {
  all: ['strategies'] as const,
  lists: () => [...strategyKeys.all, 'list'] as const,
  list: (params: StrategyListParams) => [...strategyKeys.lists(), params] as const,
  details: () => [...strategyKeys.all, 'detail'] as const,
  detail: (id: string) => [...strategyKeys.details(), id] as const,
  stats: () => [...strategyKeys.all, 'stats'] as const,
}

export const backtestKeys = {
  all: ['backtest'] as const,
  config: () => [...backtestKeys.all, 'config'] as const,
  status: (taskId: string) => [...backtestKeys.all, 'status', taskId] as const,
  result: (taskId: string) => [...backtestKeys.all, 'result', taskId] as const,
  templates: () => [...backtestKeys.all, 'templates'] as const,
}

export const taskKeys = {
  all: ['tasks'] as const,
  lists: () => [...taskKeys.all, 'list'] as const,
  list: (params: TaskListParams) => [...taskKeys.lists(), params] as const,
  details: () => [...taskKeys.all, 'detail'] as const,
  detail: (id: string) => [...taskKeys.details(), id] as const,
  stats: (id: string) => [...taskKeys.all, 'stats', id] as const,
  executions: (taskId: string) => [...taskKeys.all, 'executions', taskId] as const,
  executionList: (taskId: string, params: ExecutionListParams) =>
    [...taskKeys.executions(taskId), params] as const,
  execution: (id: string) => [...taskKeys.all, 'execution', id] as const,
}

// 默认 stale time: 5 分钟
const DEFAULT_STALE_TIME = 5 * 60 * 1000

/**
 * Hook to fetch paginated strategy list
 */
export function useStrategies(params: StrategyListParams = {}) {
  return useQuery({
    queryKey: strategyKeys.list(params),
    queryFn: () => strategyApi.list(params),
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch a single strategy
 */
export function useStrategy(id: string) {
  return useQuery({
    queryKey: strategyKeys.detail(id),
    queryFn: () => strategyApi.get(id),
    enabled: !!id,
  })
}

/**
 * Hook to fetch strategy statistics
 */
export function useStrategyStats() {
  return useQuery({
    queryKey: strategyKeys.stats(),
    queryFn: strategyApi.getStats,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook for strategy mutations
 */
export function useStrategyMutations() {
  const queryClient = useQueryClient()

  const invalidateStrategies = () => {
    queryClient.invalidateQueries({ queryKey: strategyKeys.all })
  }

  const createMutation = useMutation({
    mutationFn: (request: StrategyCreate) => strategyApi.create(request),
    onSuccess: () => {
      invalidateStrategies()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, update }: { id: string; update: StrategyUpdate }) =>
      strategyApi.update(id, update),
    onSuccess: (data) => {
      queryClient.setQueryData(strategyKeys.detail(data.id), data)
      invalidateStrategies()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => strategyApi.delete(id),
    onSuccess: () => {
      invalidateStrategies()
    },
  })

  return {
    createStrategy: createMutation,
    updateStrategy: updateMutation,
    deleteStrategy: deleteMutation,
  }
}

/**
 * Hook to fetch backtest config (defaults and available factors)
 */
export function useBacktestConfig() {
  return useQuery({
    queryKey: backtestKeys.config(),
    queryFn: backtestApi.getConfig,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook to fetch backtest templates
 */
export function useBacktestTemplates() {
  return useQuery({
    queryKey: backtestKeys.templates(),
    queryFn: backtestApi.getTemplates,
  })
}

/**
 * Hook for backtest submission and status tracking
 * Uses polling instead of WebSocket for status updates
 */
export function useBacktest() {
  const [taskId, setTaskId] = useState<string | null>(null)
  const [status, setStatus] = useState<BacktestStatus | null>(null)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const submitMutation = useMutation({
    mutationFn: (request: BacktestRequest) => backtestApi.submit(request),
    onSuccess: (data) => {
      setTaskId(data.task_id)
      setStatus(data)
      setError(null)
      setResult(null)
    },
    onError: (err: Error) => {
      setError(err)
    },
  })

  // Poll for status updates
  const pollStatus = useCallback(async (taskId: string) => {
    try {
      const statusData = await backtestApi.getStatus(taskId)
      setStatus(statusData)

      // If completed, failed, or cancelled, fetch result and stop polling
      if (['completed', 'failed', 'cancelled'].includes(statusData.status)) {
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }

        // Fetch result if completed or failed
        if (statusData.status === 'completed' || statusData.status === 'failed') {
          try {
            const resultData = await backtestApi.getResult(taskId)
            setResult(resultData)
          } catch (e) {
            console.error('Failed to fetch result:', e)
          }
        }
      }
    } catch (e) {
      console.error('Failed to poll status:', e)
      // Stop polling on error
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
      setError(e instanceof Error ? e : new Error('Failed to get status'))
    }
  }, [])

  // Start polling when taskId changes
  useEffect(() => {
    if (taskId && !pollingRef.current) {
      // Initial poll
      pollStatus(taskId)

      // Start polling every 2 seconds
      pollingRef.current = setInterval(() => {
        pollStatus(taskId)
      }, 2000)
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [taskId, pollStatus])

  const cancelMutation = useMutation({
    mutationFn: (taskId: string) => backtestApi.cancel(taskId),
    onSuccess: () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
      setStatus((prev) =>
        prev ? { ...prev, status: 'cancelled' } : null
      )
    },
    onError: (err: Error) => {
      // Cancel may fail if task already completed, just update status
      setError(err)
    },
  })

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
    cancel: () => taskId && cancelMutation.mutate(taskId),
    reset,
    isSubmitting: submitMutation.isPending,
    isCancelling: cancelMutation.isPending,
    taskId,
    status,
    result,
    error,
    isRunning: status?.status === 'running' || status?.status === 'pending',
    isCompleted: status?.status === 'completed',
    isFailed: status?.status === 'failed',
    isCancelled: status?.status === 'cancelled',
  }
}

/**
 * Hook to fetch backtest result (polling fallback)
 */
export function useBacktestResult(taskId: string | null) {
  return useQuery({
    queryKey: backtestKeys.result(taskId || ''),
    queryFn: () => backtestApi.getResult(taskId!),
    enabled: !!taskId,
  })
}

/**
 * Hook for batch backtest submission and status tracking
 * 批量回测 hook，支持同时提交多个回测任务
 */
export function useBatchBacktest() {
  const [batchStatus, setBatchStatus] = useState<BatchBacktestStatus | null>(null)
  const [results, setResults] = useState<Map<string, BacktestResult>>(new Map())
  const [error, setError] = useState<Error | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const submitMutation = useMutation({
    mutationFn: (request: BatchBacktestRequest) => backtestApi.submitBatch(request),
    onSuccess: (data) => {
      setBatchStatus(data)
      setError(null)
      setResults(new Map())
    },
    onError: (err: Error) => {
      setError(err)
    },
  })

  // Poll for status updates
  const pollStatus = useCallback(async (taskIds: string[]) => {
    try {
      const statusData = await backtestApi.getBatchStatus(taskIds)
      setBatchStatus(statusData)

      // Check if all tasks are completed
      const allDone = statusData.tasks.every((t) =>
        ['completed', 'failed', 'cancelled'].includes(t.status)
      )

      if (allDone && pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null

        // Fetch results for completed tasks
        const completedTasks = statusData.tasks.filter(
          (t) => t.status === 'completed' || t.status === 'failed'
        )
        const newResults = new Map(results)

        await Promise.all(
          completedTasks.map(async (task) => {
            try {
              const resultData = await backtestApi.getResult(task.task_id)
              newResults.set(task.task_id, resultData)
            } catch (e) {
              console.error(`Failed to fetch result for ${task.task_id}:`, e)
            }
          })
        )

        setResults(newResults)
      }
    } catch (e) {
      console.error('Failed to poll batch status:', e)
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
      setError(e instanceof Error ? e : new Error('Failed to get batch status'))
    }
  }, [results])

  // Start polling when batch status changes
  useEffect(() => {
    if (batchStatus && batchStatus.tasks.length > 0 && !pollingRef.current) {
      const taskIds = batchStatus.tasks.map((t) => t.task_id)

      // Check if already all done
      const allDone = batchStatus.tasks.every((t) =>
        ['completed', 'failed', 'cancelled'].includes(t.status)
      )

      if (!allDone) {
        // Start polling every 2 seconds
        pollingRef.current = setInterval(() => {
          pollStatus(taskIds)
        }, 2000)
      }
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [batchStatus, pollStatus])

  const reset = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    setBatchStatus(null)
    setResults(new Map())
    setError(null)
  }, [])

  // Derived states
  const completedCount = batchStatus?.tasks.filter((t) => t.status === 'completed').length ?? 0
  const failedCount = batchStatus?.tasks.filter((t) => t.status === 'failed').length ?? 0
  const runningCount = batchStatus?.tasks.filter(
    (t) => t.status === 'running' || t.status === 'pending'
  ).length ?? 0

  return {
    submit: submitMutation.mutate,
    submitAsync: submitMutation.mutateAsync,
    reset,
    isSubmitting: submitMutation.isPending,
    batchStatus,
    results,
    error,
    // Progress tracking
    totalCount: batchStatus?.total ?? 0,
    completedCount,
    failedCount,
    runningCount,
    isAllDone: batchStatus ? runningCount === 0 : false,
    progress: batchStatus?.total ? ((completedCount + failedCount) / batchStatus.total) * 100 : 0,
  }
}

// =============================================================================
// 任务管理 Hooks
// =============================================================================

/**
 * Hook to fetch paginated task list
 */
export function useTasks(params: TaskListParams = {}) {
  return useQuery({
    queryKey: taskKeys.list(params),
    queryFn: () => taskApi.list(params),
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch a single task
 */
export function useTask(taskId: string) {
  return useQuery({
    queryKey: taskKeys.detail(taskId),
    queryFn: () => taskApi.get(taskId),
    enabled: !!taskId,
  })
}

/**
 * Hook to fetch task statistics
 */
export function useTaskStats(taskId: string) {
  return useQuery({
    queryKey: taskKeys.stats(taskId),
    queryFn: () => taskApi.getStats(taskId),
    enabled: !!taskId,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch task executions
 */
export function useTaskExecutions(taskId: string, params: ExecutionListParams = {}) {
  return useQuery({
    queryKey: taskKeys.executionList(taskId, params),
    queryFn: () => taskApi.listExecutions(taskId, params),
    enabled: !!taskId,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch a single execution
 */
export function useExecution(executionId: string) {
  return useQuery({
    queryKey: taskKeys.execution(executionId),
    queryFn: () => taskApi.getExecution(executionId),
    enabled: !!executionId,
  })
}

/**
 * Hook for task mutations (create, update, delete, duplicate)
 */
export function useTaskMutations() {
  const queryClient = useQueryClient()

  const invalidateTasks = () => {
    queryClient.invalidateQueries({ queryKey: taskKeys.all })
  }

  const createMutation = useMutation({
    mutationFn: (request: CreateTaskRequest) => taskApi.create(request),
    onSuccess: () => {
      invalidateTasks()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ taskId, request }: { taskId: string; request: UpdateTaskRequest }) =>
      taskApi.update(taskId, request),
    onSuccess: (data) => {
      queryClient.setQueryData(taskKeys.detail(data.id), data)
      invalidateTasks()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (taskId: string) => taskApi.delete(taskId),
    onSuccess: () => {
      invalidateTasks()
    },
  })

  const duplicateMutation = useMutation({
    mutationFn: ({ taskId, request }: { taskId: string; request: DuplicateTaskRequest }) =>
      taskApi.duplicate(taskId, request),
    onSuccess: () => {
      invalidateTasks()
    },
  })

  return {
    createTask: createMutation,
    updateTask: updateMutation,
    deleteTask: deleteMutation,
    duplicateTask: duplicateMutation,
  }
}

/**
 * Hook for task execution with polling
 */
export function useTaskExecution(taskId: string) {
  const queryClient = useQueryClient()
  const [executionId, setExecutionId] = useState<string | null>(null)
  const [execution, setExecution] = useState<TaskExecution | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const executeMutation = useMutation({
    mutationFn: () => taskApi.execute(taskId),
    onSuccess: (data) => {
      setExecutionId(data.execution_id)
      setError(null)
      // Invalidate task list to update execution count
      queryClient.invalidateQueries({ queryKey: taskKeys.all })
    },
    onError: (err: Error) => {
      setError(err)
    },
  })

  // Poll for execution status updates
  const pollExecution = useCallback(async (execId: string) => {
    try {
      const execData = await taskApi.getExecution(execId)
      setExecution(execData)

      // If completed, failed, or cancelled, stop polling
      if (['completed', 'failed', 'cancelled'].includes(execData.status)) {
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }
        // Invalidate executions list
        queryClient.invalidateQueries({ queryKey: taskKeys.executions(taskId) })
      }
    } catch (e) {
      console.error('Failed to poll execution status:', e)
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
      setError(e instanceof Error ? e : new Error('Failed to get execution status'))
    }
  }, [queryClient, taskId])

  // Start polling when executionId changes
  useEffect(() => {
    if (!executionId) return

    // Initial poll
    pollExecution(executionId)

    // Start polling every 2 seconds
    pollingRef.current = setInterval(() => {
      pollExecution(executionId)
    }, 2000)

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
    // 只依赖 executionId，避免 pollExecution 变化导致轮询重启
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [executionId])

  const reset = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    setExecutionId(null)
    setExecution(null)
    setError(null)
  }, [])

  return {
    execute: executeMutation.mutate,
    executeAsync: executeMutation.mutateAsync,
    reset,
    isExecuting: executeMutation.isPending,
    executionId,
    execution,
    error,
    isRunning: execution?.status === 'running' || execution?.status === 'pending',
    isCompleted: execution?.status === 'completed',
    isFailed: execution?.status === 'failed',
  }
}

/**
 * Hook for execution mutations (delete, export to strategy)
 */
export function useExecutionMutations() {
  const queryClient = useQueryClient()

  const deleteMutation = useMutation({
    mutationFn: (executionId: string) => taskApi.deleteExecution(executionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.all })
    },
  })

  const exportMutation = useMutation({
    mutationFn: ({
      executionId,
      request,
    }: {
      executionId: string
      request: ExportToStrategyRequest
    }) => taskApi.exportToStrategy(executionId, request),
    onSuccess: () => {
      // Invalidate strategies list as well
      queryClient.invalidateQueries({ queryKey: strategyKeys.all })
    },
  })

  return {
    deleteExecution: deleteMutation,
    exportToStrategy: exportMutation,
  }
}

// =============================================================================
// 策略分析 Hooks
// =============================================================================

/**
 * Hook for param search
 */
export function useParamSearch() {
  return useMutation({
    mutationFn: (request: ParamSearchRequest) => analysisApi.runParamSearch(request),
  })
}

/**
 * Hook for param analysis (heatmap/plain chart)
 */
export function useParamAnalysis() {
  return useMutation({
    mutationFn: (request: ParamAnalysisRequest) => analysisApi.analyzeParams(request),
  })
}

/**
 * Hook for backtest-live comparison
 */
export function useBacktestComparison() {
  return useMutation({
    mutationFn: (request: BacktestComparisonRequest) => analysisApi.compareBacktest(request),
  })
}

/**
 * Hook for factor value comparison
 */
export function useFactorComparison() {
  return useMutation({
    mutationFn: (request: FactorComparisonRequest) => analysisApi.compareFactorValues(request),
  })
}

/**
 * Hook for coin similarity analysis
 */
export function useCoinSimilarity() {
  return useMutation({
    mutationFn: (request: StrategyComparisonRequest) => analysisApi.analyzeCoinSimilarity(request),
  })
}

/**
 * Hook for equity correlation analysis
 */
export function useEquityCorrelation() {
  return useMutation({
    mutationFn: (request: StrategyComparisonRequest) =>
      analysisApi.analyzeEquityCorrelation(request),
  })
}
