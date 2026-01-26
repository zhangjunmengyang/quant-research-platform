/**
 * Data Monitor Page - New Coins Price Dashboard
 * 数据观察页面 - 显示近N天上线的新币价格走势看板
 * 使用美观的折线图展示，支持鼠标悬浮查看详情
 */

import { useMemo, useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, TrendingUp, TrendingDown, Calendar, RefreshCw, Eye, ChevronDown } from 'lucide-react'
import { useSymbols, useKline } from '@/features/data'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import type { Symbol, KlineData } from '@/features/data/types'
import * as echarts from 'echarts'

// 计算 N 天前的日期
function getDaysAgo(days: number): Date {
  const date = new Date()
  date.setDate(date.getDate() - days)
  date.setHours(0, 0, 0, 0)
  return date
}

// 计算涨跌幅 - 使用第一个有效价格
function calculateChange(data: KlineData[]): { value: number; isPositive: boolean } | null {
  if (!data || data.length < 2) return null

  // 找到第一个有效的开盘价（非0非null）
  let firstValidOpen: number | null = null
  for (const item of data) {
    if (item.open && item.open > 0) {
      firstValidOpen = item.open
      break
    }
  }

  const last = data[data.length - 1]
  if (!firstValidOpen || !last || !last.close) return null

  const change = ((last.close - firstValidOpen) / firstValidOpen) * 100

  // 检查是否为有效数字
  if (!Number.isFinite(change)) return null

  return { value: change, isPositive: change >= 0 }
}

// 格式化数字显示
function formatNumber(num: number): string {
  if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B'
  if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M'
  if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K'
  if (num < 0.0001) return num.toExponential(2)
  if (num < 1) return num.toPrecision(4)
  return num.toFixed(2)
}

// 格式化时间显示
function formatTime(timeStr: string): string {
  const date = new Date(timeStr)
  return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
}

// 美观的价格折线图组件 - 支持hover交互
function MiniPriceChart({
  data,
  height = 100,
  isPositive = true,
}: {
  data: KlineData[]
  height?: number
  isPositive?: boolean
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const chart = echarts.init(containerRef.current)
    chartRef.current = chart

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.dispose()
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!chartRef.current || !data || data.length === 0) return

    // 过滤掉无效数据点（价格为0或null的数据）
    const validData = data.filter((d) => d.close && d.close > 0)
    if (validData.length === 0) return

    const times = validData.map((d) => d.time)
    const prices = validData.map((d) => d.close)

    // 根据涨跌选择颜色
    const lineColor = isPositive ? '#22c55e' : '#ef4444'
    const areaColorStart = isPositive ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'
    const areaColorEnd = isPositive ? 'rgba(34, 197, 94, 0.02)' : 'rgba(239, 68, 68, 0.02)'

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      animation: false,
      grid: {
        left: 4,
        right: 4,
        top: 8,
        bottom: 4,
      },
      tooltip: {
        trigger: 'axis',
        confine: false,
        appendToBody: true,
        backgroundColor: 'rgba(255, 255, 255, 0.98)',
        borderColor: '#e5e7eb',
        borderWidth: 1,
        padding: [8, 12],
        textStyle: {
          color: '#374151',
          fontSize: 12,
        },
        axisPointer: {
          type: 'line',
          lineStyle: {
            color: '#9ca3af',
            type: 'dashed',
          },
        },
        formatter: (params: unknown) => {
          const paramArray = params as Array<{
            axisValue: string
            dataIndex: number
            data: number
          }>
          if (!paramArray || paramArray.length === 0) return ''

          const firstParam = paramArray[0]
          if (!firstParam) return ''

          const dataIndex = firstParam.dataIndex
          const pointData = validData[dataIndex]
          if (!pointData) return ''

          // 第一个有效数据点的价格作为基准
          const basePrice = validData[0]?.close ?? 0

          // 计算涨跌幅
          let changeStr = '-'
          let changeColor = '#9ca3af'
          if (basePrice > 0 && pointData.close > 0) {
            const change = ((pointData.close - basePrice) / basePrice) * 100
            if (Number.isFinite(change)) {
              changeStr = change >= 0 ? `+${change.toFixed(2)}%` : `${change.toFixed(2)}%`
              changeColor = change >= 0 ? '#22c55e' : '#ef4444'
            }
          }

          return `
            <div style="min-width: 140px">
              <div style="color: #6b7280; font-size: 11px; margin-bottom: 6px">${formatTime(pointData.time)}</div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px">
                <span style="color: #9ca3af">价格</span>
                <span style="font-weight: 600; font-family: monospace">${formatNumber(pointData.close)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px">
                <span style="color: #9ca3af">涨跌</span>
                <span style="font-weight: 500; color: ${changeColor}; font-family: monospace">${changeStr}</span>
              </div>
              ${pointData.quote_volume ? `
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px">
                <span style="color: #9ca3af">成交额</span>
                <span style="font-family: monospace">${formatNumber(pointData.quote_volume)}</span>
              </div>
              ` : ''}
              <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; padding-top: 4px; border-top: 1px solid #f3f4f6; margin-top: 4px">
                <span style="color: #9ca3af; font-size: 10px">H ${formatNumber(pointData.high)}</span>
                <span style="color: #9ca3af; font-size: 10px">L ${formatNumber(pointData.low)}</span>
              </div>
            </div>
          `
        },
      },
      xAxis: {
        type: 'category',
        data: times,
        show: false,
        boundaryGap: false,
      },
      yAxis: {
        type: 'value',
        show: false,
        scale: true,
      },
      series: [
        {
          type: 'line',
          data: prices,
          smooth: 0.3,
          symbol: 'none',
          lineStyle: {
            width: 1.5,
            color: lineColor,
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: areaColorStart },
                { offset: 1, color: areaColorEnd },
              ],
            },
          },
          emphasis: {
            lineStyle: {
              width: 2,
            },
          },
        },
      ],
    }

    chartRef.current.setOption(option, { notMerge: true })
  }, [data, isPositive])

  return <div ref={containerRef} style={{ width: '100%', height }} />
}

