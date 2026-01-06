/**
 * Factor Analysis Page
 * 因子分析页 - 包含因子计算、单因子分析、多因子分析、因子分箱四个 Tab
 */

import { useState, useMemo, useEffect } from 'react'
import {
  BarChart3,
  GitCompare,
  Loader2,
  Play,
  Plus,
  X,
  Calculator,
  Layers,
} from 'lucide-react'
import { cn, stripPyExtension } from '@/lib/utils'
import { useFactors, useFactorStyles, useFactorGroupAnalysis } from '@/features/factor'
import type { FactorGroupAnalysisRequest, FactorGroupAnalysisResponse, DataType, BinMethod } from '@/features/factor'
import { useSymbols, useFactorCalculation } from '@/features/data'
import type { FactorCalcResult, FactorParamResult } from '@/features/data'
import {
  ICTimeSeries,
  GroupReturnChart,
  DistributionChart,
  CorrelationMatrix,
  BarChart,
  LineChart,
  BaseChart,
} from '@/components/charts'
import type { EChartsOption } from 'echarts'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'

type TabType = 'calculator' | 'single' | 'multi' | 'grouping'

export function Component() {
  const [activeTab, setActiveTab] = useState<TabType>('calculator')

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex items-center gap-4 border-b">
        <button
          onClick={() => setActiveTab('calculator')}
          className={cn(
            'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'calculator'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <Calculator className="h-4 w-4" />
          因子计算
        </button>
        <button
          onClick={() => setActiveTab('single')}
          className={cn(
            'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'single'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <BarChart3 className="h-4 w-4" />
          单因子分析
        </button>
        <button
          onClick={() => setActiveTab('multi')}
          className={cn(
            'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'multi'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <GitCompare className="h-4 w-4" />
          多因子分析
        </button>
        <button
          onClick={() => setActiveTab('grouping')}
          className={cn(
            'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'grouping'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <Layers className="h-4 w-4" />
          因子分箱
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'calculator' && <CalculatorTab />}
      {activeTab === 'single' && <SingleFactorTab />}
      {activeTab === 'multi' && <MultiFactorTab />}
      {activeTab === 'grouping' && <GroupingTab />}
    </div>
  )
}

// ============================================================================
// 因子计算 Tab
// ============================================================================

interface FactorConfig {
  id: string
  factor: string
  params: number[]
}

interface CalculationResult {
  symbol: string
  data_type: string
  factors: Array<{
    name: string
    param: number
    data: Array<{ time: string; value: number | null }>
    stats: {
      count?: number
      mean?: number | null
      std?: number | null
      min?: number | null
      max?: number | null
      latest?: number | null
    }
  }>
}

function CalculatorTab() {
  const { data: symbols = [], isLoading: symbolsLoading } = useSymbols()
  const { data: factorsData } = useFactors({ page_size: 1000 })
  const factors = factorsData?.items || []
  const factorCalculation = useFactorCalculation()

  const [selectedSymbol, setSelectedSymbol] = useState('BTC-USDT')
  const [dataType, setDataType] = useState<'spot' | 'swap'>('swap')
  const [factorConfigs, setFactorConfigs] = useState<FactorConfig[]>([
    { id: '1', factor: 'Bias.py', params: [20] },
  ])
  const [result, setResult] = useState<CalculationResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  // 日期范围状态 - 默认最近1个月
  const [dateRange, setDateRange] = useState(() => {
    const end = new Date()
    const start = new Date()
    start.setMonth(start.getMonth() - 1)
    return {
      start_date: start.toISOString().slice(0, 10),
      end_date: end.toISOString().slice(0, 10),
    }
  })

  // 转换为 SearchableSelect 选项
  const symbolOptions: SelectOption[] = useMemo(
    () =>
      symbols.map((s) => ({
        value: s.symbol,
        label: s.symbol,
        description: `${s.has_spot ? '现货' : ''}${s.has_spot && s.has_swap ? ' / ' : ''}${s.has_swap ? '合约' : ''}`,
      })),
    [symbols]
  )

  const factorOptions: SelectOption[] = useMemo(
    () =>
      [...factors]
        .sort((a, b) => stripPyExtension(a.filename).localeCompare(stripPyExtension(b.filename)))
        .map((f) => ({
          value: f.filename,
          label: stripPyExtension(f.filename),
        })),
    [factors]
  )

  const handleAddFactor = () => {
    setFactorConfigs([
      ...factorConfigs,
      {
        id: Date.now().toString(),
        factor: '',
        params: [20],
      },
    ])
  }

  const handleRemoveFactor = (id: string) => {
    setFactorConfigs(factorConfigs.filter((f) => f.id !== id))
  }

  const handleUpdateFactor = (id: string, updates: Partial<FactorConfig>) => {
    setFactorConfigs(
      factorConfigs.map((f) => (f.id === id ? { ...f, ...updates } : f))
    )
  }

  // 页面加载时自动计算默认因子
  const [hasAutoCalculated, setHasAutoCalculated] = useState(false)

  const handleCalculate = async () => {
    if (!selectedSymbol || factorConfigs.length === 0) return

    const validConfigs = factorConfigs.filter((f) => f.factor)
    if (validConfigs.length === 0) return

    setError(null)

    // 为每个因子配置调用 API
    const allResults: CalculationResult['factors'] = []

    for (const config of validConfigs) {
      try {
        const factorName = stripPyExtension(config.factor)
        const apiResult = await factorCalculation.mutateAsync({
          symbol: selectedSymbol,
          factor_name: factorName,
          params: config.params,
          data_type: dataType,
          start_date: dateRange.start_date,
          end_date: dateRange.end_date,
          limit: 10000,  // 增加限制以适应更长的时间范围
        })

        // 转换 API 结果为内部格式
        for (const paramResult of apiResult.results) {
          allResults.push({
            name: factorName,
            param: paramResult.param,
            data: paramResult.data.map((d) => ({
              time: d.time.slice(0, 10),  // 截取日期部分
              value: d.value,
            })),
            stats: paramResult.stats,
          })
        }
      } catch (err) {
        setError(`因子 ${config.factor} 计算失败: ${(err as Error).message}`)
        return
      }
    }

    setResult({
      symbol: selectedSymbol,
      data_type: dataType,
      factors: allResults,
    })
  }

  // 页面加载时自动计算默认因子
  useEffect(() => {
    if (!hasAutoCalculated && !symbolsLoading && symbols.length > 0 && factors.length > 0) {
      setHasAutoCalculated(true)
      handleCalculate()
    }
  }, [symbolsLoading, symbols.length, factors.length, hasAutoCalculated])

  // Generate chart series
  const chartSeries = useMemo(() => {
    if (!result) return []
    return result.factors.map((f) => ({
      name: `${f.name}(${f.param})`,
      data: f.data.filter((d) => d.value !== null) as Array<{ time: string; value: number }>,
    }))
  }, [result])

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 font-semibold">计算配置</h3>

        <div className="space-y-4">
          {/* Symbol and Data Type Selection */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-sm font-medium">选择币种</label>
              <SearchableSelect
                options={symbolOptions}
                value={selectedSymbol}
                onChange={setSelectedSymbol}
                placeholder="请选择币种"
                searchPlaceholder="搜索币种..."
                disabled={symbolsLoading}
                clearable
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">数据类型</label>
              <SearchableSelect
                options={[
                  { value: 'swap', label: '合约 (swap)' },
                  { value: 'spot', label: '现货 (spot)' },
                ]}
                value={dataType}
                onChange={(v) => setDataType(v as 'spot' | 'swap')}
                placeholder="选择数据类型"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">开始日期</label>
              <input
                type="date"
                value={dateRange.start_date}
                onChange={(e) =>
                  setDateRange((prev) => ({ ...prev, start_date: e.target.value }))
                }
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">结束日期</label>
              <input
                type="date"
                value={dateRange.end_date}
                onChange={(e) =>
                  setDateRange((prev) => ({ ...prev, end_date: e.target.value }))
                }
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
          </div>

          {/* Factor Configs */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-sm font-medium">因子配置</label>
              <button
                onClick={handleAddFactor}
                className="flex items-center gap-1 rounded-md border px-2 py-1 text-sm hover:bg-accent"
              >
                <Plus className="h-4 w-4" />
                添加因子
              </button>
            </div>

            {factorConfigs.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                请点击"添加因子"配置要计算的因子
              </p>
            ) : (
              <div className="space-y-2">
                {factorConfigs.map((config) => (
                  <div
                    key={config.id}
                    className="flex items-center gap-4 rounded border p-3"
                  >
                    <div className="flex-1">
                      <SearchableSelect
                        options={factorOptions}
                        value={config.factor}
                        onChange={(v) => handleUpdateFactor(config.id, { factor: v })}
                        placeholder="选择因子"
                        searchPlaceholder="搜索因子..."
                        maxHeight={400}
                      />
                    </div>

                    <div className="flex items-center gap-2">
                      <label className="text-sm text-muted-foreground">参数:</label>
                      <input
                        type="text"
                        value={config.params.join(',')}
                        onChange={(e) =>
                          handleUpdateFactor(config.id, {
                            params: e.target.value
                              .split(',')
                              .map((v) => parseInt(v.trim()))
                              .filter((v) => !isNaN(v)),
                          })
                        }
                        className="w-24 rounded-md border border-input bg-background px-2 py-1 text-sm"
                        placeholder="20"
                      />
                    </div>

                    <button
                      onClick={() => handleRemoveFactor(config.id)}
                      className="rounded p-1 text-red-600 hover:bg-red-100"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Calculate Button */}
          <div className="flex justify-end">
            <button
              onClick={handleCalculate}
              disabled={
                !selectedSymbol ||
                factorConfigs.filter((f) => f.factor).length === 0 ||
                factorCalculation.isPending
              }
              className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {factorCalculation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  计算中...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  计算因子
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-600">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Statistics */}
          <div className="rounded-lg border bg-card">
            <div className="border-b px-6 py-4">
              <h3 className="font-semibold">
                计算结果 - {result.symbol} ({result.data_type})
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                时间范围: {dateRange.start_date} ~ {dateRange.end_date}
              </p>
            </div>
            <div className="overflow-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left text-sm font-medium">因子</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">参数</th>
                    <th className="px-4 py-3 text-center text-sm font-medium">数据点</th>
                    <th className="px-4 py-3 text-center text-sm font-medium">最新值</th>
                    <th className="px-4 py-3 text-center text-sm font-medium">均值</th>
                    <th className="px-4 py-3 text-center text-sm font-medium">标准差</th>
                    <th className="px-4 py-3 text-center text-sm font-medium">最小值</th>
                    <th className="px-4 py-3 text-center text-sm font-medium">最大值</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {result.factors.map((f, i) => (
                    <tr key={i} className="hover:bg-muted/50">
                      <td className="px-4 py-3 font-medium">{f.name}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {f.param}
                      </td>
                      <td className="px-4 py-3 text-center text-muted-foreground">
                        {f.stats.count ?? '-'}
                      </td>
                      <td className="px-4 py-3 text-center font-medium">
                        {f.stats.latest != null ? f.stats.latest.toFixed(4) : '-'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {f.stats.mean != null ? f.stats.mean.toFixed(4) : '-'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {f.stats.std != null ? f.stats.std.toFixed(4) : '-'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {f.stats.min != null ? f.stats.min.toFixed(4) : '-'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {f.stats.max != null ? f.stats.max.toFixed(4) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Chart */}
          <div className="rounded-lg border bg-card p-6">
            <h3 className="mb-4 font-semibold">因子时序图</h3>
            <LineChart
              series={chartSeries}
              height={400}
              yAxisName="因子值"
              showDataZoom
            />
          </div>

          {/* Factor Comparison */}
          {result.factors.length > 1 && (
            <div className="rounded-lg border bg-card p-6">
              <h3 className="mb-4 font-semibold">因子分位数对比</h3>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {result.factors.map((f, i) => {
                  const latestValue = f.stats.latest ?? 0
                  const minVal = f.stats.min ?? 0
                  const maxVal = f.stats.max ?? 0
                  const range = maxVal - minVal
                  const percentile = range > 0
                    ? ((latestValue - minVal) / range) * 100
                    : 50

                  return (
                    <div key={i} className="rounded-lg border p-4">
                      <h4 className="font-medium mb-2">
                        {f.name}({f.param})
                      </h4>
                      <div className="mb-2">
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-muted-foreground">当前分位</span>
                          <span className="font-medium">{percentile.toFixed(1)}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full bg-primary transition-all"
                            style={{ width: `${Math.min(100, Math.max(0, percentile))}%` }}
                          />
                        </div>
                      </div>
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>最低: {minVal.toFixed(2)}</span>
                        <span>最高: {maxVal.toFixed(2)}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!result && !factorCalculation.isPending && (
        <div className="flex h-64 items-center justify-center rounded-lg border bg-card">
          <div className="text-center">
            <Calculator className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-2 text-muted-foreground">
              配置币种和因子后点击"计算因子"
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// 单因子分析 Tab
// ============================================================================

interface SingleAnalysisResult {
  ic: Array<{ time: string; ic: number; rankIC?: number }>
  groupReturns: {
    groups: string[]
    returns: number[]
  }
  distribution: {
    bins: string[]
    counts: number[]
  }
  stats: {
    ic_mean: number
    ic_std: number
    ic_ir: number
    rank_ic_mean: number
    positive_ratio: number
  }
}

function SingleFactorTab() {
  const { data: factorsData } = useFactors({ page_size: 1000 })

  const [selectedFactor, setSelectedFactor] = useState('')
  const [params, setParams] = useState<number[]>([20])
  const [analysisResult, setAnalysisResult] = useState<SingleAnalysisResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const factors = factorsData?.items || []

  const factorOptions: SelectOption[] = useMemo(
    () =>
      [...factors]
        .sort((a, b) => stripPyExtension(a.filename).localeCompare(stripPyExtension(b.filename)))
        .map((f) => ({
          value: f.filename,
          label: stripPyExtension(f.filename),
        })),
    [factors]
  )

  const handleAnalyze = async () => {
    if (!selectedFactor) return

    setIsLoading(true)
    // Simulate API call - in production, this would call the actual analysis API
    setTimeout(() => {
      setAnalysisResult({
        ic: generateMockICData(),
        groupReturns: {
          groups: ['Q1 (低)', 'Q2', 'Q3', 'Q4', 'Q5 (高)'],
          returns: [-2.5, -0.8, 0.3, 1.2, 3.1],
        },
        distribution: {
          bins: ['<-2', '-2~-1', '-1~0', '0~1', '1~2', '>2'],
          counts: [45, 120, 280, 290, 110, 35],
        },
        stats: {
          ic_mean: 0.052,
          ic_std: 0.12,
          ic_ir: 0.43,
          rank_ic_mean: 0.048,
          positive_ratio: 0.62,
        },
      })
      setIsLoading(false)
    }, 1500)
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 font-semibold">分析配置</h3>
        <div className="flex flex-wrap items-end gap-4">
          <div className="min-w-[250px]">
            <label className="mb-1 block text-sm font-medium">选择因子</label>
            <SearchableSelect
              options={factorOptions}
              value={selectedFactor}
              onChange={setSelectedFactor}
              placeholder="请选择因子"
              searchPlaceholder="搜索因子..."
              maxHeight={400}
            />
          </div>

          <div className="min-w-[120px]">
            <label className="mb-1 block text-sm font-medium">参数</label>
            <input
              type="text"
              value={params.join(',')}
              onChange={(e) =>
                setParams(
                  e.target.value
                    .split(',')
                    .map((v) => parseInt(v.trim()))
                    .filter((v) => !isNaN(v))
                )
              }
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="20"
            />
          </div>

          <button
            onClick={handleAnalyze}
            disabled={!selectedFactor || isLoading}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                分析中...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                开始分析
              </>
            )}
          </button>
        </div>
      </div>

      {/* Results */}
      {analysisResult && (
        <>
          {/* Stats Summary */}
          <div className="grid gap-4 md:grid-cols-5">
            <div className="rounded-lg border bg-card p-4">
              <p className="text-sm text-muted-foreground">IC 均值</p>
              <p className="text-xl font-semibold">{analysisResult.stats.ic_mean.toFixed(4)}</p>
            </div>
            <div className="rounded-lg border bg-card p-4">
              <p className="text-sm text-muted-foreground">IC 标准差</p>
              <p className="text-xl font-semibold">{analysisResult.stats.ic_std.toFixed(4)}</p>
            </div>
            <div className="rounded-lg border bg-card p-4">
              <p className="text-sm text-muted-foreground">IC IR</p>
              <p className="text-xl font-semibold">{analysisResult.stats.ic_ir.toFixed(4)}</p>
            </div>
            <div className="rounded-lg border bg-card p-4">
              <p className="text-sm text-muted-foreground">Rank IC 均值</p>
              <p className="text-xl font-semibold">{analysisResult.stats.rank_ic_mean.toFixed(4)}</p>
            </div>
            <div className="rounded-lg border bg-card p-4">
              <p className="text-sm text-muted-foreground">IC 正比例</p>
              <p className="text-xl font-semibold">
                {(analysisResult.stats.positive_ratio * 100).toFixed(1)}%
              </p>
            </div>
          </div>

          {/* Charts */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* IC Time Series */}
            <div className="rounded-lg border bg-card p-6">
              <ICTimeSeries data={analysisResult.ic} title="IC 时序" height={300} />
            </div>

            {/* Group Returns */}
            <div className="rounded-lg border bg-card p-6">
              <GroupReturnChart
                groups={analysisResult.groupReturns.groups}
                returns={analysisResult.groupReturns.returns}
                title="分组收益"
                height={300}
              />
            </div>
          </div>

          {/* Distribution */}
          <div className="rounded-lg border bg-card p-6">
            <DistributionChart
              bins={analysisResult.distribution.bins}
              counts={analysisResult.distribution.counts}
              title="因子值分布"
              height={250}
            />
          </div>
        </>
      )}

      {/* Empty State */}
      {!analysisResult && !isLoading && (
        <div className="flex h-64 items-center justify-center rounded-lg border bg-card">
          <p className="text-muted-foreground">选择因子后点击"开始分析"</p>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// 多因子分析 Tab
// ============================================================================

function MultiFactorTab() {
  const { data: factorsData } = useFactors({ page_size: 1000 })
  const factors = factorsData?.items || []

  const [selectedFactors, setSelectedFactors] = useState<string[]>([])
  const [correlationData, setCorrelationData] = useState<number[][] | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [factorToAdd, setFactorToAdd] = useState('')

  // 可选因子（排除已选）
  const availableFactorOptions: SelectOption[] = useMemo(
    () =>
      [...factors]
        .filter((f) => !selectedFactors.includes(f.filename))
        .sort((a, b) => stripPyExtension(a.filename).localeCompare(stripPyExtension(b.filename)))
        .map((f) => ({
          value: f.filename,
          label: stripPyExtension(f.filename),
        })),
    [factors, selectedFactors]
  )

  const handleAddFactor = (factor: string) => {
    if (!selectedFactors.includes(factor) && selectedFactors.length < 10) {
      setSelectedFactors([...selectedFactors, factor])
    }
  }

  const handleRemoveFactor = (factor: string) => {
    setSelectedFactors(selectedFactors.filter((f) => f !== factor))
  }

  const handleAnalyze = () => {
    if (selectedFactors.length < 2) return

    setIsLoading(true)
    // Simulate correlation matrix calculation
    setTimeout(() => {
      const n = selectedFactors.length
      const matrix: number[][] = []
      for (let i = 0; i < n; i++) {
        matrix[i] = []
        for (let j = 0; j < n; j++) {
          if (i === j) {
            matrix[i][j] = 1
          } else if (j < i) {
            matrix[i][j] = matrix[j][i]
          } else {
            matrix[i][j] = Math.random() * 1.6 - 0.8
          }
        }
      }
      setCorrelationData(matrix)
      setIsLoading(false)
    }, 1000)
  }

  return (
    <div className="space-y-6">
      {/* Factor Selection */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 font-semibold">选择因子 (最多10个)</h3>

        {/* Selected Factors */}
        <div className="mb-4 flex flex-wrap gap-2">
          {selectedFactors.length === 0 ? (
            <p className="text-sm text-muted-foreground">请从下方添加因子</p>
          ) : (
            selectedFactors.map((factor) => (
              <span
                key={factor}
                className="flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1 text-sm"
              >
                {stripPyExtension(factor)}
                <button
                  onClick={() => handleRemoveFactor(factor)}
                  className="ml-1 rounded-full p-0.5 hover:bg-primary/20"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))
          )}
        </div>

        {/* Add Factor */}
        <div className="flex items-center gap-4">
          <SearchableSelect
            options={availableFactorOptions}
            value={factorToAdd}
            onChange={(value) => {
              if (value) {
                handleAddFactor(value)
                setFactorToAdd('')
              }
            }}
            placeholder="添加因子..."
            searchPlaceholder="搜索因子..."
            emptyText="无匹配因子"
            disabled={selectedFactors.length >= 10}
            className="flex-1"
          />

          <button
            onClick={handleAnalyze}
            disabled={selectedFactors.length < 2 || isLoading}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                计算中...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                计算相关性
              </>
            )}
          </button>
        </div>
      </div>

      {/* Correlation Matrix */}
      {correlationData && (
        <div className="rounded-lg border bg-card p-6">
          <CorrelationMatrix
            factors={selectedFactors.map(stripPyExtension)}
            correlations={correlationData}
            title="因子相关性矩阵"
            height={Math.max(400, selectedFactors.length * 50)}
          />
        </div>
      )}

      {/* Statistics Table */}
      {correlationData && (
        <div className="rounded-lg border bg-card">
          <div className="border-b px-6 py-4">
            <h3 className="font-semibold">相关性统计</h3>
          </div>
          <div className="overflow-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-3 text-left text-sm font-medium">因子对</th>
                  <th className="px-4 py-3 text-center text-sm font-medium">相关系数</th>
                  <th className="px-4 py-3 text-center text-sm font-medium">相关强度</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {getCorrelationPairs(selectedFactors, correlationData)
                  .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
                  .map((pair, i) => (
                    <tr key={i} className="hover:bg-muted/50">
                      <td className="px-4 py-3 text-sm">
                        {stripPyExtension(pair.factor1)} - {stripPyExtension(pair.factor2)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={pair.value > 0 ? 'text-red-600' : 'text-blue-600'}>
                          {pair.value.toFixed(4)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`rounded-full px-2 py-1 text-xs font-medium ${getCorrelationStrengthClass(
                            pair.value
                          )}`}
                        >
                          {getCorrelationStrength(pair.value)}
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!correlationData && !isLoading && (
        <div className="flex h-64 items-center justify-center rounded-lg border bg-card">
          <p className="text-muted-foreground">
            {selectedFactors.length < 2
              ? '请至少选择2个因子进行分析'
              : '点击"计算相关性"开始分析'}
          </p>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Helper Functions
// ============================================================================

function generateMockICData() {
  const data: Array<{ time: string; ic: number; rankIC: number }> = []
  const startDate = new Date('2023-01-01')

  for (let i = 0; i < 52; i++) {
    const date = new Date(startDate)
    date.setDate(date.getDate() + i * 7)
    data.push({
      time: date.toISOString().slice(0, 10),
      ic: (Math.random() - 0.4) * 0.3,
      rankIC: (Math.random() - 0.4) * 0.25,
    })
  }

  return data
}

function getCorrelationPairs(factors: string[], matrix: number[][]) {
  const pairs: Array<{ factor1: string; factor2: string; value: number }> = []
  for (let i = 0; i < factors.length; i++) {
    for (let j = i + 1; j < factors.length; j++) {
      pairs.push({
        factor1: factors[i],
        factor2: factors[j],
        value: matrix[i][j],
      })
    }
  }
  return pairs
}

function getCorrelationStrength(value: number): string {
  const abs = Math.abs(value)
  if (abs >= 0.8) return '非常强'
  if (abs >= 0.6) return '强'
  if (abs >= 0.4) return '中等'
  if (abs >= 0.2) return '弱'
  return '非常弱'
}

function getCorrelationStrengthClass(value: number): string {
  const abs = Math.abs(value)
  if (abs >= 0.8) return 'bg-red-100 text-red-800'
  if (abs >= 0.6) return 'bg-orange-100 text-orange-800'
  if (abs >= 0.4) return 'bg-yellow-100 text-yellow-800'
  if (abs >= 0.2) return 'bg-green-100 text-green-800'
  return 'bg-gray-100 text-gray-600'
}

// ============================================================================
// 因子分箱 Tab
// ============================================================================

interface FactorGroupConfig {
  id: string
  factor: string
  params: number[]
}

function GroupingTab() {
  const { data: factorsData } = useFactors({ page_size: 1000 })
  const factors = factorsData?.items || []
  const groupAnalysis = useFactorGroupAnalysis()

  const [factorConfigs, setFactorConfigs] = useState<FactorGroupConfig[]>([])
  const [dataType, setDataType] = useState<DataType>('swap')
  const [bins, setBins] = useState(5)
  const [method, setMethod] = useState<BinMethod>('pct')
  const [results, setResults] = useState<FactorGroupAnalysisResponse[]>([])

  // 数据类型选项
  const dataTypeOptions: SelectOption[] = useMemo(
    () => [
      { value: 'swap', label: '合约' },
      { value: 'spot', label: '现货' },
      { value: 'all', label: '全部' },
    ],
    []
  )

  // 分箱方法选项
  const methodOptions: SelectOption[] = useMemo(
    () => [
      { value: 'pct', label: '分位数 (等频)' },
      { value: 'val', label: '等宽' },
    ],
    []
  )

  // 因子选项
  const factorOptions: SelectOption[] = useMemo(
    () =>
      [...factors]
        .sort((a, b) => stripPyExtension(a.filename).localeCompare(stripPyExtension(b.filename)))
        .map((f) => ({
          value: f.filename,
          label: stripPyExtension(f.filename),
        })),
    [factors]
  )

  const handleAddFactor = () => {
    setFactorConfigs([
      ...factorConfigs,
      {
        id: Date.now().toString(),
        factor: '',
        params: [20],
      },
    ])
  }

  const handleRemoveFactor = (id: string) => {
    setFactorConfigs(factorConfigs.filter((f) => f.id !== id))
  }

  const handleUpdateFactor = (id: string, updates: Partial<FactorGroupConfig>) => {
    setFactorConfigs(
      factorConfigs.map((f) => (f.id === id ? { ...f, ...updates } : f))
    )
  }

  const handleAnalyze = () => {
    const validConfigs = factorConfigs.filter((f) => f.factor)
    if (validConfigs.length === 0) return

    // Build factor_dict from configs (去掉 .py 后缀)
    const factor_dict: Record<string, number[]> = {}
    for (const config of validConfigs) {
      factor_dict[stripPyExtension(config.factor)] = config.params
    }

    const request: FactorGroupAnalysisRequest = {
      factor_dict,
      data_type: dataType,
      bins,
      method,
    }

    groupAnalysis.mutate(request, {
      onSuccess: (data) => {
        setResults(data)
      },
    })
  }

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 font-semibold">分箱分析配置</h3>

        <div className="space-y-4">
          {/* Global Settings */}
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm font-medium">数据类型</label>
              <SearchableSelect
                options={dataTypeOptions}
                value={dataType}
                onChange={(value) => setDataType(value as DataType)}
                placeholder="选择数据类型"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">分组数量</label>
              <input
                type="number"
                value={bins}
                onChange={(e) => setBins(Math.max(2, Math.min(20, parseInt(e.target.value) || 5)))}
                min={2}
                max={20}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">分箱方法</label>
              <SearchableSelect
                options={methodOptions}
                value={method}
                onChange={(value) => setMethod(value as BinMethod)}
                placeholder="选择方法"
              />
            </div>
          </div>

          {/* Factor Configs */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-sm font-medium">因子配置</label>
              <button
                onClick={handleAddFactor}
                className="flex items-center gap-1 rounded-md border px-2 py-1 text-sm hover:bg-accent"
              >
                <Plus className="h-4 w-4" />
                添加因子
              </button>
            </div>

            {factorConfigs.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                请点击"添加因子"配置要分析的因子
              </p>
            ) : (
              <div className="space-y-2">
                {factorConfigs.map((config) => (
                  <div
                    key={config.id}
                    className="flex items-center gap-4 rounded border p-3"
                  >
                    <SearchableSelect
                      options={factorOptions}
                      value={config.factor}
                      onChange={(value) =>
                        handleUpdateFactor(config.id, { factor: value })
                      }
                      placeholder="选择因子"
                      searchPlaceholder="搜索因子..."
                      emptyText="无匹配因子"
                      className="flex-1"
                    />

                    <div className="flex items-center gap-2">
                      <label className="text-sm text-muted-foreground">参数:</label>
                      <input
                        type="text"
                        value={config.params.join(',')}
                        onChange={(e) =>
                          handleUpdateFactor(config.id, {
                            params: e.target.value
                              .split(',')
                              .map((v) => parseInt(v.trim()))
                              .filter((v) => !isNaN(v)),
                          })
                        }
                        className="w-24 rounded-md border border-input bg-background px-2 py-1 text-sm"
                        placeholder="20"
                      />
                    </div>

                    <button
                      onClick={() => handleRemoveFactor(config.id)}
                      className="rounded p-1 text-red-600 hover:bg-red-100"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Analyze Button */}
          <div className="flex justify-end">
            <button
              onClick={handleAnalyze}
              disabled={
                factorConfigs.filter((f) => f.factor).length === 0 ||
                groupAnalysis.isPending
              }
              className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {groupAnalysis.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  分析中...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  开始分析
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {groupAnalysis.isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-600">
          分析失败: {(groupAnalysis.error as Error)?.message}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-6">
          <h3 className="font-semibold">分析结果</h3>
          {results.map((result, i) => (
            <div key={i} className="rounded-lg border bg-card p-4">
              <h4 className="mb-4 font-medium">{result.factor_name}</h4>
              {result.error ? (
                <p className="text-sm text-red-600">{result.error}</p>
              ) : (
                <div className="grid gap-4 lg:grid-cols-2">
                  {/* Bar Chart - 分组净值柱状图 */}
                  <div>
                    <h5 className="mb-2 text-sm font-medium text-muted-foreground">分组净值</h5>
                    <BaseChart
                      style={{ height: '300px' }}
                      option={{
                        tooltip: {
                          trigger: 'axis',
                          axisPointer: { type: 'shadow' }
                        },
                        xAxis: {
                          type: 'category',
                          data: result.bar_data.map(d => d.group),
                          axisLabel: { rotate: 45 }
                        },
                        yAxis: {
                          type: 'value',
                          name: 'NAV'
                        },
                        series: [{
                          type: 'bar',
                          data: result.bar_data.map(d => ({
                            value: d.nav,
                            itemStyle: {
                              color: d.group === 'long_short_nav' ? '#10b981' :
                                     d.label === 'Min Value' ? '#ef4444' :
                                     d.label === 'Max Value' ? '#3b82f6' : '#6b7280'
                            }
                          })),
                          label: {
                            show: true,
                            position: 'top',
                            formatter: (params: { value: number }) => params.value.toFixed(2)
                          }
                        }]
                      } as EChartsOption}
                    />
                  </div>

                  {/* Line Chart - 分组净值曲线 */}
                  <div>
                    <h5 className="mb-2 text-sm font-medium text-muted-foreground">净值曲线</h5>
                    <BaseChart
                      style={{ height: '300px' }}
                      option={{
                        tooltip: {
                          trigger: 'axis'
                        },
                        legend: {
                          data: [...result.labels, ...(result.data_type !== 'spot' ? ['long_short_nav'] : [])],
                          top: 0
                        },
                        grid: {
                          top: 40,
                          bottom: 60
                        },
                        xAxis: {
                          type: 'category',
                          data: result.curve_data.map(d => d.date),
                          axisLabel: { rotate: 45 }
                        },
                        yAxis: {
                          type: 'log',
                          name: 'NAV (log)'
                        },
                        series: [
                          ...result.labels.map((label, idx) => ({
                            name: label,
                            type: 'line' as const,
                            data: result.curve_data.map(d => d.values[label] || 0),
                            smooth: true,
                            showSymbol: false
                          })),
                          ...(result.data_type !== 'spot' ? [{
                            name: 'long_short_nav',
                            type: 'line' as const,
                            data: result.curve_data.map(d => d.values['long_short_nav'] || 0),
                            smooth: true,
                            showSymbol: false,
                            lineStyle: { width: 2, type: 'dashed' as const }
                          }] : [])
                        ]
                      } as EChartsOption}
                    />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {results.length === 0 && !groupAnalysis.isPending && (
        <div className="flex h-64 items-center justify-center rounded-lg border bg-card">
          <div className="text-center">
            <Layers className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-2 text-muted-foreground">
              配置因子后点击"开始分析"进行分箱分析
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
