/**
 * Strategy Browser Page
 * 策略浏览页 - 展示策略列表和统计
 */

import { useState } from 'react'
import { Loader2, TrendingUp, CheckCircle, Plus, ChevronLeft, ChevronRight, Trash2 } from 'lucide-react'
import { useStrategies, useStrategyStats, useStrategyStore, useStrategyMutations } from '@/features/strategy'
import { StatsCard } from '@/features/factor/components/StatsCard'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { cn, formatPercent } from '@/lib/utils'
import { Link } from 'react-router-dom'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'
import type { Strategy } from '@/features/strategy'

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

  return factorList.map(name => {
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


export function Component() {
  const { filters, setFilters } = useStrategyStore()
  const { data: stats, isLoading: statsLoading } = useStrategyStats()
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
          valueColor={stats?.avg_sharpe && stats.avg_sharpe > 1 ? 'success' : stats?.avg_sharpe && stats.avg_sharpe > 0 ? 'warning' : 'default'}
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
        <StrategyTable
          strategies={data?.items || []}
          onDelete={handleDeleteClick}
          isDeleting={deleteStrategy.isPending}
          deletingId={strategyToDelete?.id}
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
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            显示 {(data.page - 1) * data.page_size + 1}-
            {Math.min(data.page * data.page_size, data.total)} / 共 {data.total} 条
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilters({ page: data.page - 1 })}
              disabled={data.page <= 1}
              className="rounded-md border p-2 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-accent"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="px-3 text-sm">
              {data.page} / {data.total_pages}
            </span>
            <button
              onClick={() => setFilters({ page: data.page + 1 })}
              disabled={data.page >= data.total_pages}
              className="rounded-md border p-2 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-accent"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

interface StrategyTableProps {
  strategies: Strategy[]
  onDelete: (strategy: Strategy) => void
  isDeleting: boolean
  deletingId?: string
}

function StrategyTable({ strategies, onDelete, isDeleting, deletingId }: StrategyTableProps) {
  if (strategies.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center rounded-lg border text-muted-foreground">
        暂无策略
      </div>
    )
  }

  return (
    <div className="rounded-lg border overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-3 py-3 text-left text-sm font-medium whitespace-nowrap">策略名称</th>
            <th className="px-3 py-3 text-left text-sm font-medium whitespace-nowrap">因子(参数)</th>
            <th className="px-3 py-3 text-center text-sm font-medium whitespace-nowrap text-success">多</th>
            <th className="px-3 py-3 text-center text-sm font-medium whitespace-nowrap text-destructive">空</th>
            <th className="px-3 py-3 text-center text-sm font-medium whitespace-nowrap">净值</th>
            <th className="px-3 py-3 text-center text-sm font-medium whitespace-nowrap">年化收益</th>
            <th className="px-3 py-3 text-center text-sm font-medium whitespace-nowrap">最大回撤</th>
            <th className="px-3 py-3 text-center text-sm font-medium whitespace-nowrap">收益回撤比</th>
            <th className="px-3 py-3 text-center text-sm font-medium whitespace-nowrap">回测区间</th>
            <th className="px-3 py-3 text-center text-sm font-medium whitespace-nowrap">创建时间</th>
            <th className="px-3 py-3 text-center text-sm font-medium w-16">操作</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {strategies.map((strategy) => {
            const factorDisplay = formatFactorWithParams(strategy)
            return (
              <tr key={strategy.id} className="hover:bg-muted/50 transition-colors">
                <td className="px-3 py-3">
                  <Link
                    to={`/strategies/${strategy.id}`}
                    className="font-medium hover:text-primary"
                  >
                    {strategy.name}
                  </Link>
                  {strategy.description && (
                    <p className="mt-1 text-xs text-muted-foreground line-clamp-1">
                      {strategy.description}
                    </p>
                  )}
                </td>
                <td className="px-3 py-3 max-w-[250px]">
                  <p
                    className="text-sm text-muted-foreground line-clamp-1 font-mono"
                    title={factorDisplay}
                  >
                    {factorDisplay}
                  </p>
                </td>
                <td className="px-3 py-3 text-center">
                  <span className="text-sm font-medium text-success">
                    {strategy.long_select_coin_num ?? strategy.select_coin_num}
                  </span>
                </td>
                <td className="px-3 py-3 text-center">
                  <span className="text-sm font-medium text-destructive">
                    {strategy.short_select_coin_num ?? 0}
                  </span>
                </td>
                <td className="px-3 py-3 text-center">
                  <span
                    className={cn(
                      'font-medium',
                      strategy.cumulative_return && strategy.cumulative_return >= 1
                        ? 'text-success'
                        : 'text-destructive'
                    )}
                  >
                    {strategy.cumulative_return?.toFixed(2) ?? '-'}
                  </span>
                </td>
                <td className="px-3 py-3 text-center">
                  <span
                    className={cn(
                      'font-medium',
                      strategy.annual_return && strategy.annual_return > 0
                        ? 'text-success'
                        : 'text-destructive'
                    )}
                  >
                    {formatPercent(strategy.annual_return)}
                  </span>
                </td>
                <td className="px-3 py-3 text-center">
                  <span className="text-destructive font-medium">
                    {formatPercent(strategy.max_drawdown)}
                  </span>
                </td>
                <td className="px-3 py-3 text-center">
                  <span
                    className={cn(
                      'font-medium',
                      strategy.sharpe_ratio && strategy.sharpe_ratio > 0
                        ? 'text-success'
                        : 'text-destructive'
                    )}
                  >
                    {strategy.sharpe_ratio?.toFixed(2) ?? '-'}
                  </span>
                </td>
                <td className="px-3 py-3 text-center">
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {strategy.start_date && strategy.end_date
                      ? `${strategy.start_date} ~ ${strategy.end_date}`
                      : '-'}
                  </span>
                </td>
                <td className="px-3 py-3 text-center">
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {formatDate(strategy.created_at)}
                  </span>
                </td>
                <td className="px-3 py-3 text-center">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      onDelete(strategy)
                    }}
                    disabled={isDeleting && deletingId === strategy.id}
                    className="inline-flex items-center justify-center rounded-md p-2 text-muted-foreground hover:bg-red-50 hover:text-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    title="删除策略"
                  >
                    {isDeleting && deletingId === strategy.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
