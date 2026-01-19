/**
 * Factor Analysis Page - Calculator Tab
 * 因子分析页 - 因子计算器 Tab 组件
 */

import { useState, useMemo, useEffect, useCallback } from 'react'
import {
  Loader2,
  Play,
  Plus,
  X,
  Calculator,
} from 'lucide-react'
import { useFactors } from '@/features/factor'
import { useSymbols, useFactorCalculation } from '@/features/data'
import type { FactorParamResult } from '@/features/data'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'
import { stripPyExtension } from '@/lib/utils'
import { LineChart } from '@/components/charts'
import type { FactorConfig, CalculationResult } from './types'

export function CalculatorTab() {
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

  const handleCalculate = useCallback(async () => {
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
        for (const paramResult of apiResult.results as FactorParamResult[]) {
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
  }, [selectedSymbol, factorConfigs, dataType, dateRange, factorCalculation])

  // 页面加载时自动计算默认因子
  useEffect(() => {
    if (!hasAutoCalculated && !symbolsLoading && symbols.length > 0 && factors.length > 0) {
      setHasAutoCalculated(true)
      handleCalculate()
    }
  }, [symbolsLoading, symbols.length, factors.length, hasAutoCalculated, handleCalculate])

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
