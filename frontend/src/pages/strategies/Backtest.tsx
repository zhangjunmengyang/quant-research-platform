/**
 * Backtest Task Management Page
 * 回测任务管理页 - 任务列表、创建、执行和历史记录管理
 *
 * 核心概念:
 * - BacktestTask: 任务单（配置模板），可被多次执行
 * - TaskExecution: 执行记录，每次执行的状态和结果
 */

import { useState, useEffect, useCallback } from 'react'
import {
  Loader2,
  Play,
  Plus,
  Trash2,
  Settings,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Copy,
  History,
  ListTodo,
  ArrowUpRight,
} from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import {
  useTasks,
  useTask,
  useTaskExecutions,
  useTaskMutations,
  useTaskExecution,
  useExecutionMutations,
  useBacktestTemplates,
  useBacktestConfig,
  createDefaultBacktestRequest,
  createDefaultStrategyItem,
  createDefaultFactorItem,
} from '@/features/strategy'
import { StatsCard } from '@/features/factor/components/StatsCard'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { cn, formatPercent } from '@/lib/utils'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'
import type {
  BacktestTask,
  TaskExecution,
  BacktestRequest,
  StrategyItem,
  FactorItem,
  TaskConfig,
} from '@/features/strategy'

// 账户类型选项
const ACCOUNT_TYPE_OPTIONS: SelectOption[] = [
  { value: '统一账户', label: '统一账户' },
  { value: '普通账户', label: '普通账户' },
]

// hold_period 选项
const HOLD_PERIOD_OPTIONS: SelectOption[] = [
  { value: '1H', label: '1H' },
  { value: '2H', label: '2H' },
  { value: '4H', label: '4H' },
  { value: '6H', label: '6H' },
  { value: '8H', label: '8H' },
  { value: '12H', label: '12H' },
  { value: '1D', label: '1D' },
  { value: '3D', label: '3D' },
  { value: '7D', label: '7D' },
]

// market 选项
const MARKET_OPTIONS: SelectOption[] = [
  { value: 'swap_swap', label: 'swap_swap' },
  { value: 'spot_spot', label: 'spot_spot' },
  { value: 'spot_swap', label: 'spot_swap' },
  { value: 'mix_swap', label: 'mix_swap' },
  { value: 'mix_spot', label: 'mix_spot' },
]

// 排序方向选项
const SORT_OPTIONS: SelectOption[] = [
  { value: 'true', label: 'Asc' },
  { value: 'false', label: 'Desc' },
]

// =============================================================================
// Helper Functions
// =============================================================================

