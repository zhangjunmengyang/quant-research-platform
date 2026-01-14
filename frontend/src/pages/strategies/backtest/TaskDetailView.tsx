/**
 * Task Detail View Component
 * 任务详情视图组件
 */

import { useState, useEffect } from 'react'
import {
  Loader2,
  Play,
  Trash2,
  RefreshCw,
  ArrowUpRight,
} from 'lucide-react'
import {
  useTask,
  useTaskExecutions,
  useTaskExecution,
  useExecutionMutations,
} from '@/features/strategy'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { cn, formatPercent } from '@/lib/utils'
import type { TaskExecution } from '@/features/strategy'
import { parseJSON, formatDateTime, getStatusIcon, getStatusLabel } from './utils'
import type { TaskConfig } from '@/features/strategy'

export interface TaskDetailViewProps {
  taskId: string
  onBack: () => void
}

export function TaskDetailView({ taskId, onBack }: TaskDetailViewProps) {
  const { data: task, isLoading: taskLoading } = useTask(taskId)
  const { data: executions, isLoading: executionsLoading, refetch } = useTaskExecutions(taskId)
  const taskExecution = useTaskExecution(taskId)
  const { deleteExecution, exportToStrategy } = useExecutionMutations()

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [executionToDelete, setExecutionToDelete] = useState<TaskExecution | null>(null)
  const [exportDialogOpen, setExportDialogOpen] = useState(false)
  const [executionToExport, setExecutionToExport] = useState<TaskExecution | null>(null)
  const [exportName, setExportName] = useState('')

  // Refetch executions when a new execution completes
  useEffect(() => {
    if (taskExecution.isCompleted || taskExecution.isFailed) {
      refetch()
      // 使用 setTimeout 避免同步调用导致的状态混乱
      const timer = setTimeout(() => {
        taskExecution.reset()
      }, 0)
      return () => clearTimeout(timer)
    }
  }, [taskExecution.isCompleted, taskExecution.isFailed, refetch, taskExecution.reset])

  const config = task ? parseJSON<TaskConfig | null>(task.config, null) : null

  const handleExecute = () => {
    taskExecution.execute()
  }

  const handleDeleteExecution = (execution: TaskExecution) => {
    setExecutionToDelete(execution)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = () => {
    if (executionToDelete) {
      deleteExecution.mutate(executionToDelete.id, {
        onSuccess: () => {
          setDeleteDialogOpen(false)
          setExecutionToDelete(null)
          refetch()
        },
      })
    }
  }

  const handleExportClick = (execution: TaskExecution) => {
    setExecutionToExport(execution)
    setExportName(task?.name || '')
    setExportDialogOpen(true)
  }

  const handleExportConfirm = () => {
    if (executionToExport && exportName) {
      exportToStrategy.mutate(
        { executionId: executionToExport.id, request: { strategy_name: exportName } },
        {
          onSuccess: () => {
            setExportDialogOpen(false)
            setExecutionToExport(null)
            setExportName('')
            refetch()
          },
        }
      )
    }
  }

  if (taskLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!task) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <p className="text-muted-foreground">任务不存在</p>
        <button onClick={onBack} className="text-primary hover:underline">
          返回列表
        </button>
      </div>
    )
  }

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="rounded-md border p-2 hover:bg-accent">
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
          <div>
            <h1 className="text-xl font-semibold">{task.name}</h1>
            {task.description && (
              <p className="text-sm text-muted-foreground">{task.description}</p>
            )}
          </div>
        </div>
        <button
          onClick={handleExecute}
          disabled={taskExecution.isExecuting || taskExecution.isRunning}
          className="flex items-center gap-2 rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          {taskExecution.isExecuting || taskExecution.isRunning ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              执行中...
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              执行回测
            </>
          )}
        </button>
      </div>

      {/* Current Execution Progress */}
      {taskExecution.execution && (
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center gap-3">
            {getStatusIcon(taskExecution.execution.status)}
            <div className="flex-1">
              <p className="font-medium">当前执行</p>
              <p className="text-sm text-muted-foreground">
                {taskExecution.execution.message || getStatusLabel(taskExecution.execution.status)}
              </p>
            </div>
            {taskExecution.isRunning && (
              <div className="w-32">
                <div className="h-2 rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-blue-500 transition-all"
                    style={{ width: `${(taskExecution.execution.progress || 0) * 100}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: Config Summary */}
        <div className="space-y-6">
          <div className="rounded-lg border bg-card p-6">
            <h3 className="mb-4 font-semibold">任务配置</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">回测区间</span>
                <span className="font-medium">
                  {config?.start_date} ~ {config?.end_date}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">初始资金</span>
                <span className="font-medium">
                  {config?.initial_usdt?.toLocaleString()} USDT
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">杠杆倍数</span>
                <span className="font-medium">{config?.leverage}x</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">账户类型</span>
                <span className="font-medium">{config?.account_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">策略数量</span>
                <span className="font-medium">{config?.strategy_list?.length || 0}</span>
              </div>
            </div>
          </div>

          <div className="rounded-lg border bg-card p-6">
            <h3 className="mb-4 font-semibold">因子配置</h3>
            <div className="space-y-2">
              {config?.strategy_list?.map((stg, i) => (
                <div key={i} className="rounded bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground mb-1">
                    {stg.hold_period} | {stg.market} | 多{stg.long_select_coin_num}/空
                    {stg.short_select_coin_num}
                  </p>
                  <div className="space-y-1">
                    {stg.factor_list.map((f, j) => (
                      <p key={j} className="text-sm font-mono">
                        {f.name}({Array.isArray(f.param) ? f.param.join(',') : f.param})
                        {f.is_sort_asc ? '\u2191' : '\u2193'}
                      </p>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Execution History */}
        <div className="lg:col-span-2">
          <div className="rounded-lg border bg-card">
            <div className="flex items-center justify-between border-b px-4 py-3">
              <h3 className="font-semibold">执行历史</h3>
              <button
                onClick={() => refetch()}
                className="rounded p-1.5 hover:bg-muted"
                title="刷新"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>

            {executionsLoading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : executions?.items.length === 0 ? (
              <div className="flex h-32 items-center justify-center text-muted-foreground">
                暂无执行记录
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="px-4 py-2 text-left text-xs font-medium">状态</th>
                      <th className="px-4 py-2 text-center text-xs font-medium">净值</th>
                      <th className="px-4 py-2 text-center text-xs font-medium">年化</th>
                      <th className="px-4 py-2 text-center text-xs font-medium">回撤</th>
                      <th className="px-4 py-2 text-center text-xs font-medium">夏普</th>
                      <th className="px-4 py-2 text-center text-xs font-medium">执行时间</th>
                      <th className="px-4 py-2 text-center text-xs font-medium w-24">操作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {executions?.items.map((exec) => (
                      <tr key={exec.id} className="hover:bg-muted/50">
                        <td className="px-4 py-2">
                          <div className="flex items-center gap-2">
                            {getStatusIcon(exec.status)}
                            <span className="text-xs">{getStatusLabel(exec.status)}</span>
                          </div>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span
                            className={cn(
                              'text-sm font-medium',
                              exec.cumulative_return && exec.cumulative_return >= 1
                                ? 'text-green-600'
                                : 'text-red-600'
                            )}
                          >
                            {exec.cumulative_return?.toFixed(2) ?? '-'}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span
                            className={cn(
                              'text-sm font-medium',
                              exec.annual_return && exec.annual_return > 0
                                ? 'text-green-600'
                                : 'text-red-600'
                            )}
                          >
                            {formatPercent(exec.annual_return)}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span className="text-sm font-medium text-red-600">
                            {formatPercent(exec.max_drawdown)}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span
                            className={cn(
                              'text-sm font-medium',
                              exec.sharpe_ratio && exec.sharpe_ratio > 0
                                ? 'text-green-600'
                                : 'text-red-600'
                            )}
                          >
                            {exec.sharpe_ratio?.toFixed(2) ?? '-'}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span className="text-xs text-muted-foreground">
                            {formatDateTime(exec.created_at)}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <div className="flex items-center justify-center gap-1">
                            {exec.status === 'completed' && !exec.strategy_id && (
                              <button
                                onClick={() => handleExportClick(exec)}
                                className="rounded p-1.5 hover:bg-muted text-primary"
                                title="导出到策略库"
                              >
                                <ArrowUpRight className="h-4 w-4" />
                              </button>
                            )}
                            {exec.strategy_id && (
                              <span className="text-xs text-green-600">已导出</span>
                            )}
                            <button
                              onClick={() => handleDeleteExecution(exec)}
                              className="rounded p-1.5 hover:bg-muted text-muted-foreground hover:text-red-500"
                              title="删除"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Delete Execution Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="删除执行记录"
        description="确定要删除此执行记录吗? 此操作不可撤销。"
        confirmText="删除"
        cancelText="取消"
        onConfirm={handleDeleteConfirm}
        isLoading={deleteExecution.isPending}
        variant="danger"
      />

      {/* Export to Strategy Dialog */}
      <ConfirmDialog
        open={exportDialogOpen}
        onOpenChange={setExportDialogOpen}
        title="导出到策略库"
        description={
          <div className="space-y-3">
            <p>请输入策略名称:</p>
            <input
              type="text"
              value={exportName}
              onChange={(e) => setExportName(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="策略名称"
            />
          </div>
        }
        confirmText="导出"
        cancelText="取消"
        onConfirm={handleExportConfirm}
        isLoading={exportToStrategy.isPending}
      />
    </>
  )
}
