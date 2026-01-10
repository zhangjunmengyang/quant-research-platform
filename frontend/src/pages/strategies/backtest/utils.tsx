/**
 * Backtest Page Utility Functions
 * 回测页面工具函数
 */

import { Clock, Loader2, CheckCircle2, XCircle } from 'lucide-react'
import type { TaskConfig } from '@/features/strategy'

/**
 * 格式化日期时间为简短格式
 */
export function formatDateTime(dateStr: string | undefined | null): string {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr.split('T')[0] || '-'
  }
}

/**
 * 安全解析 JSON 字符串
 */
export function parseJSON<T>(json: string | undefined | null, defaultValue: T): T {
  if (!json) return defaultValue
  try {
    return JSON.parse(json) as T
  } catch {
    return defaultValue
  }
}

/**
 * 获取状态图标
 */
export function getStatusIcon(status: string | undefined) {
  switch (status) {
    case 'pending':
      return <Clock className="h-4 w-4 text-yellow-500" />
    case 'running':
      return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
    case 'completed':
      return <CheckCircle2 className="h-4 w-4 text-green-500" />
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-500" />
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />
  }
}

/**
 * 获取状态标签文本
 */
export function getStatusLabel(status: string | undefined) {
  switch (status) {
    case 'pending':
      return '等待中'
    case 'running':
      return '执行中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    default:
      return '未知'
  }
}

/**
 * 从配置中格式化因子列表
 */
export function formatFactorListFromConfig(config: TaskConfig | null): string {
  if (!config?.strategy_list?.length) return '-'
  const factors = config.strategy_list.flatMap((s) =>
    s.factor_list.map((f) => {
      const param = Array.isArray(f.param) ? f.param.join(',') : f.param
      const dir = f.is_sort_asc ? '\u2191' : '\u2193'
      return `${f.name}(${param})${dir}`
    })
  )
  return factors.join(', ') || '-'
}