function formatDateTime(dateStr: string | undefined | null): string {
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

function parseJSON<T>(json: string | undefined | null, defaultValue: T): T {
  if (!json) return defaultValue
  try {
    return JSON.parse(json) as T
  } catch {
    return defaultValue
  }
}

function getStatusIcon(status: string | undefined) {
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

function getStatusLabel(status: string | undefined) {
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

function formatFactorListFromConfig(config: TaskConfig | null): string {
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

// =============================================================================
// Main Component
// =============================================================================

type ViewMode = 'list' | 'create' | 'detail'

export function Component() {
  const [searchParams, setSearchParams] = useSearchParams()
  const viewMode = (searchParams.get('view') as ViewMode) || 'list'
  const detailId = searchParams.get('id')

  const setViewMode = useCallback(
    (mode: ViewMode, id?: string) => {
      const params = new URLSearchParams()
      params.set('view', mode)
      if (id) params.set('id', id)
      setSearchParams(params)
    },
    [setSearchParams]
  )

  return (
    <div className="space-y-6">
      {viewMode === 'list' && (
        <TaskListView
          onViewDetail={(id) => setViewMode('detail', id)}
          onCreateNew={() => setViewMode('create')}
        />
      )}
      {viewMode === 'create' && (
        <TaskCreateView
          onBack={() => setViewMode('list')}
          onCreated={(id) => setViewMode('detail', id)}
        />
      )}
      {viewMode === 'detail' && detailId && (
        <TaskDetailView taskId={detailId} onBack={() => setViewMode('list')} />
      )}
    </div>
  )
}

// =============================================================================
// Task List View
// =============================================================================

interface TaskListViewProps {
  onViewDetail: (id: string) => void
  onCreateNew: () => void
}

function TaskListView({ onViewDetail, onCreateNew }: TaskListViewProps) {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [taskToDelete, setTaskToDelete] = useState<BacktestTask | null>(null)
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false)
  const [taskToDuplicate, setTaskToDuplicate] = useState<BacktestTask | null>(null)
  const [newTaskName, setNewTaskName] = useState('')

  const { data, isLoading, refetch } = useTasks({
    page,
    page_size: 20,
    search: search || undefined,
    order_by: 'created_at',
    order_desc: true,
  })
  const { deleteTask, duplicateTask } = useTaskMutations()

  // Stats calculation
  const totalTasks = data?.total ?? 0

  const handleDeleteClick = (task: BacktestTask) => {
    setTaskToDelete(task)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = () => {
    if (taskToDelete) {
      deleteTask.mutate(taskToDelete.id, {
        onSuccess: () => {
          setDeleteDialogOpen(false)
          setTaskToDelete(null)
        },
      })
    }
  }

  const handleDuplicateClick = (task: BacktestTask) => {
    setTaskToDuplicate(task)
    setNewTaskName(`${task.name} (副本)`)
    setDuplicateDialogOpen(true)
  }

  const handleDuplicateConfirm = () => {
    if (taskToDuplicate && newTaskName) {
      duplicateTask.mutate(
        { taskId: taskToDuplicate.id, request: { new_name: newTaskName } },
        {
          onSuccess: () => {
            setDuplicateDialogOpen(false)
            setTaskToDuplicate(null)
            setNewTaskName('')
          },
        }
      )
    }
  }

  return (
    <>
      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="任务总数"
          value={totalTasks}
          icon={<ListTodo className="h-5 w-5" />}
        />
        <StatsCard
          title="今日创建"
          value={'-'}
          icon={<Plus className="h-5 w-5" />}
        />
        <StatsCard
          title="执行中"
          value={'-'}
          icon={<Loader2 className="h-5 w-5" />}
        />
        <StatsCard
          title="历史执行"
          value={'-'}
          icon={<History className="h-5 w-5" />}
        />
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="搜索任务..."
            className="w-64 rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
          <button
            onClick={() => refetch()}
            className="rounded-md border border-input p-2 hover:bg-accent"
            title="刷新"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>

        <button
          onClick={onCreateNew}
          className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          新建任务
        </button>
      </div>

      {/* Task List */}
      <div className="rounded-lg border bg-card">
        <div className="border-b px-4 py-3">
          <h3 className="font-semibold">任务列表</h3>
        </div>
        {isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : data?.items.length === 0 ? (
          <div className="flex h-32 flex-col items-center justify-center gap-2 text-muted-foreground">
            <p>暂无任务</p>
            <button
              onClick={onCreateNew}
              className="text-sm text-primary hover:underline"
            >
              创建第一个任务
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-3 text-left text-sm font-medium">任务名称</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">因子配置</th>
                  <th className="px-4 py-3 text-center text-sm font-medium">执行次数</th>
                  <th className="px-4 py-3 text-center text-sm font-medium">最后执行</th>
                  <th className="px-4 py-3 text-center text-sm font-medium">创建时间</th>
                  <th className="px-4 py-3 text-center text-sm font-medium w-32">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data?.items.map((task) => {
                  const config = parseJSON<TaskConfig | null>(task.config, null)
                  return (
                    <tr
                      key={task.id}
                      className="hover:bg-muted/50 transition-colors cursor-pointer"
                      onClick={() => onViewDetail(task.id)}
                    >
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium">{task.name}</p>
                          {task.description && (
                            <p className="text-xs text-muted-foreground line-clamp-1">
                              {task.description}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[250px]">
                        <p
                          className="text-sm text-muted-foreground truncate font-mono"
                          title={formatFactorListFromConfig(config)}
                        >
                          {formatFactorListFromConfig(config)}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="inline-flex items-center gap-1 text-sm">
                          <History className="h-3 w-3" />
                          {task.execution_count}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-xs text-muted-foreground">
                          {formatDateTime(task.last_execution_at)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-xs text-muted-foreground">
                          {formatDateTime(task.created_at)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div
                          className="flex items-center justify-center gap-1"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            onClick={() => onViewDetail(task.id)}
                            className="rounded p-1.5 hover:bg-muted"
                            title="查看详情"
                          >
                            <ArrowUpRight className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDuplicateClick(task)}
                            className="rounded p-1.5 hover:bg-muted"
                            title="复制任务"
                          >
                            <Copy className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteClick(task)}
                            disabled={deleteTask.isPending}
                            className="rounded p-1.5 hover:bg-muted text-muted-foreground hover:text-red-500"
                            title="删除"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.total > 0 && (
          <div className="flex items-center justify-between border-t px-4 py-3">
            <p className="text-sm text-muted-foreground">
              显示 {(data.page - 1) * data.page_size + 1}-
              {Math.min(data.page * data.page_size, data.total)} / 共 {data.total} 条
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(data.page - 1)}
                disabled={data.page <= 1}
                className="rounded-md border p-2 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-accent"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="px-3 text-sm">
                {data.page} / {data.total_pages}
              </span>
              <button
                onClick={() => setPage(data.page + 1)}
                disabled={data.page >= data.total_pages}
                className="rounded-md border p-2 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-accent"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirm Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="删除任务"
        description={`确定要删除任务"${taskToDelete?.name}"吗? 将同时删除所有执行记录，此操作不可撤销。`}
        confirmText="删除"
        cancelText="取消"
        onConfirm={handleDeleteConfirm}
        isLoading={deleteTask.isPending}
        variant="danger"
      />

      {/* Duplicate Dialog */}
      <ConfirmDialog
        open={duplicateDialogOpen}
        onOpenChange={setDuplicateDialogOpen}
        title="复制任务"
        description={
          <div className="space-y-3">
            <p>请输入新任务的名称:</p>
            <input
              type="text"
              value={newTaskName}
              onChange={(e) => setNewTaskName(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="任务名称"
            />
          </div>
        }
        confirmText="复制"
        cancelText="取消"
        onConfirm={handleDuplicateConfirm}
        isLoading={duplicateTask.isPending}
      />
    </>
  )
}

// =============================================================================
// Task Create View
// =============================================================================

interface TaskCreateViewProps {
  onBack: () => void
  onCreated: (id: string) => void
}

function TaskCreateView({ onBack, onCreated }: TaskCreateViewProps) {
  const { data: templates = [], isLoading: templatesLoading } = useBacktestTemplates()
  const { data: config } = useBacktestConfig()
  const { createTask } = useTaskMutations()

  const [formData, setFormData] = useState<BacktestRequest>(createDefaultBacktestRequest())
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [newFactorName, setNewFactorName] = useState('')

  // Use server config for defaults
  useEffect(() => {
    if (config) {
      setFormData((prev) => ({
        ...prev,
        start_date: config.start_date,
        end_date: config.end_date,
        initial_usdt: config.initial_usdt,
        leverage: config.leverage,
        margin_rate: config.margin_rate,
        swap_c_rate: config.swap_c_rate,
        spot_c_rate: config.spot_c_rate,
        swap_min_order_limit: config.swap_min_order_limit,
        spot_min_order_limit: config.spot_min_order_limit,
        avg_price_col: config.avg_price_col as 'avg_price_1m' | 'avg_price_5m',
        min_kline_num: config.min_kline_num,
      }))
    }
  }, [config])

  const handleTemplateSelect = (templateName: string) => {
    const template = templates.find((t) => t.name === templateName)
    if (template) {
      setSelectedTemplate(templateName)
      setFormData((prev) => ({
        ...prev,
        name: template.name,
        strategy_list: template.strategy_list,
        leverage: template.default_config?.leverage ?? prev.leverage,
        initial_usdt: template.default_config?.initial_usdt ?? prev.initial_usdt,
      }))
    }
  }

  const handleAddStrategy = () => {
    const newStrategy = createDefaultStrategyItem()
    newStrategy.strategy = `Strategy_${formData.strategy_list.length + 1}`
    setFormData((prev) => ({
      ...prev,
      strategy_list: [...prev.strategy_list, newStrategy],
    }))
  }

  const handleRemoveStrategy = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      strategy_list: prev.strategy_list.filter((_, i) => i !== index),
    }))
  }

  const handleStrategyChange = (index: number, field: keyof StrategyItem, value: unknown) => {
    setFormData((prev) => ({
      ...prev,
      strategy_list: prev.strategy_list.map((stg, i) =>
        i === index ? { ...stg, [field]: value } : stg
      ),
    }))
  }

  const handleAddFactor = (strategyIndex: number) => {
    if (!newFactorName.trim()) return

    const factor = createDefaultFactorItem(newFactorName.trim())
    setFormData((prev) => ({
      ...prev,
      strategy_list: prev.strategy_list.map((stg, i) =>
        i === strategyIndex ? { ...stg, factor_list: [...stg.factor_list, factor] } : stg
      ),
    }))
    setNewFactorName('')
  }

  const handleRemoveFactor = (strategyIndex: number, factorIndex: number) => {
    setFormData((prev) => ({
      ...prev,
      strategy_list: prev.strategy_list.map((stg, i) =>
        i === strategyIndex
          ? { ...stg, factor_list: stg.factor_list.filter((_, j) => j !== factorIndex) }
          : stg
      ),
    }))
  }

  const handleFactorChange = (
    strategyIndex: number,
    factorIndex: number,
    field: keyof FactorItem,
    value: unknown
  ) => {
    setFormData((prev) => ({
      ...prev,
      strategy_list: prev.strategy_list.map((stg, i) =>
        i === strategyIndex
          ? {
              ...stg,
              factor_list: stg.factor_list.map((f, j) =>
                j === factorIndex ? { ...f, [field]: value } : f
              ),
            }
          : stg
      ),
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name || formData.strategy_list.length === 0) return

    const hasFactors = formData.strategy_list.every((stg) => stg.factor_list.length > 0)
    if (!hasFactors) return

    createTask.mutate(
      {
        name: formData.name,
        description: undefined,
        config: formData,
      },
      {
        onSuccess: (task) => {
          onCreated(task.id)
        },
      }
    )
  }

  const canSubmit =
    formData.name &&
    formData.strategy_list.length > 0 &&
    formData.strategy_list.every((stg) => stg.factor_list.length > 0)

  return (
    <>
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={onBack} className="rounded-md border p-2 hover:bg-accent">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <h1 className="text-xl font-semibold">创建回测任务</h1>
      </div>

      <form onSubmit={handleSubmit} className="grid gap-6 lg:grid-cols-3">
        {/* Left: Form */}
        <div className="space-y-6 lg:col-span-2">
          {/* Templates */}
          <div className="rounded-lg border bg-card p-6">
            <h3 className="mb-4 font-semibold">选择模板 (可选)</h3>
            {templatesLoading ? (
              <div className="flex h-20 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {templates.map((template) => (
                  <button
                    key={template.name}
                    type="button"
                    onClick={() => handleTemplateSelect(template.name)}
                    className={cn(
                      'rounded-lg border p-4 text-left transition-colors',
                      selectedTemplate === template.name
                        ? 'border-primary bg-primary/5'
                        : 'hover:bg-muted/50'
                    )}
                  >
                    <p className="font-medium">{template.name}</p>
                    {template.description && (
                      <p className="mt-1 text-sm text-muted-foreground">{template.description}</p>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Basic Config */}
          <div className="rounded-lg border bg-card p-6">
            <h3 className="mb-4 font-semibold">基本配置</h3>
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">任务名称 *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  placeholder="输入任务名称"
                  required
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium">开始日期</label>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, start_date: e.target.value }))
                    }
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    required
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">结束日期</label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData((prev) => ({ ...prev, end_date: e.target.value }))}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    required
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label className="mb-1 block text-sm font-medium">初始资金</label>
                  <input
                    type="number"
                    value={formData.initial_usdt}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        initial_usdt: parseFloat(e.target.value) || 10000,
                      }))
                    }
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    min="100"
                    step="100"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">杠杆倍数</label>
                  <input
                    type="number"
                    value={formData.leverage}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        leverage: parseFloat(e.target.value) || 1,
                      }))
                    }
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    min="0.1"
                    max="10"
                    step="0.1"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">账户类型</label>
                  <SearchableSelect
                    options={ACCOUNT_TYPE_OPTIONS}
                    value={formData.account_type}
                    onChange={(value) =>
                      setFormData((prev) => ({
                        ...prev,
                        account_type: value as '统一账户' | '普通账户',
                      }))
                    }
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Strategy List */}
          <div className="rounded-lg border bg-card p-6">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-semibold">策略配置 *</h3>
              <button
                type="button"
                onClick={handleAddStrategy}
                className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
              >
                <Plus className="h-3 w-3" />
                添加策略
              </button>
            </div>

            {formData.strategy_list.length === 0 ? (
              <p className="text-sm text-muted-foreground">请添加策略或选择模板</p>
            ) : (
              <div className="space-y-4">
                {formData.strategy_list.map((stg, stgIndex) => (
                  <StrategyConfigCard
                    key={stgIndex}
                    index={stgIndex}
                    strategy={stg}
                    availableFactors={config?.available_factors || []}
                    newFactorName={newFactorName}
                    onNewFactorNameChange={setNewFactorName}
                    onStrategyChange={handleStrategyChange}
                    onRemoveStrategy={handleRemoveStrategy}
                    onAddFactor={handleAddFactor}
                    onRemoveFactor={handleRemoveFactor}
                    onFactorChange={handleFactorChange}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Advanced Config */}
          <div className="rounded-lg border bg-card">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex w-full items-center justify-between p-4"
            >
              <div className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                <span className="font-medium">高级配置</span>
              </div>
              {showAdvanced ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>

            {showAdvanced && (
              <div className="space-y-4 border-t p-6">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-sm font-medium">合约手续费率</label>
                    <input
                      type="number"
                      value={formData.swap_c_rate}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          swap_c_rate: parseFloat(e.target.value) || 0.0006,
                        }))
                      }
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      step="0.0001"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium">现货手续费率</label>
                    <input
                      type="number"
                      value={formData.spot_c_rate}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          spot_c_rate: parseFloat(e.target.value) || 0.001,
                        }))
                      }
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      step="0.0001"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Summary & Submit */}
        <div className="space-y-6">
          <div className="rounded-lg border bg-card p-6 sticky top-6">
            <h3 className="mb-4 font-semibold">任务摘要</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">名称</span>
                <span className="font-medium">{formData.name || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">回测区间</span>
                <span className="font-medium">
                  {formData.start_date} ~ {formData.end_date}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">初始资金</span>
                <span className="font-medium">{formData.initial_usdt.toLocaleString()} USDT</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">杠杆倍数</span>
                <span className="font-medium">{formData.leverage}x</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">策略数量</span>
                <span className="font-medium">{formData.strategy_list.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">因子数量</span>
                <span className="font-medium">
                  {formData.strategy_list.reduce((acc, s) => acc + s.factor_list.length, 0)}
                </span>
              </div>
            </div>

            <div className="mt-6 space-y-2">
              <button
                type="submit"
                disabled={!canSubmit || createTask.isPending}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {createTask.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    创建中...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4" />
                    创建任务
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={onBack}
                className="w-full rounded-md border border-input px-4 py-2.5 text-sm font-medium hover:bg-accent"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      </form>
    </>
  )
}

// =============================================================================
// Strategy Config Card Component
// =============================================================================

interface StrategyConfigCardProps {
  index: number
  strategy: StrategyItem
  availableFactors: string[]
  newFactorName: string
  onNewFactorNameChange: (name: string) => void
  onStrategyChange: (index: number, field: keyof StrategyItem, value: unknown) => void
  onRemoveStrategy: (index: number) => void
  onAddFactor: (strategyIndex: number) => void
  onRemoveFactor: (strategyIndex: number, factorIndex: number) => void
  onFactorChange: (
    strategyIndex: number,
    factorIndex: number,
    field: keyof FactorItem,
    value: unknown
  ) => void
}

function StrategyConfigCard({
  index,
  strategy,
  availableFactors,
  newFactorName,
  onNewFactorNameChange,
  onStrategyChange,
  onRemoveStrategy,
  onAddFactor,
  onRemoveFactor,
  onFactorChange,
}: StrategyConfigCardProps) {
  return (
    <div className="rounded-md border p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-medium">策略 #{index + 1}</span>
        <button
          type="button"
          onClick={() => onRemoveStrategy(index)}
          className="text-red-500 hover:text-red-700"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs">hold_period</label>
          <SearchableSelect
            options={HOLD_PERIOD_OPTIONS}
            value={strategy.hold_period}
            onChange={(value) => onStrategyChange(index, 'hold_period', value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs">market</label>
          <SearchableSelect
            options={MARKET_OPTIONS}
            value={strategy.market}
            onChange={(value) => onStrategyChange(index, 'market', value)}
          />
        </div>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs">long_select_coin_num</label>
          <input
            type="number"
            value={strategy.long_select_coin_num}
            onChange={(e) =>
              onStrategyChange(index, 'long_select_coin_num', parseFloat(e.target.value) || 0)
            }
            className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
            min="0"
            step="any"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs">short_select_coin_num</label>
          <input
            type="text"
            value={strategy.short_select_coin_num}
            onChange={(e) => {
              const val = e.target.value
              if (val === 'long_nums' || val === '') {
                onStrategyChange(index, 'short_select_coin_num', val || 0)
              } else {
                const num = parseFloat(val)
                onStrategyChange(index, 'short_select_coin_num', isNaN(num) ? val : num)
              }
            }}
            className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
            placeholder="数字或 long_nums"
          />
        </div>
      </div>

      {/* Factor List */}
      <div className="mt-3">
        <label className="mb-1 block text-xs font-medium">factor_list *</label>
        <div className="space-y-2">
          {strategy.factor_list.map((factor, fIndex) => (
            <div key={fIndex} className="flex items-center gap-2 rounded bg-muted/50 p-2">
              <span className="min-w-[100px] text-sm font-medium">{factor.name}</span>
              <SearchableSelect
                options={SORT_OPTIONS}
                value={factor.is_sort_asc ? 'true' : 'false'}
                onChange={(value) =>
                  onFactorChange(index, fIndex, 'is_sort_asc', value === 'true')
                }
                className="w-20"
              />
              <input
                type="text"
                value={Array.isArray(factor.param) ? factor.param.join(',') : factor.param}
                onChange={(e) => {
                  const val = e.target.value
                  if (val.includes(',')) {
                    const nums = val
                      .split(',')
                      .map((s) => parseInt(s.trim()))
                      .filter((n) => !isNaN(n))
                    onFactorChange(index, fIndex, 'param', nums.length > 0 ? nums : 0)
                  } else {
                    onFactorChange(index, fIndex, 'param', val === '' ? '' : parseInt(val) || 0)
                  }
                }}
                className="w-20 rounded border border-input bg-background px-2 py-1 text-xs"
                placeholder="param"
              />
              <input
                type="number"
                value={factor.weight}
                onChange={(e) =>
                  onFactorChange(index, fIndex, 'weight', parseFloat(e.target.value) || 1)
                }
                className="w-16 rounded border border-input bg-background px-2 py-1 text-xs"
                placeholder="weight"
                step="0.1"
              />
              <button
                type="button"
                onClick={() => onRemoveFactor(index, fIndex)}
                className="text-red-500 hover:text-red-700"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          ))}
          <div className="flex gap-2">
            <SearchableSelect
              options={availableFactors.map((f) => ({ value: f, label: f }))}
              value={newFactorName}
              onChange={onNewFactorNameChange}
              placeholder="选择因子..."
              searchPlaceholder="搜索因子..."
              emptyText="无匹配因子"
              className="flex-1"
            />
            <button
              type="button"
              onClick={() => onAddFactor(index)}
              disabled={!newFactorName}
              className="rounded-md bg-secondary px-3 py-1.5 text-xs font-medium hover:bg-secondary/80 disabled:opacity-50"
            >
              添加
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Task Detail View
// =============================================================================

interface TaskDetailViewProps {
  taskId: string
  onBack: () => void
}

function TaskDetailView({ taskId, onBack }: TaskDetailViewProps) {
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
      taskExecution.reset()
    }
  }, [taskExecution.isCompleted, taskExecution.isFailed, refetch, taskExecution])

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
            <ChevronLeft className="h-4 w-4" />
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
