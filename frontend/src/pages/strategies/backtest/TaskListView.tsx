/**
 * Task List View Component
 * 任务列表视图组件
 */

import { useState } from 'react'
import {
  Loader2,
  Plus,
  Trash2,
  RefreshCw,
  Copy,
  History,
  ListTodo,
  ArrowUpRight,
} from 'lucide-react'
import { useTasks, useTaskMutations } from '@/features/strategy'
import { StatsCard } from '@/features/factor/components/StatsCard'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import type { BacktestTask } from '@/features/strategy'
import { formatDateTime, parseJSON, formatFactorListFromConfig } from './utils'
import type { TaskConfig } from '@/features/strategy'

export interface TaskListViewProps {
  onViewDetail: (id: string) => void
  onCreateNew: () => void
}

export function TaskListView({ onViewDetail, onCreateNew }: TaskListViewProps) {
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
              <span className="px-3 text-sm">
                {data.page} / {data.total_pages}
              </span>
              <button
                onClick={() => setPage(data.page + 1)}
                disabled={data.page >= data.total_pages}
                className="rounded-md border p-2 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-accent"
              >
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
                    d="M9 5l7 7-7 7"
                  />
                </svg>
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
