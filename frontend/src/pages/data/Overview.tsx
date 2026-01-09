/**
 * Data Overview Page
 * 数据概览页 - 展示数据统计、币种列表和K线详情
 */

import { useState, useMemo, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Loader2,
  Database,
  Coins,
  Calendar,
  RefreshCw,
  Search,
  Filter,
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from 'lucide-react'
import { useDataOverview, useSymbols, useKline } from '@/features/data'
import type { Symbol } from '@/features/data'
import { StatsCard } from '@/features/factor/components/StatsCard'
import { KlineChart } from '@/components/charts'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'

// 排序字段类型
type SortField = 'symbol' | 'type' | 'first_candle_time' | 'last_candle_time' | 'kline_count'
type SortOrder = 'asc' | 'desc'

// 获取类型排序值（用于排序: 仅现货=0, 仅合约=1, 都有=2）
function getTypeSortValue(symbol: Symbol): number {
  if (symbol.has_spot && symbol.has_swap) return 2
  if (symbol.has_swap) return 1
  if (symbol.has_spot) return 0
  return -1
}

// 每页显示数量选项
const PAGE_SIZE_OPTIONS = [20, 50, 100, 200]

// 类型筛选选项
const FILTER_TYPE_OPTIONS: SelectOption[] = [
  { value: 'all', label: '全部类型' },
  { value: 'spot', label: '现货' },
  { value: 'swap', label: '合约' },
]

// 每页条数选项
const PAGE_SIZE_SELECT_OPTIONS: SelectOption[] = PAGE_SIZE_OPTIONS.map(size => ({
  value: String(size),
  label: `${size} 条/页`,
}))

export function Component() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { data: overview, isLoading: overviewLoading, refetch } = useDataOverview()
  const { data: symbols = [], isLoading: symbolsLoading } = useSymbols()
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<'all' | 'spot' | 'swap'>('all')

  // 排序状态
  const [sortField, setSortField] = useState<SortField>('first_candle_time')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)

  // 从 URL 获取选中的币种
  const selectedSymbolName = searchParams.get('symbol')
  const selectedDataType = searchParams.get('type') as 'spot' | 'swap' | null

  // 日期范围 - 默认近30天
  const [dateRange, setDateRange] = useState(() => {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - 30)
    return {
      start_date: start.toISOString().slice(0, 10),
      end_date: '',
    }
  })

  // 详情页分页状态
  const [detailPage, setDetailPage] = useState(1)
  const [detailPageSize, setDetailPageSize] = useState(50)

  // 根据 URL 参数找到选中的币种
  const selectedSymbol = useMemo(() => {
    if (!selectedSymbolName) return null
    return symbols.find(s => s.symbol === selectedSymbolName) || null
  }, [symbols, selectedSymbolName])

  // 确定要查看的数据类型（URL 指定 > 币种支持的类型，优先 swap）
  const viewDataType = useMemo(() => {
    if (selectedDataType) return selectedDataType
    if (selectedSymbol?.has_swap) return 'swap'
    if (selectedSymbol?.has_spot) return 'spot'
    return 'swap'
  }, [selectedDataType, selectedSymbol])

  // 构建日期参数 - 确保 queryKey 稳定
  const klineParams = useMemo(() => {
    const params: { start_date?: string; end_date?: string } = {}
    if (dateRange.start_date) params.start_date = dateRange.start_date
    if (dateRange.end_date) params.end_date = dateRange.end_date
    return Object.keys(params).length > 0 ? params : undefined
  }, [dateRange.start_date, dateRange.end_date])

  // 获取K线数据
  const { data: klineData = [], isLoading: klineLoading } = useKline(
    selectedSymbol?.symbol || '',
    viewDataType,
    klineParams
  )

  // 当选中币种变化时重置详情页状态
  useEffect(() => {
    setDetailPage(1)
    // 重置为近30天
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - 30)
    setDateRange({
      start_date: start.toISOString().slice(0, 10),
      end_date: '',
    })
  }, [selectedSymbolName, selectedDataType])

  // 过滤和排序
  const filteredAndSortedSymbols = useMemo(() => {
    let result = symbols

    // 按类型过滤
    if (filterType === 'spot') {
      result = result.filter((s) => s.has_spot)
    } else if (filterType === 'swap') {
      result = result.filter((s) => s.has_swap)
    }

    // 按搜索关键词过滤
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (s) =>
          s.symbol.toLowerCase().includes(query) ||
          s.base_currency.toLowerCase().includes(query)
      )
    }

    // 排序
    result = [...result].sort((a, b) => {
      let compareResult = 0
      switch (sortField) {
        case 'symbol':
          compareResult = a.symbol.localeCompare(b.symbol)
          break
        case 'type':
          compareResult = getTypeSortValue(a) - getTypeSortValue(b)
          break
        case 'first_candle_time':
          const aFirst = a.first_candle_time || ''
          const bFirst = b.first_candle_time || ''
          compareResult = aFirst.localeCompare(bFirst)
          break
        case 'last_candle_time':
          const aLast = a.last_candle_time || ''
          const bLast = b.last_candle_time || ''
          compareResult = aLast.localeCompare(bLast)
          break
        case 'kline_count':
          compareResult = (a.kline_count || 0) - (b.kline_count || 0)
          break
      }
      return sortOrder === 'asc' ? compareResult : -compareResult
    })

    return result
  }, [symbols, searchQuery, filterType, sortField, sortOrder])

  // 分页数据
  const paginatedSymbols = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize
    return filteredAndSortedSymbols.slice(startIndex, startIndex + pageSize)
  }, [filteredAndSortedSymbols, currentPage, pageSize])

  const totalPages = Math.ceil(filteredAndSortedSymbols.length / pageSize)

  // K线图数据 - 直接使用 klineData（类型兼容，无需转换）

  // 详情页分页数据
  const paginatedKlineData = useMemo(() => {
    const reversed = [...klineData].reverse()
    const startIndex = (detailPage - 1) * detailPageSize
    return reversed.slice(startIndex, startIndex + detailPageSize)
  }, [klineData, detailPage, detailPageSize])

  const detailTotalPages = Math.ceil(klineData.length / detailPageSize)

  // 计算统计信息 - 单次遍历优化
  const klineStats = useMemo(() => {
    const len = klineData.length
    if (len === 0) return null

    let high = -Infinity
    let low = Infinity
    let totalVolume = 0
    let totalQuoteVolume = 0
    let quoteVolumeCount = 0
    let totalBuyRatio = 0
    let buyRatioCount = 0
    let totalFundingFee = 0
    let fundingFeeCount = 0

    // 单次遍历计算所有统计量
    for (const d of klineData) {
      if (d.high > high) high = d.high
      if (d.low < low) low = d.low
      totalVolume += d.volume

      if (d.quote_volume != null) {
        totalQuoteVolume += d.quote_volume
        quoteVolumeCount++

        if (d.taker_buy_quote_asset_volume != null && d.quote_volume > 0) {
          totalBuyRatio += d.taker_buy_quote_asset_volume / d.quote_volume
          buyRatioCount++
        }
      }

      if (d.funding_fee != null && d.funding_fee !== 0) {
        totalFundingFee += d.funding_fee
        fundingFeeCount++
      }
    }

    const first = klineData[0]?.close ?? 0
    const latest = klineData[len - 1]?.close ?? 0
    const change = first ? ((latest - first) / first) * 100 : 0

    return {
      latest,
      high,
      low,
      change,
      avgVolume: totalVolume / len,
      avgQuoteVolume: quoteVolumeCount > 0 ? totalQuoteVolume / quoteVolumeCount : null,
      avgBuyRatio: buyRatioCount > 0 ? (totalBuyRatio / buyRatioCount) * 100 : null,
      avgFundingFee: fundingFeeCount > 0 ? (totalFundingFee / fundingFeeCount) * 100 : null,
      dataPoints: len,
    }
  }, [klineData])

  // 点击排序
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
    setCurrentPage(1)
  }

  // 渲染排序图标
  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-4 w-4 text-muted-foreground/50" />
    }
    return sortOrder === 'asc'
      ? <ArrowUp className="h-4 w-4" />
      : <ArrowDown className="h-4 w-4" />
  }

  // 点击币种 - 使用 URL 参数（优先 swap）
  const handleSymbolClick = (symbol: Symbol, dataType?: 'spot' | 'swap') => {
    const type = dataType || (symbol.has_swap ? 'swap' : 'spot')
    setSearchParams({ symbol: symbol.symbol, type })
  }

  // 返回列表 - 清除 URL 参数
  const handleBack = () => {
    setSearchParams({})
  }

  // 重置分页
  const handleFilterChange = (type: 'all' | 'spot' | 'swap') => {
    setFilterType(type)
    setCurrentPage(1)
  }

  const handleSearchChange = (query: string) => {
    setSearchQuery(query)
    setCurrentPage(1)
  }

  const handlePageSizeChange = (size: number) => {
    setPageSize(size)
    setCurrentPage(1)
  }

  if (overviewLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // 如果选中了币种，展示详情
  if (selectedSymbol) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent"
          >
            <ArrowLeft className="h-4 w-4" />
            返回列表
          </button>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-semibold">{selectedSymbol.symbol}</h2>
            {/* 数据类型切换按钮 */}
            <div className="flex gap-1">
              {selectedSymbol.has_spot && (
                <button
                  onClick={() => handleSymbolClick(selectedSymbol, 'spot')}
                  className={`rounded-full px-2 py-1 text-xs font-medium transition-colors ${
                    viewDataType === 'spot'
                      ? 'bg-warning text-warning-foreground'
                      : 'bg-warning-muted text-warning hover:bg-warning/20'
                  }`}
                >
                  现货
                </button>
              )}
              {selectedSymbol.has_swap && (
                <button
                  onClick={() => handleSymbolClick(selectedSymbol, 'swap')}
                  className={`rounded-full px-2 py-1 text-xs font-medium transition-colors ${
                    viewDataType === 'swap'
                      ? 'bg-info text-info-foreground'
                      : 'bg-info-muted text-info hover:bg-info/20'
                  }`}
                >
                  合约
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Date Range Filter */}
        <div className="rounded-lg border bg-card p-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* 快捷按钮 */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground mr-1">快捷:</span>
              {[
                { label: '7天', days: 7 },
                { label: '30天', days: 30 },
                { label: '90天', days: 90 },
                { label: '180天', days: 180 },
              ].map(({ label, days }) => {
                const isActive = (() => {
                  if (!dateRange.start_date) return false
                  const start = new Date(dateRange.start_date)
                  const now = new Date()
                  const diffDays = Math.round((now.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
                  return diffDays === days && !dateRange.end_date
                })()
                return (
                  <button
                    key={label}
                    onClick={() => {
                      const end = new Date()
                      const start = new Date()
                      start.setDate(end.getDate() - days)
                      setDateRange({
                        start_date: start.toISOString().slice(0, 10),
                        end_date: '',
                      })
                    }}
                    className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                      isActive
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted hover:bg-muted/80'
                    }`}
                  >
                    {label}
                  </button>
                )
              })}
            </div>

            <div className="h-6 w-px bg-border mx-1" />

            {/* 自定义日期 */}
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={dateRange.start_date}
                onChange={(e) =>
                  setDateRange((prev) => ({ ...prev, start_date: e.target.value }))
                }
                className="rounded-md border border-input bg-background px-3 py-1.5 text-sm w-36"
              />
              <span className="text-muted-foreground">~</span>
              <input
                type="date"
                value={dateRange.end_date}
                onChange={(e) =>
                  setDateRange((prev) => ({ ...prev, end_date: e.target.value }))
                }
                className="rounded-md border border-input bg-background px-3 py-1.5 text-sm w-36"
              />
            </div>

            <div className="h-6 w-px bg-border mx-1" />

            {/* 数据范围提示 */}
            <div className="text-sm text-muted-foreground">
              可选范围: {selectedSymbol.first_candle_time?.slice(0, 10) ?? '-'} ~ {selectedSymbol.last_candle_time?.slice(0, 10) ?? '-'}
            </div>
          </div>
        </div>

        {/* Stats */}
        {klineStats && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <StatsCard
              title="最新价"
              value={klineStats.latest.toFixed(4)}
              variant="compact"
            />
            <StatsCard
              title="区间涨跌"
              value={`${klineStats.change >= 0 ? '+' : ''}${klineStats.change.toFixed(2)}%`}
              valueColor={klineStats.change >= 0 ? 'success' : 'destructive'}
              icon={klineStats.change >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
              variant="compact"
            />
            <StatsCard
              title="最高价"
              value={klineStats.high.toFixed(4)}
              variant="compact"
            />
            <StatsCard
              title="最低价"
              value={klineStats.low.toFixed(4)}
              variant="compact"
            />
            <StatsCard
              title="数据点数"
              value={klineStats.dataPoints}
              variant="compact"
            />
          </div>
        )}

        {/* Chart */}
        <div className="rounded-lg border bg-card p-6">
          <h3 className="mb-4 font-semibold">{selectedSymbol.symbol} K线图</h3>
          {klineLoading ? (
            <div className="flex h-[400px] items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : klineData.length === 0 ? (
            <div className="flex h-[400px] items-center justify-center text-muted-foreground">
              暂无数据
            </div>
          ) : (
            <KlineChart data={klineData} height={400} showVolume={true} />
          )}
        </div>

        {/* Data Table with Pagination */}
        {klineData.length > 0 && (
          <div className="rounded-lg border bg-card">
            <div className="flex items-center justify-between border-b px-6 py-4">
              <h3 className="font-semibold">数据明细</h3>
              <div className="flex items-center gap-4">
                <span className="text-sm text-muted-foreground">
                  共 {klineData.length} 条
                </span>
                <SearchableSelect
                  options={PAGE_SIZE_SELECT_OPTIONS}
                  value={String(detailPageSize)}
                  onChange={(value) => {
                    setDetailPageSize(Number(value))
                    setDetailPage(1)
                  }}
                  className="w-28"
                />
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm" style={{ minWidth: '1200px' }}>
                <thead className="sticky top-0 bg-card z-10">
                  <tr className="border-b bg-muted/50">
                    <th className="px-3 py-2 text-left font-medium whitespace-nowrap">时间</th>
                    <th className="px-3 py-2 text-right font-medium whitespace-nowrap">开盘</th>
                    <th className="px-3 py-2 text-right font-medium whitespace-nowrap">最高</th>
                    <th className="px-3 py-2 text-right font-medium whitespace-nowrap">最低</th>
                    <th className="px-3 py-2 text-right font-medium whitespace-nowrap">收盘</th>
                    <th className="px-3 py-2 text-right font-medium whitespace-nowrap">成交量</th>
                    <th className="px-3 py-2 text-right font-medium whitespace-nowrap">成交额</th>
                    <th className="px-3 py-2 text-right font-medium whitespace-nowrap">成交笔数</th>
                    <th className="px-3 py-2 text-right font-medium whitespace-nowrap">主动买量</th>
                    <th className="px-3 py-2 text-right font-medium whitespace-nowrap">主动买额</th>
                    {viewDataType === 'swap' && (
                      <th className="px-3 py-2 text-right font-medium whitespace-nowrap">资金费率</th>
                    )}
                    <th className="px-3 py-2 text-right font-medium whitespace-nowrap">1m均价</th>
                    <th className="px-3 py-2 text-right font-medium whitespace-nowrap">5m均价</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {paginatedKlineData.map((row, i) => (
                    <tr key={i} className="hover:bg-muted/50 transition-colors">
                      <td className="px-3 py-2 whitespace-nowrap">{row.time}</td>
                      <td className="px-3 py-2 text-right">{row.open.toFixed(4)}</td>
                      <td className="px-3 py-2 text-right">{row.high.toFixed(4)}</td>
                      <td className="px-3 py-2 text-right">{row.low.toFixed(4)}</td>
                      <td className="px-3 py-2 text-right">{row.close.toFixed(4)}</td>
                      <td className="px-3 py-2 text-right">{row.volume.toFixed(2)}</td>
                      <td className="px-3 py-2 text-right">
                        {row.quote_volume?.toFixed(2) ?? '-'}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {row.trade_num ?? '-'}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {row.taker_buy_base_asset_volume?.toFixed(2) ?? '-'}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {row.taker_buy_quote_asset_volume?.toFixed(2) ?? '-'}
                      </td>
                      {viewDataType === 'swap' && (
                        <td className="px-3 py-2 text-right">
                          {row.funding_fee != null ? `${(row.funding_fee * 100).toFixed(4)}%` : '-'}
                        </td>
                      )}
                      <td className="px-3 py-2 text-right">
                        {row.avg_price_1m?.toFixed(4) ?? '-'}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {row.avg_price_5m?.toFixed(4) ?? '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Pagination */}
            {detailTotalPages > 1 && (
              <div className="flex items-center justify-between border-t px-6 py-3">
                <div className="text-sm text-muted-foreground">
                  第 {(detailPage - 1) * detailPageSize + 1} - {Math.min(detailPage * detailPageSize, klineData.length)} 条
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setDetailPage(1)}
                    disabled={detailPage === 1}
                    className="rounded-md p-1 hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronsLeft className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setDetailPage(p => Math.max(1, p - 1))}
                    disabled={detailPage === 1}
                    className="rounded-md p-1 hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <span className="text-sm px-2">
                    {detailPage} / {detailTotalPages}
                  </span>
                  <button
                    onClick={() => setDetailPage(p => Math.min(detailTotalPages, p + 1))}
                    disabled={detailPage === detailTotalPages}
                    className="rounded-md p-1 hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setDetailPage(detailTotalPages)}
                    disabled={detailPage === detailTotalPages}
                    className="rounded-md p-1 hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronsRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  // 如果 URL 有参数但数据还在加载，显示加载状态
  if (selectedSymbolName && symbolsLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // 默认展示概览和列表
  return (
    <div className="space-y-6">
      {/* Overall Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <StatsCard
          title="币种总数"
          value={overview?.total_symbols ?? 0}
          icon={<Coins className="h-5 w-5" />}
        />
        <StatsCard
          title="总数据记录"
          value={(
            (overview?.spot?.total_records ?? 0) + (overview?.swap?.total_records ?? 0)
          ).toLocaleString()}
          icon={<Database className="h-5 w-5" />}
        />
        <StatsCard
          title="数据截止日期"
          value={overview?.swap?.data_end_date?.slice(0, 10) ?? '-'}
          icon={<Calendar className="h-5 w-5" />}
        />
      </div>

      {/* Spot & Swap Stats */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Spot Stats */}
        <div className="rounded-lg border bg-card p-6 shadow-depth-1">
          <h3 className="mb-4 font-semibold text-warning">现货数据</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">币种数</p>
              <p className="text-2xl font-bold">{overview?.spot?.total_symbols ?? 0}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">K线记录</p>
              <p className="text-2xl font-bold">
                {overview?.spot?.total_records?.toLocaleString() ?? 0}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">开始日期</p>
              <p className="text-lg font-medium">
                {overview?.spot?.data_start_date ?? '-'}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">截止日期</p>
              <p className="text-lg font-medium">
                {overview?.spot?.data_end_date ?? '-'}
              </p>
            </div>
          </div>
        </div>

        {/* Swap Stats */}
        <div className="rounded-lg border bg-card p-6 shadow-depth-1">
          <h3 className="mb-4 font-semibold text-info">合约数据</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">币种数</p>
              <p className="text-2xl font-bold">{overview?.swap?.total_symbols ?? 0}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">K线记录</p>
              <p className="text-2xl font-bold">
                {overview?.swap?.total_records?.toLocaleString() ?? 0}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">开始日期</p>
              <p className="text-lg font-medium">
                {overview?.swap?.data_start_date ?? '-'}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">截止日期</p>
              <p className="text-lg font-medium">
                {overview?.swap?.data_end_date ?? '-'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Symbols List */}
      <div className="rounded-lg border bg-card">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b px-6 py-4">
          <h3 className="font-semibold">币种列表</h3>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <SearchableSelect
                options={FILTER_TYPE_OPTIONS}
                value={filterType}
                onChange={(value) => handleFilterChange(value as 'all' | 'spot' | 'swap')}
                className="w-28"
              />
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="搜索币种..."
                value={searchQuery}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="w-48 rounded-md border border-input bg-background pl-9 pr-3 py-2 text-sm"
              />
            </div>
            <SearchableSelect
              options={PAGE_SIZE_SELECT_OPTIONS}
              value={String(pageSize)}
              onChange={(value) => handlePageSizeChange(Number(value))}
              className="w-28"
            />
            <button
              onClick={() => refetch()}
              className="rounded-md p-2 hover:bg-accent"
              title="刷新"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>

        {symbolsLoading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : filteredAndSortedSymbols.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-muted-foreground">
            暂无数据
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full" style={{ minWidth: '800px' }}>
              <thead className="sticky top-0 bg-card z-10">
                <tr className="border-b bg-muted/50">
                  <th
                    className="px-4 py-3 text-left text-sm font-medium cursor-pointer hover:bg-muted"
                    onClick={() => handleSort('symbol')}
                  >
                    <div className="flex items-center gap-2">
                      币种
                      {renderSortIcon('symbol')}
                    </div>
                  </th>
                  <th
                    className="px-4 py-3 text-center text-sm font-medium cursor-pointer hover:bg-muted"
                    onClick={() => handleSort('type')}
                  >
                    <div className="flex items-center justify-center gap-2">
                      类型
                      {renderSortIcon('type')}
                    </div>
                  </th>
                  <th
                    className="px-4 py-3 text-left text-sm font-medium cursor-pointer hover:bg-muted"
                    onClick={() => handleSort('first_candle_time')}
                  >
                    <div className="flex items-center gap-2">
                      上线时间
                      {renderSortIcon('first_candle_time')}
                    </div>
                  </th>
                  <th
                    className="px-4 py-3 text-left text-sm font-medium cursor-pointer hover:bg-muted"
                    onClick={() => handleSort('last_candle_time')}
                  >
                    <div className="flex items-center gap-2">
                      最新数据
                      {renderSortIcon('last_candle_time')}
                    </div>
                  </th>
                  <th
                    className="px-4 py-3 text-right text-sm font-medium cursor-pointer hover:bg-muted"
                    onClick={() => handleSort('kline_count')}
                  >
                    <div className="flex items-center justify-end gap-2">
                      K线数量
                      {renderSortIcon('kline_count')}
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {paginatedSymbols.map((symbol, index) => (
                  <tr
                    key={`${symbol.symbol}-${index}`}
                    className="hover:bg-muted/50 transition-colors cursor-pointer"
                    onClick={() => handleSymbolClick(symbol)}
                  >
                    <td className="px-4 py-3 font-medium text-primary hover:underline">
                      {symbol.symbol}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex justify-center gap-1">
                        {symbol.has_spot && (
                          <span className="rounded-full px-2 py-0.5 text-xs font-medium bg-warning-muted text-warning">
                            现货
                          </span>
                        )}
                        {symbol.has_swap && (
                          <span className="rounded-full px-2 py-0.5 text-xs font-medium bg-info-muted text-info">
                            合约
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground whitespace-nowrap">
                      {symbol.first_candle_time?.slice(0, 10) ?? '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground whitespace-nowrap">
                      {symbol.last_candle_time?.slice(0, 10) ?? '-'}
                    </td>
                    <td className="px-4 py-3 text-right text-sm">
                      {symbol.kline_count?.toLocaleString() ?? '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-t px-6 py-3">
          <div className="text-sm text-muted-foreground">
            共 {filteredAndSortedSymbols.length} 条记录
            {filterType !== 'all' && ` (${filterType === 'spot' ? '现货' : '合约'})`}
            {searchQuery && ` (搜索: ${searchQuery})`}
          </div>
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                className="rounded-md p-1 hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                title="首页"
              >
                <ChevronsLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="rounded-md p-1 hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                title="上一页"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm px-2">
                第 {currentPage} / {totalPages} 页
              </span>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="rounded-md p-1 hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                title="下一页"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
              <button
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
                className="rounded-md p-1 hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                title="末页"
              >
                <ChevronsRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Last Updated */}
      {overview?.last_updated && (
        <p className="text-sm text-muted-foreground">
          最后更新: {new Date(overview.last_updated).toLocaleString()}
        </p>
      )}
    </div>
  )
}
