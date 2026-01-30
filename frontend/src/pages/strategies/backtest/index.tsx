/**
 * Backtest Task Management Page
 * 回测任务管理页 - 任务列表、创建、执行和历史记录管理
 *
 * 核心概念:
 * - BacktestTask: 任务单（配置模板），可被多次执行
 * - TaskExecution: 执行记录，每次执行的状态和结果
 */

import { useCallback } from 'react'
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom'
import { TaskListView } from './TaskListView'
import { TaskCreateView } from './TaskCreateView'
import { TaskDetailView } from './TaskDetailView'

type ViewMode = 'list' | 'create' | 'detail'

export function Component() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const viewMode = (searchParams.get('view') as ViewMode) || 'list'
  const detailId = searchParams.get('id')

  const setViewMode = useCallback(
    (mode: ViewMode, id?: string, options?: { replace?: boolean }) => {
      const params = new URLSearchParams()
      params.set('view', mode)
      if (id) params.set('id', id)
      setSearchParams(params, { replace: options?.replace })
    },
    [setSearchParams]
  )

  // 安全的后退函数：如果没有历史记录则返回列表视图
  const handleBack = useCallback(() => {
    if (location.key === 'default') {
      // 直接访问或刷新页面，返回到列表视图
      setViewMode('list', undefined, { replace: true })
    } else {
      navigate(-1)
    }
  }, [navigate, location.key, setViewMode])

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
          onBack={handleBack}
          onCreated={(id) => setViewMode('detail', id, { replace: true })}
        />
      )}
      {viewMode === 'detail' && detailId && (
        <TaskDetailView taskId={detailId} onBack={handleBack} />
      )}
    </div>
  )
}
