/**
 * Stock Hub - 因子库浏览页
 */

import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Search, RefreshCw } from 'lucide-react'
import { useStockStatus, useStockFactors, useStockCategories } from '@/features/stock-hub'
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

export function Component() {
  const { t } = useTranslation()
  const { data: status, isLoading: statusLoading } = useStockStatus()
  const { data: categories } = useStockCategories()

  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)

  const params: StockFactorListParams = useMemo(
    () => ({ page, page_size: 50, search: search || undefined, category: category || undefined }),
    [page, search, category]
  )

  const { data, isLoading } = useStockFactors(params)

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
          {factors.map((f) => (
            <div
              key={f.name}
              className="rounded-lg border p-4 hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{f.name}</span>
                  <span className="rounded bg-muted px-2 py-0.5 text-xs">{f.category}</span>
                </div>
                {f.has_add_factor && (
                  <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400">
                    add_factor
                  </span>
                )}
              </div>
              {f.description && (
                <p className="mt-1 text-sm text-muted-foreground line-clamp-2">{f.description}</p>
              )}
            </div>
          ))}
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
    </div>
  )
}
