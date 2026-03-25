/**
 * 双因子分析页 — 热力图 + 风格暴露
 */

import { useState, useMemo } from 'react'
import {
  BarChart3, Play, FileText, ChevronDown, ChevronUp,
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { BaseChart } from '@/components/charts/BaseChart'

import {
  useStockHubStatus,
  useDualAnalysis,
  useCachedFactors,
  useAvailableBacktests,
} from '@/features/stock-hub'
import type { DualAnalysisData, HeatmapData } from '@/features/stock-hub'
import { StockHubNotConfigured } from './StockHubNotConfigured'

// ===== 预设 =====

const PERIOD_PRESETS = [
  { label: '5日单offset', value: ['5_0'], desc: '仅5_0' },
  { label: '5日全offset', value: ['5_0', '5_1', '5_2', '5_3', '5_4'], desc: '5_0~5_4' },
  { label: '周度单offset', value: ['W_0'], desc: '仅W_0' },
]

const REBALANCE_OPTIONS = [
  { label: '0930', value: '0930' },
  { label: '0955', value: '0955' },
  { label: '1000', value: '1000' },
  { label: '收盘', value: 'close' },
]

// ===== 热力图组件 =====

function HeatmapChart({ data, title }: { data: HeatmapData; title: string }) {
  const option = useMemo(() => {
    const flatValues = data.values.flat()
    const min = Math.min(...flatValues)
    const max = Math.max(...flatValues)

    const seriesData: [number, number, number][] = []
    for (let i = 0; i < data.index.length; i++) {
      for (let j = 0; j < data.columns.length; j++) {
        seriesData.push([j, i, data.values[i]?.[j] ?? 0])
      }
    }

    return {
      title: { text: title, left: 'center', textStyle: { fontSize: 13 } },
      tooltip: {
        position: 'top' as const,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        formatter: (p: any) => {
          const arr = p.data as number[]
          const col = arr[0] ?? 0
          const row = arr[1] ?? 0
          const val = arr[2] ?? 0
          return `${data.index[row] ?? ''} × ${data.columns[col] ?? ''}: ${val.toFixed(3)}`
        },
      },
      grid: { left: '12%', right: '12%', bottom: '15%', top: '15%' },
      xAxis: {
        type: 'category' as const,
        data: data.columns,
        splitArea: { show: true },
        axisLabel: { fontSize: 10 },
      },
      yAxis: {
        type: 'category' as const,
        data: data.index,
        splitArea: { show: true },
        axisLabel: { fontSize: 10 },
      },
      visualMap: {
        min, max,
        calculable: true,
        orient: 'horizontal' as const,
        left: 'center',
        bottom: '0%',
        inRange: {
          color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026'],
        },
        textStyle: { fontSize: 10 },
      },
      series: [{
        type: 'heatmap' as const,
        data: seriesData,
        label: {
          show: data.columns.length <= 6,
          fontSize: 9,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter: (p: any) => ((p.data as number[])[2] ?? 0).toFixed(2),
        },
      }],
    }
  }, [data, title])

  return <BaseChart option={option} style={{ height: '350px' }} />
}

// ===== 三柱图（风格暴露） =====

function DualStyleChart({ data, title }: { data: DualAnalysisData['style_exposure']; title: string }) {
  const option = useMemo(() => {
    const styles = Object.keys(data)
    const mainVals = styles.map(s => data[s]?.main ?? 0)
    const subVals = styles.map(s => data[s]?.sub ?? 0)
    const dualVals = styles.map(s => data[s]?.dual ?? 0)

    return {
      title: { text: title, left: 'center', textStyle: { fontSize: 13 } },
      tooltip: { trigger: 'axis' as const },
      legend: { data: ['主因子', '次因子', '双因子'], bottom: 0, textStyle: { fontSize: 10 } },
      grid: { left: '10%', right: '4%', bottom: '15%', top: '15%' },
      xAxis: { type: 'category' as const, data: styles, axisLabel: { fontSize: 10, rotate: 20 } },
      yAxis: { type: 'value' as const, min: -1, max: 1 },
      series: [
        { name: '主因子', type: 'bar' as const, data: mainVals, itemStyle: { color: '#3b82f6' } },
        { name: '次因子', type: 'bar' as const, data: subVals, itemStyle: { color: '#f59e0b' } },
        { name: '双因子', type: 'bar' as const, data: dualVals, itemStyle: { color: '#10b981' } },
      ],
    }
  }, [data, title])

  return <BaseChart option={option} style={{ height: '300px' }} />
}

// ===== 因子选择器 =====

function FactorPicker({
  label,
  value,
  onChange,
  factors,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  factors: string[]
}) {
  const [search, setSearch] = useState('')
  const filtered = search
    ? factors.filter(f => f.toLowerCase().includes(search.toLowerCase()))
    : factors

  return (
    <div className="space-y-1">
      <label className="block text-xs text-muted-foreground">{label}</label>
      <input
        type="text"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="搜索..."
        className="h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
      />
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
        size={5}
      >
        {filtered.map(f => (
          <option key={f} value={f}>{f}</option>
        ))}
      </select>
    </div>
  )
}

// ===== 主页面 =====

export function Component() {
  const { data: status } = useStockHubStatus()
  const { data: backtestData } = useAvailableBacktests()
  const backtests = backtestData?.backtests ?? []
  const [backtestName, setBacktestName] = useState<string>('')

  const { data: cachedData } = useCachedFactors(backtestName || undefined)
  const factors = cachedData?.factors ?? []

  const [mainFactor, setMainFactor] = useState('')
  const [subFactor, setSubFactor] = useState('')
  const [periodIdx, setPeriodIdx] = useState(0)
  const [rebalanceTime, setRebalanceTime] = useState('0955')
  const [bins, setBins] = useState(5)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showReport, setShowReport] = useState(false)

  const dualMutation = useDualAnalysis()
  const result = dualMutation.data as DualAnalysisData | undefined

  // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
  const preset = PERIOD_PRESETS[periodIdx]!

  const handleAnalyze = () => {
    if (!mainFactor || !subFactor) return
    dualMutation.mutate({
      main_factor: mainFactor,
      sub_factor: subFactor,
      period_offset_list: preset.value,
      rebalance_time: rebalanceTime,
      bins,
      ...(backtestName ? { backtest_name: backtestName } : {}),
    })
    setShowReport(false)
  }

  if (status && !status.available) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">双因子分析</h1>
        <StockHubNotConfigured status={status} />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">双因子分析</h1>

      {/* 配置区 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BarChart3 className="h-4 w-4" />
            双因子配置
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* 回测数据源 */}
          <div>
            <label className="block text-xs text-muted-foreground mb-1">回测数据源</label>
            <select
              value={backtestName}
              onChange={(e) => { setBacktestName(e.target.value); setMainFactor(''); setSubFactor('') }}
              className="h-8 w-full max-w-md rounded-md border border-input bg-background px-2 text-xs"
            >
              <option value="">默认（框架config.py）</option>
              {backtests.map((bt) => (
                <option key={bt.name} value={bt.name}>
                  {bt.name}（{bt.factor_count}因子，{bt.modified_time}）
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-3 gap-4">
            {/* 主因子 */}
            <FactorPicker
              label={`主因子 (${factors.length})`}
              value={mainFactor}
              onChange={setMainFactor}
              factors={factors}
            />
            {/* 次因子 */}
            <FactorPicker
              label="次因子"
              value={subFactor}
              onChange={setSubFactor}
              factors={factors}
            />
            {/* 参数 */}
            <div className="space-y-2">
              <div>
                <label className="block text-xs text-muted-foreground mb-1">分析周期</label>
                <div className="flex flex-wrap gap-1">
                  {PERIOD_PRESETS.map((p, i) => (
                    <Button
                      key={p.label}
                      variant={periodIdx === i ? 'default' : 'outline'}
                      size="sm"
                      className="text-xs"
                      onClick={() => setPeriodIdx(i)}
                    >
                      {p.label}
                    </Button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">换仓时间</label>
                <div className="flex flex-wrap gap-1">
                  {REBALANCE_OPTIONS.map(opt => (
                    <Button
                      key={opt.value}
                      variant={rebalanceTime === opt.value ? 'default' : 'outline'}
                      size="sm"
                      className="text-xs"
                      onClick={() => setRebalanceTime(opt.value)}
                    >
                      {opt.label}
                    </Button>
                  ))}
                </div>
              </div>
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                {showAdvanced ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                高级选项
              </button>
              {showAdvanced && (
                <div>
                  <label className="block text-xs text-muted-foreground">分组数</label>
                  <input
                    type="number"
                    value={bins}
                    onChange={e => setBins(Number(e.target.value))}
                    className="h-7 w-16 rounded-md border border-input bg-background px-2 text-xs"
                    min={2} max={10}
                  />
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              onClick={handleAnalyze}
              loading={dualMutation.isPending}
              disabled={!mainFactor || !subFactor || mainFactor === subFactor}
              className="gap-1"
            >
              <Play className="h-4 w-4" />
              开始双因子分析
            </Button>
            {mainFactor && subFactor && (
              <span className="text-xs text-muted-foreground">
                主: {mainFactor} | 次: {subFactor} | {preset.desc} | {rebalanceTime}
              </span>
            )}
            {mainFactor === subFactor && mainFactor && (
              <Badge variant="destructive" className="text-xs">主次因子不能相同</Badge>
            )}
            {dualMutation.isError && (
              <Badge variant="destructive" className="text-xs">
                {(dualMutation.error as Error).message}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 结果 */}
      {result && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Badge variant="outline">{result.main_factor}</Badge>
            <span>×</span>
            <Badge variant="outline">{result.sub_factor}</Badge>
            <span>{result.start_date} ~ {result.end_date}</span>
            <span>| 耗时: {result.elapsed_seconds}s</span>
          </div>

          {/* 4个热力图 */}
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardContent className="p-2">
                <HeatmapChart data={result.mix_nv} title="组合日均收益(‰)" />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-2">
                <HeatmapChart data={result.mix_prop} title="组合平均占比(%)" />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-2">
                <HeatmapChart data={result.filter_nv_ms} title={`过滤: ${result.main_factor}→${result.sub_factor}`} />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-2">
                <HeatmapChart data={result.filter_nv_sm} title={`过滤: ${result.sub_factor}→${result.main_factor}`} />
              </CardContent>
            </Card>
          </div>

          {/* 风格暴露 */}
          <Card>
            <CardContent className="p-2">
              <DualStyleChart data={result.style_exposure} title="双因子风格暴露" />
            </CardContent>
          </Card>

          {/* HTML报告 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4" />
                完整报告
                <div className="ml-auto flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowReport(!showReport)}
                    className="text-xs gap-1"
                  >
                    {showReport ? '收起' : '展开'}
                    {showReport ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            {showReport && result.html_path && (
              <CardContent className="p-0">
                <p className="px-4 py-2 text-xs text-muted-foreground">
                  报告路径: {result.html_path}
                </p>
              </CardContent>
            )}
          </Card>
        </div>
      )}

      {/* 空状态 */}
      {!result && !dualMutation.isPending && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <BarChart3 className="mx-auto h-12 w-12 mb-3 text-muted-foreground/30" />
            <p>选择主因子和次因子，配置参数后点击"开始双因子分析"</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
