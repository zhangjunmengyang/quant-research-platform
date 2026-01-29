/**
 * Strategy Detail Page
 * 策略详情页 - 展示完整的回测指标
 */

import { useParams, Link } from 'react-router-dom'
import {
  Loader2,
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Calendar,
  Settings,
  CheckCircle,
  BarChart3,
} from 'lucide-react'
import { useStrategy } from '@/features/strategy'
import { EquityCurveSubplots, type EquityCurveDataPoint } from '@/components/charts'
import { EntityGraph } from '@/features/graph'
import { cn, formatPercent } from '@/lib/utils'
import type { Strategy } from '@/features/strategy'

// 周期收益数据类型
interface PeriodReturn {
  candle_begin_time: string
  涨跌幅?: string
  [key: string]: unknown
}

// 指标名称映射
const METRIC_LABELS: Record<string, string> = {
  cumulative_return: '累积净值',
  annual_return: '年化收益',
  max_drawdown: '最大回撤',
  sharpe_ratio: '年化收益/回撤比',
  win_rate: '胜率',
  profit_loss_ratio: '盈亏收益比',
  win_periods: '盈利周期数',
  loss_periods: '亏损周期数',
  avg_return_per_period: '每周期平均收益',
  return_std: '收益率标准差',
  max_single_profit: '单周期最大盈利',
  max_single_loss: '单周期最大亏损',
  max_consecutive_wins: '最大连续盈利周期数',
  max_consecutive_losses: '最大连续亏损周期数',
  max_drawdown_start: '最大回撤开始时间',
  max_drawdown_end: '最大回撤结束时间',
  recovery_rate: '修复涨幅',
  recovery_time: '修复时间',
}

// 核心指标
const CORE_METRICS = [
  'cumulative_return',
  'annual_return',
  'max_drawdown',
  'sharpe_ratio',
]

// 交易统计指标
const TRADING_METRICS = [
  'win_rate',
  'profit_loss_ratio',
  'win_periods',
  'loss_periods',
  'avg_return_per_period',
  'return_std',
]

