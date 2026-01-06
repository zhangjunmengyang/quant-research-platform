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
} from 'lucide-react'
import { useStrategy } from '@/features/strategy'
import { EquityCurve } from '@/components/charts'
import { cn, formatPercent } from '@/lib/utils'
import type { Strategy } from '@/features/strategy'

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
  const equityCurve = parseJSON<Array<{ time: string; value: number }>>(strategy.equity_curve, [])

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

      {/* Equity Curve */}
      {equityCurve.length > 0 && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="mb-3 text-sm font-medium">资金曲线</h3>
          <EquityCurve data={equityCurve} height={350} />
        </div>
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
