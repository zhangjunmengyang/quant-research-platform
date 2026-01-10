/**
 * Backtest Task Management Page
 * 回测任务管理页 - 任务列表、创建、执行和历史记录管理
 *
 * 核心概念:
 * - BacktestTask: 任务单（配置模板），可被多次执行
 * - TaskExecution: 执行记录，每次执行的状态和结果
 */

import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { TaskListView } from './TaskListView'
import { TaskCreateView } from './TaskCreateView'
import { TaskDetailView } from './TaskDetailView'

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