// 单个新币卡片组件
function NewCoinCard({ symbol, daysFilter, chartHeight }: { symbol: Symbol; daysFilter: number; chartHeight: number }) {
  // 计算应该获取的数据范围：从币种上线时间或筛选时间的较晚者开始
  const startDate = useMemo(() => {
    const filterStartDate = getDaysAgo(daysFilter)
    if (symbol.first_candle_time) {
      const listingDate = new Date(symbol.first_candle_time)
      return listingDate > filterStartDate ? listingDate : filterStartDate
    }
    return filterStartDate
  }, [symbol.first_candle_time, daysFilter])

  const { data: klineData, isLoading } = useKline(symbol.symbol, 'swap', {
    start_date: startDate.toISOString().split('T')[0],
    limit: 2000,
  })

  const change = useMemo(() => {
    if (!klineData || klineData.length === 0) return null
    return calculateChange(klineData)
  }, [klineData])

  // 获取最新价格
  const latestPrice = useMemo(() => {
    if (!klineData || klineData.length === 0) return null
    const lastData = klineData[klineData.length - 1]
    return lastData?.close ?? null
  }, [klineData])

  const listingDate = symbol.first_candle_time
    ? new Date(symbol.first_candle_time).toLocaleDateString('zh-CN', {
        month: 'numeric',
        day: 'numeric',
      })
    : '-'

  return (
    <Card className="overflow-hidden transition-all hover:shadow-md group">
      {/* 头部信息 - 紧凑布局 */}
      <div className="flex items-center justify-between px-2.5 py-1.5 border-b bg-muted/20">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-xs font-semibold truncate">{symbol.symbol.replace('-USDT', '')}</span>
          <span className="text-2xs text-muted-foreground flex items-center gap-0.5">
            <Calendar className="h-2.5 w-2.5" />
            {listingDate}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {latestPrice && (
            <span className="text-2xs font-mono text-muted-foreground">
              {formatNumber(latestPrice)}
            </span>
          )}
          {change && (
            <Badge
              variant="outline"
              className={cn(
                'text-2xs font-mono px-1 py-0 h-4',
                change.isPositive
                  ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-400'
                  : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400'
              )}
            >
              {change.isPositive ? (
                <TrendingUp className="h-2.5 w-2.5 mr-0.5" />
              ) : (
                <TrendingDown className="h-2.5 w-2.5 mr-0.5" />
              )}
              {change.isPositive ? '+' : ''}
              {change.value.toFixed(1)}%
            </Badge>
          )}
        </div>
      </div>
      {/* 价格折线图 - 支持hover */}
      <CardContent className="p-0">
        {isLoading ? (
          <div className="flex items-center justify-center" style={{ height: chartHeight }}>
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        ) : klineData && klineData.length > 0 ? (
          <MiniPriceChart
            data={klineData}
            height={chartHeight}
            isPositive={change?.isPositive ?? true}
          />
        ) : (
          <div className="flex items-center justify-center text-2xs text-muted-foreground" style={{ height: chartHeight }}>
            暂无数据
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// 固定布局配置
const GRID_COLS = 'grid-cols-2 md:grid-cols-4'
const CHART_HEIGHT = 100

// 主流币列表
const MAJOR_COINS = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT', 'BNB-USDT']

// 主流币卡片组件
function MajorCoinCard({ symbol, daysFilter }: { symbol: string; daysFilter: number }) {
  const startDate = useMemo(() => getDaysAgo(daysFilter), [daysFilter])

  const { data: klineData, isLoading } = useKline(symbol, 'swap', {
    start_date: startDate.toISOString().split('T')[0],
    limit: 2000,
  })

  const change = useMemo(() => {
    if (!klineData || klineData.length === 0) return null
    return calculateChange(klineData)
  }, [klineData])

  const latestPrice = useMemo(() => {
    if (!klineData || klineData.length === 0) return null
    const lastData = klineData[klineData.length - 1]
    return lastData?.close ?? null
  }, [klineData])

  const coinName = symbol.replace('-USDT', '')

  return (
    <Card className="overflow-hidden transition-all hover:shadow-md">
      <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/20">
        <span className="text-sm font-semibold">{coinName}</span>
        <div className="flex items-center gap-2">
          {latestPrice && (
            <span className="text-xs font-mono text-muted-foreground">
              {formatNumber(latestPrice)}
            </span>
          )}
          {change && (
            <Badge
              variant="outline"
              className={cn(
                'text-xs font-mono px-1.5 py-0 h-5',
                change.isPositive
                  ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-400'
                  : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400'
              )}
            >
              {change.isPositive ? (
                <TrendingUp className="h-3 w-3 mr-0.5" />
              ) : (
                <TrendingDown className="h-3 w-3 mr-0.5" />
              )}
              {change.isPositive ? '+' : ''}
              {change.value.toFixed(2)}%
            </Badge>
          )}
        </div>
      </div>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="flex items-center justify-center h-[100px]">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        ) : klineData && klineData.length > 0 ? (
          <MiniPriceChart
            data={klineData}
            height={100}
            isPositive={change?.isPositive ?? true}
          />
        ) : (
          <div className="flex items-center justify-center h-[100px] text-xs text-muted-foreground">
            暂无数据
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function Component() {
  const { t } = useTranslation()
  const { data: symbols, isLoading, refetch, isRefetching } = useSymbols()
  const [daysFilter, setDaysFilter] = useState(30)
  const [majorCoinsOpen, setMajorCoinsOpen] = useState(true)
  const [newCoinsOpen, setNewCoinsOpen] = useState(true)

  // 筛选近 N 天上线的新币
  const newCoins = useMemo(() => {
    if (!symbols) return []
    const cutoffDate = getDaysAgo(daysFilter)

    return symbols
      .filter((s) => {
        // 只要有合约数据
        if (!s.has_swap) return false
        // 有上线时间
        if (!s.first_candle_time) return false
        // 上线时间在 cutoff 之后
        const listingDate = new Date(s.first_candle_time)
        return listingDate >= cutoffDate
      })
      .sort((a, b) => {
        // 按上线时间降序（最新的在前）
        const dateA = new Date(a.first_candle_time ?? 0)
        const dateB = new Date(b.first_candle_time ?? 0)
        return dateB.getTime() - dateA.getTime()
      })
  }, [symbols, daysFilter])

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-3 p-3">
      {/* 标题和控制栏 */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold flex items-center gap-2">
            <Eye className="h-5 w-5" />
            {t('nav.dataMonitor')}
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* 时间筛选 */}
          <div className="flex items-center rounded-md border bg-background">
            {[7, 14, 30, 60].map((days) => (
              <Button
                key={days}
                variant="ghost"
                size="sm"
                className={cn(
                  'h-7 rounded-none px-2.5 text-xs',
                  daysFilter === days && 'bg-muted'
                )}
                onClick={() => setDaysFilter(days)}
              >
                {days}D
              </Button>
            ))}
          </div>

          {/* 刷新按钮 */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isRefetching}
            className="h-7"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', isRefetching && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {/* 主流币区域 */}
      <Collapsible open={majorCoinsOpen} onOpenChange={setMajorCoinsOpen}>
        <div className="rounded-lg border bg-muted/30 p-3">
          <CollapsibleTrigger asChild>
            <button className="w-full text-sm font-medium text-foreground mb-2 flex items-center justify-between hover:opacity-80 transition-opacity">
              <span className="flex items-center gap-1.5">
                <div className="w-1 h-4 bg-muted-foreground/50 rounded-full" />
                主流币
              </span>
              <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', majorCoinsOpen && 'rotate-180')} />
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {MAJOR_COINS.map((symbol) => (
                <MajorCoinCard key={symbol} symbol={symbol} daysFilter={daysFilter} />
              ))}
            </div>
          </CollapsibleContent>
        </div>
      </Collapsible>

      {/* 新币区域 */}
      <Collapsible open={newCoinsOpen} onOpenChange={setNewCoinsOpen}>
        <div className="rounded-lg border bg-muted/30 p-3">
          <CollapsibleTrigger asChild>
            <button className="w-full text-sm font-medium text-foreground mb-2 flex items-center justify-between hover:opacity-80 transition-opacity">
              <span className="flex items-center gap-1.5">
                <div className="w-1 h-4 bg-muted-foreground/50 rounded-full" />
                新币
                <span className="text-xs font-normal text-muted-foreground">({newCoins.length})</span>
              </span>
              <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', newCoinsOpen && 'rotate-180')} />
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            {newCoins.length === 0 ? (
              <Card>
                <CardContent className="flex h-32 flex-col items-center justify-center gap-2 text-muted-foreground">
                  <p className="text-sm">{t('data.noNewCoins')}</p>
                </CardContent>
              </Card>
            ) : (
              <div className={cn('grid gap-2', GRID_COLS)}>
                {newCoins.map((symbol) => (
                  <NewCoinCard
                    key={symbol.symbol}
                    symbol={symbol}
                    daysFilter={daysFilter}
                    chartHeight={CHART_HEIGHT}
                  />
                ))}
              </div>
            )}
          </CollapsibleContent>
        </div>
      </Collapsible>
    </div>
  )
}
