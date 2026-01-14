/**
 * 通用轮询 Hook
 * 用于定期轮询任务状态，支持自动停止和错误处理
 */

import { useEffect, useRef, useCallback, useState } from 'react'

/**
 * 轮询状态
 */
export type PollingStatus = 'idle' | 'polling' | 'success' | 'error' | 'cancelled'

/**
 * 轮询配置
 */
export interface PollingConfig<T> {
  // 轮询查询函数
  queryFn: () => Promise<T>
  // 判断是否为终止状态（返回 true 停止轮询）
  isTerminal: (data: T) => boolean
  // 轮询间隔（毫秒），默认 2000
  interval?: number
  // 是否立即执行第一次轮询，默认 true
  immediate?: boolean
  // 轮询开始条件，默认 true
  enabled?: boolean
  // 成功回调
  onSuccess?: (data: T) => void
  // 错误回调
  onError?: (error: Error) => void
  // 终止回调
  onTerminal?: (data: T) => void
}

/**
 * 轮询状态
 */
export interface PollingState<T> {
  status: PollingStatus
  data: T | null
  error: Error | null
  isPolling: boolean
}

/**
 * 通用轮询 Hook
 */
export function usePolling<T>(config: PollingConfig<T>) {
  const {
    queryFn,
    isTerminal,
    interval = 2000,
    immediate = true,
    enabled = true,
    onSuccess,
    onError,
    onTerminal,
  } = config

  const [state, setState] = useState<PollingState<T>>({
    status: 'idle',
    data: null,
    error: null,
    isPolling: false,
  })

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const isActiveRef = useRef(false)
  const isMountedRef = useRef(true)

  // 组件卸载时标记
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  // 执行单次轮询
  const poll = useCallback(async () => {
    if (!enabled || isActiveRef.current) return

    try {
      isActiveRef.current = true
      const data = await queryFn()

      // 检查组件是否已卸载
      if (!isMountedRef.current) return

      setState((prev) => ({
        ...prev,
        status: 'polling',
        data,
        error: null,
      }))

      onSuccess?.(data)

      // 检查是否达到终止状态
      if (isTerminal(data)) {
        stopPolling()
        if (!isMountedRef.current) return
        setState((prev) => ({
          ...prev,
          status: 'success',
          isPolling: false,
        }))
        onTerminal?.(data)
      }
    } catch (error) {
      // 检查组件是否已卸载
      if (!isMountedRef.current) return

      const err = error instanceof Error ? error : new Error('Polling failed')
      setState((prev) => ({
        ...prev,
        status: 'error',
        error: err,
        isPolling: false,
      }))
      onError?.(err)
      stopPolling()
    } finally {
      isActiveRef.current = false
    }
  }, [enabled, queryFn, isTerminal, onSuccess, onError, onTerminal])

  // 停止轮询
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    isActiveRef.current = false
  }, [])

  // 开始轮询
  const startPolling = useCallback(() => {
    if (!enabled || pollingRef.current) return

    setState((prev) => ({ ...prev, status: 'polling', isPolling: true }))

    // 立即执行第一次
    if (immediate) {
      poll()
    }

    // 启动定时轮询
    pollingRef.current = setInterval(() => {
      poll()
    }, interval)
  }, [enabled, immediate, interval, poll])

  // 重置状态
  const reset = useCallback(() => {
    stopPolling()
    setState({
      status: 'idle',
      data: null,
      error: null,
      isPolling: false,
    })
  }, [stopPolling])

  // 手动触发一次轮询
  const refetch = useCallback(() => {
    poll()
  }, [poll])

  // 当 enabled 变化时自动开始/停止
  useEffect(() => {
    if (enabled && state.status === 'idle') {
      startPolling()
    } else if (!enabled) {
      stopPolling()
    }
    // 依赖 state.status 以便在状态变回 idle 时重新启动
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, state.status])

  // 清理
  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [stopPolling])

  return {
    // 状态
    status: state.status,
    data: state.data,
    error: state.error,
    isPolling: state.isPolling,
    isIdle: state.status === 'idle',
    isSuccess: state.status === 'success',
    isError: state.status === 'error',
    // 操作
    start: startPolling,
    stop: stopPolling,
    reset,
    refetch,
  }
}

/**
 * 简化版轮询 Hook - 用于简单的任务状态轮询
 */
export function useTaskPolling(taskId: string | null, getStatusFn: (id: string) => Promise<any>) {
  return usePolling({
    queryFn: () => getStatusFn(taskId!),
    isTerminal: (data) => ['completed', 'failed', 'cancelled'].includes(data.status),
    enabled: !!taskId,
  })
}