// 极值统计指标
const EXTREME_METRICS = [
  'max_single_profit',
  'max_single_loss',
  'max_consecutive_wins',
  'max_consecutive_losses',
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
 * 格式化指标值
 */
function formatMetricValue(key: string, value: unknown): string {
  if (value === undefined || value === null) return '-'

  if (typeof value === 'number') {
    // 累积净值：保留2位小数
    if (key === 'cumulative_return') {
      return value.toFixed(2)
    }
    // 整数类型：周期数、连续次数
    if (key.includes('periods') || key.includes('wins') || key.includes('losses')) {
      return value.toFixed(0)
    }
    // 百分比类型：收益率、回撤、胜率等
    if (key.includes('rate') || key.includes('return') || key.includes('drawdown') || key.includes('std')) {
      return formatPercent(value)
    }
    // 单周期盈亏也是百分比
    if (key === 'max_single_profit' || key === 'max_single_loss') {
      return formatPercent(value)
    }
    return value.toFixed(2)
  }

  return String(value)
}

/**
 * 获取指标颜色
 */
function getMetricColor(key: string, value: unknown): string | undefined {
  if (typeof value !== 'number') return undefined

  if (key === 'cumulative_return') {
    return value >= 1 ? 'text-green-600' : 'text-red-600'
  }
  if (key === 'annual_return' || key === 'sharpe_ratio' || key === 'avg_return_per_period') {
    return value >= 0 ? 'text-green-600' : 'text-red-600'
  }
  if (key === 'max_drawdown' || key === 'max_single_loss') {
    return 'text-red-600'
  }
  if (key === 'max_single_profit') {
    return 'text-green-600'
  }
  return undefined
}

/**
 * 解析涨跌幅字符串为数值
 */
function parseReturnValue(value: string | null | undefined): number | null {
  if (!value) return null
  // 处理 "15.23%" 格式
  const match = value.match(/^(-?[\d.]+)%$/)
  if (match?.[1]) {
    return parseFloat(match[1]) / 100
  }
  return null
}

/**
 * 获取收益热力图背景色
 * 正收益：绿色系，负收益：红色系
 */
function getReturnBgColor(value: number | null): string {
  if (value === null) return ''

  // 根据收益幅度计算颜色深度
  const absValue = Math.abs(value)

  if (value >= 0) {
    // 绿色系：0-5% 浅绿，5-15% 中绿，>15% 深绿
    if (absValue < 0.02) return 'bg-green-50 dark:bg-green-950/30'
    if (absValue < 0.05) return 'bg-green-100 dark:bg-green-900/40'
    if (absValue < 0.10) return 'bg-green-200 dark:bg-green-800/50'
    if (absValue < 0.20) return 'bg-green-300 dark:bg-green-700/60'
    return 'bg-green-400 dark:bg-green-600/70'
  } else {
    // 红色系
    if (absValue < 0.02) return 'bg-red-50 dark:bg-red-950/30'
    if (absValue < 0.05) return 'bg-red-100 dark:bg-red-900/40'
    if (absValue < 0.10) return 'bg-red-200 dark:bg-red-800/50'
    if (absValue < 0.20) return 'bg-red-300 dark:bg-red-700/60'
    return 'bg-red-400 dark:bg-red-600/70'
  }
}

/**
 * 构建月度热力图数据矩阵
 */
function buildMonthlyMatrix(
  monthReturn: PeriodReturn[],
  yearReturn: PeriodReturn[]
): {
  years: number[]
  matrix: Map<string, { display: string; value: number | null }>
  yearTotals: Map<number, { display: string; value: number | null }>
} {
  const matrix = new Map<string, { display: string; value: number | null }>()
  const yearsSet = new Set<number>()
  const yearTotals = new Map<number, { display: string; value: number | null }>()

  // 解析月度数据
  for (const item of monthReturn) {
    if (!item.candle_begin_time) continue
    const date = new Date(item.candle_begin_time)
    if (Number.isNaN(date.getTime())) continue

    const year = date.getFullYear()
    const month = date.getMonth() + 1
    yearsSet.add(year)

    const key = `${year}-${month}`
    const value = parseReturnValue(item.涨跌幅)
    matrix.set(key, {
      display: item.涨跌幅 || '-',
      value,
    })
  }

  // 解析年度汇总数据
  for (const item of yearReturn) {
    if (!item.candle_begin_time) continue
    const date = new Date(item.candle_begin_time)
    if (Number.isNaN(date.getTime())) continue

    const year = date.getFullYear()
    yearsSet.add(year)

    const value = parseReturnValue(item.涨跌幅)
    yearTotals.set(year, {
      display: item.涨跌幅 || '-',
      value,
    })
  }

  // 按年份升序排列（从古到今）
  const years = Array.from(yearsSet).sort((a, b) => a - b)

  return { years, matrix, yearTotals }
}

/**
 * 周期收益热力图组件
 */
function PeriodReturnHeatmap({
  yearReturn,
  quarterReturn,
  monthReturn,
}: {
  yearReturn: PeriodReturn[]
  quarterReturn: PeriodReturn[]
  monthReturn: PeriodReturn[]
}) {
  // 没有任何周期数据时不展示
  if (yearReturn.length === 0 && quarterReturn.length === 0 && monthReturn.length === 0) {
    return null
  }

  const { years, matrix, yearTotals } = buildMonthlyMatrix(monthReturn, yearReturn)
  const months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

  // 如果没有月度数据但有年度数据，显示简化版
  if (monthReturn.length === 0 && yearReturn.length > 0) {
    return (
      <div className="rounded-lg border bg-card p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium">
          <BarChart3 className="h-4 w-4" />
          年度收益
        </h3>
        <div className="flex flex-wrap gap-2">
          {yearReturn.map((item, index) => {
            const date = new Date(item.candle_begin_time)
            const year = Number.isNaN(date.getTime()) ? '-' : date.getFullYear()
            const value = parseReturnValue(item.涨跌幅)
            const colorClass = value !== null
              ? value >= 0 ? 'text-green-600' : 'text-red-600'
              : ''

            return (
              <div
                key={index}
                className={cn(
                  'rounded-md px-3 py-2',
                  getReturnBgColor(value)
                )}
              >
                <div className="text-xs text-muted-foreground">{year}年</div>
                <div className={cn('text-sm font-semibold', colorClass)}>
                  {item.涨跌幅 || '-'}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-medium">
        <BarChart3 className="h-4 w-4" />
        周期收益
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="px-1 py-1.5 text-left font-medium text-muted-foreground">年份</th>
              {months.map((m) => (
                <th key={m} className="px-1 py-1.5 text-center font-medium text-muted-foreground">
                  {m}月
                </th>
              ))}
              <th className="px-1 py-1.5 text-center font-medium text-muted-foreground border-l">
                全年
              </th>
            </tr>
          </thead>
          <tbody>
            {years.map((year) => {
              const yearTotal = yearTotals.get(year)
              const yearColorClass = yearTotal?.value !== null && yearTotal?.value !== undefined
                ? yearTotal.value >= 0 ? 'text-green-600' : 'text-red-600'
                : ''

              return (
                <tr key={year} className="border-t">
                  <td className="px-1 py-1.5 font-medium">{year}</td>
                  {months.map((month) => {
                    const key = `${year}-${month}`
                    const cell = matrix.get(key)
                    const colorClass = cell?.value !== null && cell?.value !== undefined
                      ? cell.value >= 0 ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'
                      : 'text-muted-foreground'

                    return (
                      <td
                        key={month}
                        className={cn(
                          'px-1 py-1.5 text-center font-mono',
                          getReturnBgColor(cell?.value ?? null),
                          colorClass
                        )}
                      >
                        {cell?.display || '-'}
                      </td>
                    )
                  })}
                  <td
                    className={cn(
                      'px-1 py-1.5 text-center font-mono font-semibold border-l',
                      getReturnBgColor(yearTotal?.value ?? null),
                      yearColorClass
                    )}
                  >
                    {yearTotal?.display || '-'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function Component() {
  const { id } = useParams<{ id: string }>()
  const { data: strategy, isLoading, error } = useStrategy(id || '')

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error || !strategy) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <p className="text-destructive">
          {error ? `加载失败: ${(error as Error).message}` : '策略不存在'}
        </p>
        <Link
          to="/strategies"
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          返回策略列表
        </Link>
      </div>
    )
  }

  const factorList = parseJSON<string[]>(strategy.factor_list, [])
  const factorParams = parseJSON<Record<string, unknown>>(strategy.factor_params, {})
  const sortDirections = parseJSON<Record<string, boolean>>(strategy.sort_directions, {})

  // 解析资金曲线数据（支持完整的多子图数据）
  const equityCurve = parseJSON<EquityCurveDataPoint[]>(
    strategy.equity_curve,
    []
  )

  // 解析周期收益数据
  const yearReturn = parseJSON<PeriodReturn[]>(strategy.year_return, [])
  const quarterReturn = parseJSON<PeriodReturn[]>(strategy.quarter_return, [])
  const monthReturn = parseJSON<PeriodReturn[]>(strategy.month_return, [])

  // 格式化因子显示（包含参数和排序方向）
  const formatFactorDisplay = () => {
    return factorList.map(name => {
      const param = factorParams[name]
      const isAsc = sortDirections[name]
      const direction = isAsc !== undefined ? (isAsc ? '升' : '降') : ''
      const paramStr = param !== undefined ? `(${Array.isArray(param) ? param.join(',') : param})` : ''
      return `${name}${paramStr}${direction ? ` [${direction}]` : ''}`
    }).join(', ')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link
            to="/strategies"
            className="mb-2 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            返回列表
          </Link>
          <h1 className="text-2xl font-bold">{strategy.name}</h1>
          {strategy.description && (
            <p className="mt-1 text-muted-foreground">{strategy.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {strategy.verified && (
            <span className="flex items-center gap-1 rounded-full bg-green-100 px-2 py-1 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400">
              <CheckCircle className="h-3 w-3" />
              已验证
            </span>
          )}
        </div>
      </div>

      {/* Config Info */}
      <div className="rounded-lg border bg-card p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium">
          <Settings className="h-4 w-4" />
          回测配置
        </h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <p className="text-xs text-muted-foreground">回测时间</p>
            <p className="flex items-center gap-1 text-sm">
              <Calendar className="h-3.5 w-3.5" />
              {strategy.start_date || '-'} ~ {strategy.end_date || '-'}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">持仓周期</p>
            <p className="text-sm font-medium">{strategy.hold_period || '-'}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">杠杆倍数</p>
            <p className="text-sm font-medium">{strategy.leverage}x</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">交易市场</p>
            <p className="text-sm font-medium">{strategy.market || strategy.trade_type}</p>
          </div>
        </div>

        {/* 多空配置 */}
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <p className="text-xs text-muted-foreground">多头选币</p>
            <p className="text-sm font-medium text-green-600">
              {strategy.long_select_coin_num ?? strategy.select_coin_num}
              {strategy.long_cap_weight !== undefined && ` (权重: ${strategy.long_cap_weight})`}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">空头选币</p>
            <p className="text-sm font-medium text-red-600">
              {strategy.short_select_coin_num ?? 0}
              {strategy.short_cap_weight !== undefined && strategy.short_cap_weight > 0 && ` (权重: ${strategy.short_cap_weight})`}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">初始资金</p>
            <p className="text-sm font-medium">{strategy.initial_usdt?.toLocaleString() ?? 10000} USDT</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">账户类型</p>
            <p className="text-sm font-medium">{strategy.account_type || '统一账户'}</p>
          </div>
        </div>

        {/* 因子配置 */}
        {factorList.length > 0 && (
          <div className="mt-4">
            <p className="text-xs text-muted-foreground">因子配置 (名称/参数/排序方向)</p>
            <p className="mt-1 text-sm font-mono">{formatFactorDisplay()}</p>
          </div>
        )}
      </div>

      {/* Core Metrics */}
      <div className="rounded-lg border bg-card p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium">
          <TrendingUp className="h-4 w-4" />
          策略评价
        </h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {CORE_METRICS.map((key) => {
            const value = strategy[key as keyof Strategy]
            if (value === undefined || value === null) return null
            return (
              <div key={key} className="rounded-md bg-muted p-3">
                <p className="text-xs text-muted-foreground">
                  {METRIC_LABELS[key] || key}
                </p>
                <p
                  className={cn(
                    'text-xl font-bold',
                    getMetricColor(key, value)
                  )}
                >
                  {formatMetricValue(key, value)}
                </p>
              </div>
            )
          })}
        </div>
      </div>

      {/* Trading Stats */}
      <div className="rounded-lg border bg-card p-4">
        <h3 className="mb-3 text-sm font-medium">交易统计</h3>
        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {TRADING_METRICS.map((key) => {
            const value = strategy[key as keyof Strategy]
            if (value === undefined || value === null) return null
            return (
              <div key={key} className="rounded-md bg-muted/50 p-2.5">
                <p className="text-[10px] text-muted-foreground">
                  {METRIC_LABELS[key] || key}
                </p>
                <p className={cn('text-sm font-semibold', getMetricColor(key, value))}>
                  {formatMetricValue(key, value)}
                </p>
              </div>
            )
          })}
        </div>
      </div>

      {/* Extreme Stats */}
      <div className="rounded-lg border bg-card p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium">
          <TrendingDown className="h-4 w-4" />
          极值统计
        </h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {EXTREME_METRICS.map((key) => {
            const value = strategy[key as keyof Strategy]
            if (value === undefined || value === null) return null
            return (
              <div key={key} className="rounded-md bg-muted/50 p-2.5">
                <p className="text-[10px] text-muted-foreground">
                  {METRIC_LABELS[key] || key}
                </p>
                <p
                  className={cn(
                    'text-sm font-semibold',
                    getMetricColor(key, value)
                  )}
                >
                  {formatMetricValue(key, value)}
                </p>
              </div>
            )
          })}
        </div>
      </div>

      {/* Drawdown Info */}
      {(strategy.max_drawdown_start || strategy.max_drawdown_end) && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="mb-3 text-sm font-medium">回撤时间</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {strategy.max_drawdown_start && (
              <div className="rounded-md bg-muted/50 p-2.5">
                <p className="text-[10px] text-muted-foreground">最大回撤开始</p>
                <p className="text-sm font-mono">{strategy.max_drawdown_start}</p>
              </div>
            )}
            {strategy.max_drawdown_end && (
              <div className="rounded-md bg-muted/50 p-2.5">
                <p className="text-[10px] text-muted-foreground">最大回撤结束</p>
                <p className="text-sm font-mono">{strategy.max_drawdown_end}</p>
              </div>
            )}
            {strategy.recovery_rate !== undefined && (
              <div className="rounded-md bg-muted/50 p-2.5">
                <p className="text-[10px] text-muted-foreground">修复涨幅</p>
                <p className="text-sm font-semibold">{formatPercent(strategy.recovery_rate)}</p>
              </div>
            )}
            {strategy.recovery_time && (
              <div className="rounded-md bg-muted/50 p-2.5">
                <p className="text-[10px] text-muted-foreground">修复时间</p>
                <p className="text-sm font-mono">{strategy.recovery_time}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Equity Curve with Subplots */}
      {equityCurve.length > 0 && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="mb-3 text-sm font-medium">资金曲线</h3>
          <EquityCurveSubplots data={equityCurve} height={600} />
        </div>
      )}

      {/* Period Returns */}
      <PeriodReturnHeatmap
        yearReturn={yearReturn}
        quarterReturn={quarterReturn}
        monthReturn={monthReturn}
      />

      {/* 知识关联图 */}
      {strategy.name && (
        <EntityGraph
          entityType="strategy"
          entityId={strategy.name}
          entityName={strategy.name}
          height={250}
        />
      )}

      {/* Notes */}
      {strategy.notes && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="mb-3 text-sm font-medium">备注</h3>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">{strategy.notes}</p>
        </div>
      )}

      {/* Metadata */}
      <div className="text-xs text-muted-foreground">
        <p>创建时间: {strategy.created_at || '-'}</p>
        <p>更新时间: {strategy.updated_at || '-'}</p>
        <p>策略ID: {strategy.id}</p>
      </div>
    </div>
  )
}
