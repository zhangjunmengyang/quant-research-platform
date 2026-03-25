/**
 * A股因子浏览器 — 千因子库浏览、搜索、详情查看、加入回测
 */

import { useState, useMemo, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { RefreshCw, Search, Code2, X, Check, Plus } from 'lucide-react'

import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Pagination } from '@/components/ui/pagination'
import { ResizableTable, type TableColumn, type SortState } from '@/components/ui/ResizableTable'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

import {
  useStockFactors,
  useStockCategories,
  useStockFactor,
  useRefreshStockFactors,
  useStockHubStore,
  useStockHubStatus,
  useStockEvaluation,
} from '@/features/stock-hub'
import type { StockFactorMeta, StockFactorListParams } from '@/features/stock-hub'
import { StockHubNotConfigured } from './StockHubNotConfigured'

// ===== 分类统计卡片 =====

function CategoryCards({ categories }: { categories: Record<string, number> | undefined }) {
  const { t } = useTranslation()
  if (!categories) return null

  const total = Object.values(categories).reduce((a, b) => a + b, 0)
  const items = [
    { label: t('common.all'), count: total, color: 'bg-primary' },
    ...Object.entries(categories).map(([cat, count]) => ({
      label: cat,
      count,
      color:
        cat === 'H财务'
          ? 'bg-blue-500'
          : cat === '截面'
            ? 'bg-emerald-500'
            : 'bg-amber-500',
    })),
  ]

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {items.map((item) => (
        <Card key={item.label}>
          <CardContent className="flex items-center gap-3 p-4">
            <div className={`h-2 w-2 rounded-full ${item.color}`} />
            <div>
              <p className="text-sm text-muted-foreground">{item.label}</p>
              <p className="text-xl font-bold">{item.count}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// ===== 因子详情弹窗 =====

function FactorDetailDialog({
  factorName,
  open,
  onClose,
}: {
  factorName: string
  open: boolean
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [showCode, setShowCode] = useState(false)
  const { data: factor, isLoading } = useStockFactor(factorName, showCode)
  const { data: evaluation } = useStockEvaluation(factorName, open)
  const { addPendingFactor } = useStockHubStore()
  const [addedToast, setAddedToast] = useState(false)

  const handleAddToBacktest = () => {
    addPendingFactor(factorName)
    setAddedToast(true)
    setTimeout(() => setAddedToast(false), 2000)
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {factorName}
            {factor && (
              <Badge variant={factor.category === '截面' ? 'info' : 'secondary'}>
                {factor.category}
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center gap-2 py-8 justify-center text-muted-foreground">
            <RefreshCw className="h-4 w-4 animate-spin" />
            {t('common.loading')}
          </div>
        ) : factor ? (
          <div className="space-y-4">
            {/* 操作按钮 */}
            <div className="flex gap-2">
              <Button size="sm" onClick={handleAddToBacktest} className="gap-1">
                <Plus className="h-3.5 w-3.5" />
                {t('stockHub.addToBacktest')}
              </Button>
              {addedToast && (
                <Badge variant="success">{t('stockHub.addedToBacktest')}</Badge>
              )}
              {evaluation && evaluation.overall_score !== null && (
                <Badge
                  variant={
                    evaluation.overall_score >= 4.0
                      ? 'success'
                      : evaluation.overall_score >= 3.0
                        ? 'info'
                        : evaluation.overall_score >= 2.0
                          ? 'warning'
                          : 'destructive'
                  }
                  title={`${t('stockHub.overallScore')}: ${evaluation.overall_score.toFixed(1)} — ${evaluation.verdict}`}
                >
                  AI {evaluation.overall_score.toFixed(1)}
                </Badge>
              )}
            </div>

            {/* 基本信息 */}
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-muted-foreground">{t('stockHub.library')}:</span>{' '}
                {factor.library}
              </div>
              <div>
                <span className="text-muted-foreground">{t('stockHub.hasAddFactor')}:</span>{' '}
                {factor.has_add_factor ? (
                  <Check className="inline h-4 w-4 text-green-500" />
                ) : (
                  <X className="inline h-4 w-4 text-muted-foreground" />
                )}
              </div>
            </div>

            {/* 描述 */}
            {factor.description && (
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  {t('stockHub.description')}
                </p>
                <p className="text-sm">{factor.description}</p>
              </div>
            )}

            {/* 数据列 */}
            {factor.fin_cols.length > 0 && (
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  {t('stockHub.finCols')}
                </p>
                <div className="flex flex-wrap gap-1">
                  {factor.fin_cols.map((col) => (
                    <Badge key={col} variant="outline" className="text-xs">
                      {col}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {factor.ov_cols.length > 0 && (
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  {t('stockHub.ovCols')}
                </p>
                <div className="flex flex-wrap gap-1">
                  {factor.ov_cols.map((col) => (
                    <Badge key={col} variant="outline" className="text-xs">
                      {col}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* 示例 */}
            {factor.example_select && (
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  {t('stockHub.selectExample')}
                </p>
                <pre className="rounded bg-muted p-2 text-xs overflow-x-auto">
                  {factor.example_select}
                </pre>
              </div>
            )}

            {factor.example_filter && (
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">
                  {t('stockHub.filterExample')}
                </p>
                <pre className="rounded bg-muted p-2 text-xs overflow-x-auto">
                  {factor.example_filter}
                </pre>
              </div>
            )}

            {/* 源码 */}
            <div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowCode(!showCode)}
                className="gap-1"
              >
                <Code2 className="h-3.5 w-3.5" />
                {t('stockHub.viewCode')}
              </Button>
              {showCode && factor.code && (
                <pre className="mt-2 max-h-96 overflow-auto rounded bg-muted p-3 text-xs">
                  {factor.code}
                </pre>
              )}
            </div>
          </div>
        ) : (
          <p className="text-destructive">{t('common.error')}</p>
        )}
      </DialogContent>
    </Dialog>
  )
}

// ===== 主页面 =====

export function Component() {
  const { t } = useTranslation()
  const { data: status } = useStockHubStatus()
  const [searchParams, setSearchParams] = useSearchParams()
  const {
    openDetailPanel,
    selectedFactor,
    detailPanelOpen,
    closeDetailPanel,
    addPendingFactor,
    pendingFactors,
  } = useStockHubStore()

  // 从 URL 解析筛选参数
  const params = useMemo<StockFactorListParams>(
    () => ({
      search: searchParams.get('search') || undefined,
      category: searchParams.get('category') || undefined,
      page: Number(searchParams.get('page')) || 1,
      page_size: Number(searchParams.get('page_size')) || 50,
    }),
    [searchParams]
  )

  const setParams = useCallback(
    (updates: Partial<StockFactorListParams>) => {
      const next = { ...params, ...updates }
      const sp = new URLSearchParams()
      if (next.search) sp.set('search', next.search)
      if (next.category) sp.set('category', next.category)
      if (next.page && next.page > 1) sp.set('page', String(next.page))
      if (next.page_size && next.page_size !== 50) sp.set('page_size', String(next.page_size))
      setSearchParams(sp)
    },
    [params, setSearchParams]
  )

  // 查询
  const { data, isLoading } = useStockFactors(params)
  const { data: categories } = useStockCategories()
  const refreshMutation = useRefreshStockFactors()

  // 搜索
  const [searchInput, setSearchInput] = useState(params.search || '')
  const handleSearch = () => {
    setParams({ search: searchInput || undefined, page: 1 })
  }

  // "加入回测"快捷操作的 toast
  const [addToast, setAddToast] = useState('')

  const handleQuickAdd = (name: string, e: React.MouseEvent) => {
    e.stopPropagation()
    addPendingFactor(name)
    setAddToast(name)
    setTimeout(() => setAddToast(''), 1500)
  }

  // 表格列
  const columns = useMemo<TableColumn<StockFactorMeta>[]>(
    () => [
      {
        key: 'name',
        label: t('stockHub.factorName'),
        width: 200,
        sortable: true,
        render: (_, row) => (
          <button
            type="button"
            className="text-left font-medium text-primary hover:underline"
            onClick={(e) => {
              e.stopPropagation()
              openDetailPanel(row)
            }}
          >
            {row.name}
          </button>
        ),
      },
      {
        key: 'category',
        label: t('stockHub.category'),
        width: 80,
        sortable: true,
        render: (_, row) => (
          <Badge
            variant={
              row.category === '截面'
                ? 'info'
                : row.category === 'H财务'
                  ? 'default'
                  : 'warning'
            }
          >
            {row.category}
          </Badge>
        ),
      },
      {
        key: 'has_add_factor',
        label: t('stockHub.hasAddFactor'),
        width: 90,
        align: 'center' as const,
        render: (_, row) =>
          row.has_add_factor ? (
            <Check className="mx-auto h-4 w-4 text-green-500" />
          ) : (
            <X className="mx-auto h-4 w-4 text-muted-foreground/30" />
          ),
      },
      {
        key: 'description',
        label: t('stockHub.description'),
        width: 300,
        render: (_, row) => (
          <span className="line-clamp-1 text-muted-foreground">{row.description || '-'}</span>
        ),
      },
      {
        key: 'fin_cols',
        label: t('stockHub.finCols'),
        width: 150,
        render: (_, row) => (
          <span className="text-xs text-muted-foreground">
            {row.fin_cols.length > 0 ? row.fin_cols.join(', ') : '-'}
          </span>
        ),
      },
      {
        key: '_actions',
        label: t('stockHub.addToBacktest'),
        width: 90,
        align: 'center' as const,
        render: (_, row) => {
          const alreadyAdded = pendingFactors.some((f) => f.name === row.name)
          return (
            <Button
              variant={alreadyAdded ? 'secondary' : 'outline'}
              size="icon-sm"
              onClick={(e: React.MouseEvent) => handleQuickAdd(row.name, e)}
              title={t('stockHub.addToBacktest')}
              disabled={alreadyAdded}
            >
              {alreadyAdded ? <Check className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
            </Button>
          )
        },
      },
    ],
    [t, openDetailPanel, pendingFactors, handleQuickAdd]
  )

  // 排序
  const [sortState, setSortState] = useState<SortState>({ field: 'name', order: 'asc' })

  const sortedFactors = useMemo(() => {
    if (!data?.factors) return []
    const factors = [...data.factors]
    const { field, order } = sortState
    factors.sort((a, b) => {
      const va = (a as unknown as Record<string, unknown>)[field]
      const vb = (b as unknown as Record<string, unknown>)[field]
      if (va == null && vb == null) return 0
      if (va == null) return 1
      if (vb == null) return -1
      const cmp = String(va).localeCompare(String(vb), 'zh-CN')
      return order === 'asc' ? cmp : -cmp
    })
    return factors
  }, [data?.factors, sortState])

  if (status && !status.available) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{t('stockHub.factorBrowser')}</h1>
        <StockHubNotConfigured status={status} />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('stockHub.factorBrowser')}</h1>
          {data && (
            <p className="text-sm text-muted-foreground">
              {t('stockHub.totalFactors', { count: data.total })}
              {pendingFactors.length > 0 && (
                <span className="ml-2 text-primary">
                  ({pendingFactors.length} {t('stockHub.addedToBacktest')})
                </span>
              )}
            </p>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refreshMutation.mutate()}
          loading={refreshMutation.isPending}
          className="gap-1"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          {t('stockHub.refreshCache')}
        </Button>
      </div>

      {/* 添加成功提示 */}
      {addToast && (
        <div className="rounded-md bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 px-3 py-2 text-sm text-green-700 dark:text-green-300">
          <Check className="inline h-4 w-4 mr-1" />
          {addToast} — {t('stockHub.addedToBacktest')}
        </div>
      )}

      {/* 分类统计 */}
      <CategoryCards categories={categories} />

      {/* 搜索 + 分类筛选 */}
      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 p-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder={t('common.search')}
              className="h-9 w-full rounded-md border border-input bg-background pl-9 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
          <div className="flex gap-1">
            {[undefined, 'H财务', '技术', '截面'].map((cat) => (
              <Button
                key={cat ?? 'all'}
                variant={params.category === cat ? 'default' : 'outline'}
                size="sm"
                onClick={() => setParams({ category: cat, page: 1 })}
              >
                {cat ?? t('common.all')}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 因子表格 */}
      <Card>
        <CardContent className="p-0">
          <ResizableTable<StockFactorMeta>
            columns={columns}
            data={sortedFactors}
            rowKey="name"
            onRowClick={openDetailPanel}
            stickyHeader
            maxHeight="calc(100vh - 380px)"
            emptyText={isLoading ? t('common.loading') : t('factor.noData')}
            sortState={sortState}
            onSortChange={setSortState}
          />
        </CardContent>
      </Card>

      {/* 分页 */}
      {data && data.total > 0 && (
        <Pagination
          page={params.page ?? 1}
          pageSize={params.page_size ?? 50}
          total={data.total}
          onPageChange={(page) => setParams({ page })}
          onPageSizeChange={(page_size) => setParams({ page_size, page: 1 })}
          position="between"
        />
      )}

      {/* 详情弹窗 */}
      {selectedFactor && (
        <FactorDetailDialog
          factorName={selectedFactor.name}
          open={detailPanelOpen}
          onClose={closeDetailPanel}
        />
      )}
    </div>
  )
}
