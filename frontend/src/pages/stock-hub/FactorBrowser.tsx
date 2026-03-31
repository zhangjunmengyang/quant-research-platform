/**
 * Stock Hub - 因子库浏览页
 */

import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Search, Play, X, CheckCircle2, AlertCircle } from 'lucide-react'
import { useStockStatus, useStockFactors, useStockCategories } from '@/features/stock-hub'
import { stockApi } from '@/features/stock-hub/api'
import type { StockFactorListParams } from '@/features/stock-hub'

function NotConfigured() {
  const { t } = useTranslation()
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-4 text-muted-foreground">
      <p className="text-lg font-medium">{t('stockHub.notConfigured')}</p>
      <p className="text-sm">{t('stockHub.notConfiguredHint')}</p>
    </div>
  )
}

type BacktestTask = {
  factorName: string
  taskId: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  error?: string
}

function BacktestDialog({
  factorName,
  description,
  onSubmit,
  onClose,
}: {
  factorName: string
  description: string
  onSubmit: (startDate: string, endDate: string, factorConfig: string) => void
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [startDate, setStartDate] = useState('2020-01-01')
  const [endDate, setEndDate] = useState('')
  const [factorConfig, setFactorConfig] = useState(
    `("${factorName}", True, "", 1)`
  )

  // Default end date to today
  useEffect(() => {
    if (!endDate) {
      setEndDate(new Date().toISOString().slice(0, 10))
    }
  }, [endDate])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-lg border bg-background p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold">
            {t('stockHub.runBacktest')} - {factorName}
          </h3>
          <button onClick={onClose} className="rounded p-1 hover:bg-accent">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium">{t('stockHub.startDate')}</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">{t('stockHub.endDate')}</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">
              {t('stockHub.factorConfig', '因子配置')}
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                ({t('stockHub.factorConfigFormat', '因子名, 升序, 参数, 权重')})
              </span>
            </label>
            <textarea
              value={factorConfig}
              onChange={(e) => setFactorConfig(e.target.value)}
              rows={2}
              className="w-full rounded-md border bg-background px-3 py-2 font-mono text-sm"
            />
          </div>
          {description && (
            <div className="rounded-md bg-muted/50 p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">
                {t('stockHub.factorDescription', '因子说明')}
              </p>
              <pre className="whitespace-pre-wrap text-xs text-muted-foreground">{description}</pre>
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-md border px-4 py-2 text-sm hover:bg-accent"
          >
            {t('common.cancel')}
          </button>
          <button
            onClick={() => onSubmit(startDate, endDate, factorConfig)}
            disabled={!startDate || !endDate || !factorConfig.trim()}
            className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {t('stockHub.startBacktest')}
          </button>
        </div>
      </div>
    </div>
  )
}

export function Component() {
  const { t } = useTranslation()
  const { data: status, isLoading: statusLoading } = useStockStatus()
  const { data: categories } = useStockCategories()

  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)

  // Backtest state
  const [dialogFactor, setDialogFactor] = useState<{ name: string; description: string } | null>(null)
  const [tasks, setTasks] = useState<Record<string, BacktestTask>>({})
  const pollTimers = useRef<Record<string, ReturnType<typeof setInterval>>>({})

  const params: StockFactorListParams = useMemo(
    () => ({ page, page_size: 50, search: search || undefined, category: category || undefined }),
    [page, search, category]
  )

  const { data, isLoading } = useStockFactors(params)

  const pollTask = useCallback((taskId: string, factorName: string) => {
    const timer = setInterval(async () => {
      try {
        const st = await stockApi.getAnalysisTaskStatus(taskId)
        setTasks((prev) => {
          const cur = prev[factorName]
          if (!cur) return prev
          return { ...prev, [factorName]: { ...cur, status: st.status as BacktestTask['status'] } }
        })
        if (st.status === 'completed' || st.status === 'failed') {
          clearInterval(timer)
          delete pollTimers.current[factorName]
          if (st.status === 'failed') {
            setTasks((prev) => {
              const cur = prev[factorName]
              if (!cur) return prev
              return { ...prev, [factorName]: { ...cur, error: st.error_message || 'Failed' } }
            })
          }
        }
      } catch {
        clearInterval(timer)
        delete pollTimers.current[factorName]
      }
    }, 3000)
    pollTimers.current[factorName] = timer
  }, [])

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      Object.values(pollTimers.current).forEach(clearInterval)
    }
  }, [])

  const handleSubmitBacktest = useCallback(
    async (factorName: string, startDate: string, endDate: string, factorConfig: string) => {
      setDialogFactor(null)
      try {
        const resp = await stockApi.submitFactorBacktest(factorName, startDate, endDate, factorConfig)
        setTasks((prev) => ({
          ...prev,
          [factorName]: { factorName, taskId: resp.task_id, status: 'pending' },
        }))
        pollTask(resp.task_id, factorName)
      } catch (e) {
        setTasks((prev) => ({
          ...prev,
          [factorName]: {
            factorName,
            taskId: '',
            status: 'failed',
            error: e instanceof Error ? e.message : String(e),
          },
        }))
      }
    },
    [pollTask]
  )

  if (statusLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  if (!status?.available) {
    return <NotConfigured />
  }

  const factors = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 1

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('stockHub.factorBrowser')}</h1>
        <span className="text-sm text-muted-foreground">
          {t('stockHub.totalFactors', { count: total })}
        </span>
      </div>

      {/* 搜索和分类筛选 */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder={t('common.search')}
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="w-full rounded-md border bg-background pl-10 pr-4 py-2 text-sm"
          />
        </div>
        <select
          value={category}
          onChange={(e) => { setCategory(e.target.value); setPage(1) }}
          className="rounded-md border bg-background px-3 py-2 text-sm"
        >
          <option value="">{t('common.all')}</option>
          {categories && Object.entries(categories).map(([cat, count]) => (
            <option key={cat} value={cat}>{cat} ({count})</option>
          ))}
        </select>
      </div>

      {/* 因子列表 */}
      {isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      ) : factors.length === 0 ? (
        <div className="flex h-32 items-center justify-center text-muted-foreground">
          {t('stockHub.noFactors')}
        </div>
      ) : (
        <div className="grid gap-3">
          {factors.map((f) => {
            const task = tasks[f.name]
            const isRunning = task?.status === 'pending' || task?.status === 'running'

            return (
              <div
                key={f.name}
                className="rounded-lg border p-4 hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{f.name}</span>
                    <span className="rounded bg-muted px-2 py-0.5 text-xs">{f.category}</span>
                    {f.has_add_factor && (
                      <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400">
                        add_factor
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {task?.status === 'completed' && (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    )}
                    {task?.status === 'failed' && (
                      <span className="text-xs text-destructive" title={task.error}>
                        <AlertCircle className="h-4 w-4 inline" /> {t('stockHub.backtestFailed')}
                      </span>
                    )}
                    <button
                      onClick={() => setDialogFactor({ name: f.name, description: f.description })}
                      disabled={isRunning}
                      className="flex items-center gap-1 rounded-md border px-3 py-1.5 text-xs hover:bg-accent disabled:opacity-50"
                    >
                      {isRunning ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <Play className="h-3 w-3" />
                      )}
                      {isRunning ? t('stockHub.backtestRunning') : t('stockHub.runBacktest')}
                    </button>
                  </div>
                </div>
                {f.description && (
                  <p className="mt-1 text-sm text-muted-foreground line-clamp-2">{f.description}</p>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-md border px-3 py-1.5 text-sm disabled:opacity-50"
          >
            {t('common.previous')}
          </button>
          <span className="text-sm text-muted-foreground">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-md border px-3 py-1.5 text-sm disabled:opacity-50"
          >
            {t('common.next')}
          </button>
        </div>
      )}

      {/* 回测日期选择对话框 */}
      {dialogFactor && (
        <BacktestDialog
          factorName={dialogFactor.name}
          description={dialogFactor.description}
          onSubmit={(start, end, config) => handleSubmitBacktest(dialogFactor.name, start, end, config)}
          onClose={() => setDialogFactor(null)}
        />
      )}
    </div>
  )
}
