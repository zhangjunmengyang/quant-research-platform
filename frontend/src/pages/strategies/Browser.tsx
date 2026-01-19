/**
 * Strategy Browser Page
 * 策略浏览页 - 展示策略列表和统计
 */

import { useState, useMemo, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Loader2, TrendingUp, CheckCircle, Plus, Trash2 } from 'lucide-react'
import { useStrategies, useStrategyStats, useStrategyMutations } from '@/features/strategy'
import type { Strategy, StrategyListParams } from '@/features/strategy'
import { StatsCard } from '@/features/factor/components/StatsCard'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Pagination } from '@/components/ui/pagination'
import { ResizableTable } from '@/components/ui/ResizableTable'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'
import { paramsToStrategyFilters, strategyFiltersToParams } from '@/lib/url-params'
import { cn, formatPercent } from '@/lib/utils'
import { Link } from 'react-router-dom'

// 验证状态选项
const VERIFIED_OPTIONS: SelectOption[] = [
  { value: '', label: '全部状态' },
  { value: 'true', label: '已验证' },
  { value: 'false', label: '未验证' },
]

/**
 * 解析 JSON 字符串
 */
function parseJSON<T>(json: string | undefined | null, defaultValue: T): T {
  if (!json) return defaultValue
  try {
    return JSON.parse(json) as T
  } catch {
    return defaultValue
  }
}

/**
 * 格式化因子显示（包含参数和排序方向）
 */
function formatFactorWithParams(strategy: Strategy): string {
  const factorList = parseJSON<string[]>(strategy.factor_list, [])
  const factorParams = parseJSON<Record<string, unknown>>(strategy.factor_params, {})
  const sortDirections = parseJSON<Record<string, boolean>>(strategy.sort_directions, {})

  if (factorList.length === 0) return '-'

  return factorList.map((name) => {
    const param = factorParams[name]
    const isAsc = sortDirections[name]
    const direction = isAsc !== undefined ? (isAsc ? '\u2191' : '\u2193') : ''
    const paramStr = param !== undefined ? `(${Array.isArray(param) ? param.join(',') : param})` : ''
    return `${name}${paramStr}${direction}`
  }).join(', ')
}

/**
 * 格式化日期，仅显示日期部分
 */
function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return '-'
  // 处理 ISO 格式或简单日期格式
  const date = dateStr.split('T')[0]
  return date || '-'
}

/**
 * 策略表格列定义
 */
function getStrategyColumns(onDelete: (strategy: Strategy) => void, isDeleting: boolean, deletingId?: string) {
  return [
    {
      key: 'name',
      label: '策略名称',
      width: 180,
      minWidth: 120,
      render: (_: unknown, row: Strategy) => (
        <div className="max-w-[180px]">
          <Link
            to={`/strategies/${row.id}`}
            className="font-medium hover:text-primary block truncate"
          >
            {row.name}
          </Link>
          {row.description && (
            <p className="mt-1 text-xs text-muted-foreground line-clamp-1">
              {row.description}
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'factor_list',
      label: '因子(参数)',
      width: 250,
      minWidth: 150,
      render: (_: unknown, row: Strategy) => {
        const factorDisplay = formatFactorWithParams(row)
        return (
          <p
            className="text-sm text-muted-foreground line-clamp-1 font-mono"
            title={factorDisplay}
          >
            {factorDisplay}
          </p>
        )
      },
    },
    {
      key: 'long_select_coin_num',
      label: '多',
      width: 60,
      minWidth: 50,
      align: 'center' as const,
      render: (_: unknown, row: Strategy) => (
        <span className="text-sm font-medium text-success">
          {row.long_select_coin_num ?? row.select_coin_num}
        </span>
      ),
    },
    {
      key: 'short_select_coin_num',
      label: '空',
      width: 60,
      minWidth: 50,
      align: 'center' as const,
      render: (_: unknown, row: Strategy) => (
        <span className="text-sm font-medium text-destructive">
          {row.short_select_coin_num ?? 0}
        </span>
      ),
    },
    {
      key: 'cumulative_return',
      label: '净值',
      width: 80,
      minWidth: 70,
      align: 'center' as const,
      render: (value: unknown) => (
        <span
          className={cn(
            'font-medium',
            value && (value as number) >= 1 ? 'text-success' : 'text-destructive'
          )}
        >
          {value ? Number(value).toFixed(2) : '-'}
        </span>
      ),
    },
    {
      key: 'annual_return',
      label: '年化收益',
      width: 90,
      minWidth: 80,
      align: 'center' as const,
      render: (value: unknown) => (
        <span
          className={cn(
            'font-medium',
            value && (value as number) > 0 ? 'text-success' : 'text-destructive'
          )}
        >
          {formatPercent(value as number | undefined)}
        </span>
      ),
    },
    {
      key: 'max_drawdown',
      label: '最大回撤',
      width: 90,
      minWidth: 80,
      align: 'center' as const,
      render: (value: unknown) => (
        <span className="text-destructive font-medium">
          {formatPercent(value as number | undefined)}
        </span>
      ),
    },
    {
      key: 'sharpe_ratio',
      label: '收益回撤比',
      width: 90,
      minWidth: 80,
      align: 'center' as const,
      render: (value: unknown) => (
        <span
          className={cn(
            'font-medium',
            value && (value as number) > 0 ? 'text-success' : 'text-destructive'
          )}
        >
          {value ? Number(value).toFixed(2) : '-'}
        </span>
      ),
    },
    {
      key: 'backtest_range',
      label: '回测区间',
      width: 160,
      minWidth: 120,
      align: 'center' as const,
      render: (_: unknown, row: Strategy) => (
        <span className="text-xs text-muted-foreground whitespace-nowrap">
          {row.start_date && row.end_date
            ? `${row.start_date} ~ ${row.end_date}`
            : '-'}
        </span>
      ),
    },
    {
      key: 'created_at',
      label: '创建时间',
      width: 100,
      minWidth: 80,
      align: 'center' as const,
      render: (value: unknown) => (
        <span className="text-xs text-muted-foreground whitespace-nowrap">
          {formatDate(value as string)}
        </span>
      ),
    },
    {
      key: 'actions',
      label: '操作',
      width: 60,
      minWidth: 60,
      align: 'center' as const,
      render: (_: unknown, row: Strategy) => (
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            onDelete(row)
          }}
          disabled={isDeleting && deletingId === row.id}
          className="inline-flex items-center justify-center rounded-md p-2 text-muted-foreground hover:bg-red-50 hover:text-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="删除策略"
        >
          {isDeleting && deletingId === row.id ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Trash2 className="h-4 w-4" />
          )}
        </button>
      ),
    },
  ]
}

