/**
 * Factor Analysis Page - Single Factor Tab
 * 因子分析页 - 单因子分析 Tab 组件
 */

import { useState, useMemo } from 'react'
import { Loader2, Play, BarChart3 } from 'lucide-react'
import { useFactors } from '@/features/factor'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'
import { stripPyExtension } from '@/lib/utils'
import {
  ICTimeSeries,
  GroupReturnChart,
  DistributionChart,
} from '@/components/charts'
import type { SingleAnalysisResult } from './types'
import { generateMockICData } from './utils'

export function SingleFactorTab() {
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
          <div className="text-center">
            <BarChart3 className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-2 text-muted-foreground">选择因子后点击"开始分析"</p>
          </div>
        </div>
      )}
    </div>
  )
}
