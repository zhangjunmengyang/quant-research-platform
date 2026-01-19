/**
 * Factor Analysis Page - Grouping Tab
 * 因子分析页 - 因子分箱 Tab 组件
 */

import { useState, useMemo } from 'react'
import {
  Loader2,
  Play,
  Plus,
  X,
  Layers,
} from 'lucide-react'
import { useFactors, useFactorGroupAnalysis } from '@/features/factor'
import type { FactorGroupAnalysisRequest, FactorGroupAnalysisResponse, DataType, BinMethod } from '@/features/factor'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'
import { stripPyExtension } from '@/lib/utils'
import { BaseChart } from '@/components/charts'
import type { EChartsOption } from 'echarts'
import type { FactorGroupConfig } from './types'

export function GroupingTab() {
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
                          ...result.labels.map((label) => ({
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