export function Component() {
  const [searchParams, setSearchParams] = useSearchParams()

  // 从 URL 读取 filters
  const filters = useMemo(() => paramsToStrategyFilters(searchParams), [searchParams])

  // 更新 filters 并同步到 URL
  const setFilters = useCallback((newFilters: Partial<StrategyListParams>) => {
    const updatedFilters = { ...filters, ...newFilters }
    const params = strategyFiltersToParams(updatedFilters)
    // 移除空值参数
    Object.keys(params).forEach((key) => {
      if (params[key] === '' || params[key] === 'undefined') {
        delete params[key]
      }
    })
    setSearchParams(params)
  }, [filters, setSearchParams])

  const { data: stats } = useStrategyStats()
  const { data, isLoading, isError, error } = useStrategies(filters)
  const { deleteStrategy } = useStrategyMutations()

  // 删除确认对话框状态
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [strategyToDelete, setStrategyToDelete] = useState<Strategy | null>(null)

  const handleDeleteClick = (strategy: Strategy) => {
    setStrategyToDelete(strategy)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = () => {
    if (strategyToDelete) {
      deleteStrategy.mutate(strategyToDelete.id, {
        onSuccess: () => {
          setDeleteDialogOpen(false)
          setStrategyToDelete(null)
        },
      })
    }
  }

  // 动态生成列配置
  const columns = useMemo(
    () => getStrategyColumns(handleDeleteClick, deleteStrategy.isPending, strategyToDelete?.id),
    [handleDeleteClick, deleteStrategy.isPending, strategyToDelete?.id]
  )

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <p className="text-destructive">加载失败: {(error as Error)?.message}</p>
        <button
          onClick={() => window.location.reload()}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground"
        >
          重试
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="策略总数"
          value={stats?.total ?? 0}
          icon={<TrendingUp className="h-5 w-5" />}
        />
        <StatsCard
          title="已验证"
          value={stats?.verified ?? 0}
          icon={<CheckCircle className="h-5 w-5" />}
          valueColor="success"
        />
        <StatsCard
          title="平均夏普"
          value={stats?.avg_sharpe?.toFixed(2) ?? '-'}
          icon={<TrendingUp className="h-5 w-5" />}
          valueColor={
            stats?.avg_sharpe && stats.avg_sharpe > 1
              ? 'success'
              : stats?.avg_sharpe && stats.avg_sharpe > 0
                ? 'warning'
                : 'default'
          }
        />
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <SearchableSelect
            options={VERIFIED_OPTIONS}
            value={filters.verified === undefined ? '' : String(filters.verified)}
            onChange={(value) =>
              setFilters({
                verified: value === '' ? undefined : value === 'true',
                page: 1,
              })
            }
            className="w-32"
          />
        </div>
        <Link
          to="/strategies/backtest"
          className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          新建回测
        </Link>
      </div>

      {/* Strategy List */}
      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <ResizableTable
          columns={columns}
          data={data?.items || []}
          rowKey="id"
          emptyText="暂无策略"
        />
      )}

      {/* 删除确认对话框 */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="删除策略"
        description={`确定要删除策略"${strategyToDelete?.name}"吗？此操作不可撤销。`}
        confirmText="删除"
        cancelText="取消"
        onConfirm={handleDeleteConfirm}
        isLoading={deleteStrategy.isPending}
        variant="danger"
      />

      {/* Pagination */}
      {data && data.total > 0 && (
        <Pagination
          page={data.page}
          pageSize={data.page_size}
          total={data.total}
          totalPages={data.total_pages}
          onPageChange={(page) => setFilters({ page })}
          variant="range"
          position="between"
        />
      )}
    </div>
  )
}
