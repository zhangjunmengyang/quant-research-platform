/**
 * Stock Hub - 单因子IC分析页
 *
 * 图表样式复刻自原框架 pfunctions.py（plotly），
 * 使用 ECharts 实现一致的视觉风格。
 */

import { useCallback, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Play, Brain, Save, ChevronDown, ChevronRight, Edit3, Settings } from 'lucide-react'
import { PromptEditor } from '@/components/stock-hub/PromptEditor'
import {
  useStockStatus,
  useAvailableBacktests,
  useCachedFactors,
  useEnhancedAnalysis,
  useAccumulatedEvaluations,
  PERIOD_PRESETS,
  REBALANCE_TIMES,
  stockApi,
} from '@/features/stock-hub'
import type { EvaluationType, AnalysisResult } from '@/features/stock-hub'
import { BaseChart, echarts } from '@/components/charts'
import { BarChart as EBarChart } from 'echarts/charts'
import { LineChart as ELineChart } from 'echarts/charts'
import { HeatmapChart as EHeatmapChart } from 'echarts/charts'
import { VisualMapComponent, MarkLineComponent } from 'echarts/components'
import type { EChartsOption } from 'echarts'

echarts.use([EBarChart, ELineChart, EHeatmapChart, VisualMapComponent, MarkLineComponent])

// ─── 原工具通用样式常量 ───
const TITLE_STYLE = { color: 'green', fontSize: 20, fontWeight: 500 as const }
const WHITE_BG = 'rgb(255, 255, 255)'

/** 复刻 pfunctions.py 的 float_num_process：保留有效位 */
function fmtNum(v: number): string {
  if (v === 0) return '0'
  const abs = Math.abs(v)
  if (abs >= 1) return v.toFixed(2)
  // 小数：保留 2 位有效非零数字
  const s = abs.toFixed(5)
  let nonZero = 0
  let cut = s.length
  for (let i = 2; i < s.length; i++) {
    if (s[i] !== '0') nonZero++
    if (nonZero >= 2) { cut = i + 1; break }
  }
  return (v < 0 ? '-' : '') + parseFloat(s.slice(0, cut)).toString()
}

// ─── 1. 因子RankIC图（orange 柱 + blue 累计折线，双 Y 轴） ───
function ICSeriesChart({ result }: { result: AnalysisResult }) {
  const series = result.ic_series
  if (!series?.length) return null

  const option = useMemo<EChartsOption>(() => {
    const dates = series.map((d) => d.date)
    const rankIC = series.map((d) => d.rank_ic)
    const cumRankIC = series.map((d) => d.cum_rank_ic)
    return {
      backgroundColor: WHITE_BG,
      title: { text: '因子RankIC图', left: 'center', textStyle: TITLE_STYLE },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: 'rgba(255,255,255,0.5)',
      },
      legend: {
        data: ['RankIC', '累计RankIC'],
        right: 20,
        top: 10,
        backgroundColor: 'white',
        borderColor: 'gray',
        borderWidth: 1,
        padding: [5, 10],
      },
      grid: { left: '8%', right: '8%', top: '18%', bottom: '12%' },
      xAxis: { type: 'category', data: dates, boundaryGap: true },
      yAxis: [
        { type: 'value', name: 'RankIC', splitLine: { lineStyle: { type: 'dashed' } } },
        { type: 'value', name: '累计RankIC' },
      ],
      ...(result.ic_summary ? {
        graphic: [{
          type: 'text',
          left: '10%',
          top: '13%',
          style: { text: result.ic_summary, fontSize: 14, fill: '#333' },
        }],
      } : {}),
      series: [
        {
          name: 'RankIC',
          type: 'bar',
          data: rankIC,
          itemStyle: { color: 'orange' },
          label: { show: false },
        },
        {
          name: '累计RankIC',
          type: 'line',
          yAxisIndex: 1,
          data: cumRankIC,
          smooth: false,
          showSymbol: true,
          symbolSize: 4,
          lineStyle: { color: 'blue', width: 2 },
          itemStyle: { color: 'blue' },
        },
      ],
    }
  }, [series, result.ic_summary])

  return (
    <div className="rounded-lg border p-4">
      <BaseChart option={option} style={{ height: 400 }} />
    </div>
  )
}

// ─── 2. RankIC热力图（green → yellow → red） ───
function ICHeatmapChart({ result }: { result: AnalysisResult }) {
  const heatmap = result.ic_heatmap
  if (!heatmap) return null

  const option = useMemo<EChartsOption>(() => {
    const data: [number, number, number | null][] = []
    let minVal = 0, maxVal = 0
    heatmap.years.forEach((_, yi) => {
      heatmap.months.forEach((_, mi) => {
        const v = heatmap.values[yi]?.[mi]
        if (v != null) {
          data.push([mi, yi, v])
          if (v < minVal) minVal = v
          if (v > maxVal) maxVal = v
        } else {
          data.push([mi, yi, null])
        }
      })
    })
    const absMax = Math.max(Math.abs(minVal), Math.abs(maxVal), 0.1)

    return {
      backgroundColor: WHITE_BG,
      title: { text: 'RankIC热力图(行：年份，列：月份)', left: 'center', textStyle: TITLE_STYLE },
      tooltip: {
        formatter: (params: unknown) => {
          const p = params as { data: [number, number, number | null] }
          const [mi, yi, v] = p.data
          return `${heatmap.years[yi]} - ${heatmap.months[mi]}月<br/>RankIC: ${v != null ? fmtNum(v) : '-'}`
        },
      },
      grid: { left: '12%', right: '15%', top: '15%', bottom: '10%' },
      xAxis: {
        type: 'category',
        data: heatmap.months.map((m) => `${m}月`),
        splitArea: { show: true },
      },
      yAxis: {
        type: 'category',
        data: heatmap.years,
        splitArea: { show: true },
      },
      visualMap: {
        min: -absMax,
        max: absMax,
        calculable: true,
        orient: 'vertical',
        right: '2%',
        top: 'center',
        inRange: { color: ['green', 'yellow', 'red'] },
      },
      series: [{
        type: 'heatmap',
        data,
        label: {
          show: true,
          formatter: (params: unknown) => {
            const p = params as { data: [number, number, number | null] }
            return p.data[2] != null ? fmtNum(p.data[2]) : ''
          },
          fontSize: 11,
        },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
      }],
    }
  }, [heatmap])

  return (
    <div className="rounded-lg border p-4">
      <BaseChart option={option} style={{ height: Math.max(250, heatmap.years.length * 45 + 120) }} />
    </div>
  )
}

// ─── 3. 分组资金曲线（多空净值: red + dotted, 右Y轴） ───
function GroupNavChart({ result }: { result: AnalysisResult }) {
  const nav = result.group_nav
  if (!nav?.length) return null

  const option = useMemo<EChartsOption>(() => {
    const dates = nav.map((d) => d.date as string)
    const allKeys = Object.keys(nav[0] ?? {}).filter((k) => k !== 'date')
    const groupKeys = allKeys.filter((k) => !k.includes('多空'))
    const lsKey = allKeys.find((k) => k.includes('多空'))

    const seriesList: EChartsOption['series'] = groupKeys.map((k) => ({
      name: k,
      type: 'line' as const,
      data: nav.map((d) => d[k] as number),
      smooth: false,
      showSymbol: false,
      lineStyle: { width: 2 },
    }))

    if (lsKey) {
      seriesList.push({
        name: lsKey,
        type: 'line' as const,
        yAxisIndex: 1,
        data: nav.map((d) => d[lsKey] as number),
        smooth: false,
        showSymbol: false,
        lineStyle: { color: 'red', width: 2, type: 'dotted' },
        itemStyle: { color: 'red' },
      })
    }

    return {
      backgroundColor: WHITE_BG,
      title: { text: '分组资金曲线', left: 'center', textStyle: TITLE_STYLE },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255,255,255,0.5)',
      },
      legend: {
        data: [...groupKeys, ...(lsKey ? [lsKey] : [])],
        right: 20,
        top: 10,
        backgroundColor: 'white',
        borderColor: 'gray',
        borderWidth: 1,
        padding: [5, 10],
        type: 'scroll',
      },
      grid: { left: '8%', right: '8%', top: '18%', bottom: '15%' },
      xAxis: { type: 'category', data: dates, boundaryGap: false },
      yAxis: [
        { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
        ...(lsKey ? [{ type: 'value' as const, name: lsKey }] : []),
      ],
      dataZoom: nav.length > 50 ? [
        { type: 'inside', start: 0, end: 100 },
        { show: true, type: 'slider', bottom: '3%', height: 20 },
      ] : undefined,
      series: seriesList,
    }
  }, [nav])

  return (
    <div className="rounded-lg border p-4">
      <BaseChart option={option} style={{ height: 400 }} />
    </div>
  )
}

// ─── 4. 分组净值（柱状图 + 值标签） ───
function GroupReturnSection({ result }: { result: AnalysisResult }) {
  const gv = result.group_values
  if (!gv || Object.keys(gv).length === 0) return null

  const option = useMemo<EChartsOption>(() => {
    const groups = Object.keys(gv)
    const values = Object.values(gv)
    return {
      backgroundColor: WHITE_BG,
      title: { text: '分组净值', left: 'center', textStyle: TITLE_STYLE },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '8%', right: '4%', top: '18%', bottom: '10%', containLabel: true },
      xAxis: { type: 'category', data: groups, axisLabel: { rotate: groups.length > 8 ? 30 : 0 } },
      yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
      series: [{
        type: 'bar',
        data: values,
        label: {
          show: true,
          position: 'top',
          formatter: (p: unknown) => fmtNum((p as { value: number }).value),
          fontSize: 11,
        },
      }],
    }
  }, [gv])

  return (
    <div className="rounded-lg border p-4">
      <BaseChart option={option} style={{ height: 350 }} />
    </div>
  )
}

// ─── 5. 分组持仓走势 ───
function GroupHoldingChart({ result }: { result: AnalysisResult }) {
  const holding = result.group_holding
  if (!holding?.length) return null

  const option = useMemo<EChartsOption>(() => {
    const times = holding.map((d) => String(d.time))
    const keys = Object.keys(holding[0] ?? {}).filter((k) => k !== 'time')

    return {
      backgroundColor: WHITE_BG,
      title: { text: '分组持仓走势', left: 'center', textStyle: TITLE_STYLE },
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.5)' },
      legend: {
        data: keys,
        right: 20,
        top: 10,
        backgroundColor: 'white',
        borderColor: 'gray',
        borderWidth: 1,
        padding: [5, 10],
        type: 'scroll',
      },
      grid: { left: '8%', right: '4%', top: '18%', bottom: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        data: times,
        boundaryGap: false,
        axisTick: { alignWithLabel: true },
      },
      yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
      series: keys.map((k) => ({
        name: k,
        type: 'line' as const,
        data: holding.map((d) => d[k] as number),
        smooth: false,
        showSymbol: false,
        lineStyle: { width: 2 },
      })),
    }
  }, [holding])

  return (
    <div className="rounded-lg border p-4">
      <BaseChart option={option} style={{ height: 350 }} />
    </div>
  )
}

// ─── 6. 因子风格暴露图（Y 轴 [-1, 1]，值标签） ───
function StyleExposureChart({ result }: { result: AnalysisResult }) {
  const se = result.style_exposure
  if (!se || Object.keys(se).length === 0) return null

  const option = useMemo<EChartsOption>(() => {
    const styles = Object.keys(se)
    const values = Object.values(se)
    return {
      backgroundColor: WHITE_BG,
      title: { text: '因子风格暴露图', left: 'center', textStyle: TITLE_STYLE },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '8%', right: '4%', top: '18%', bottom: '10%', containLabel: true },
      xAxis: { type: 'category', data: styles },
      yAxis: {
        type: 'value',
        min: -1,
        max: 1,
        splitLine: { lineStyle: { type: 'dashed' } },
      },
      series: [{
        type: 'bar',
        data: values,
        label: {
          show: true,
          position: 'top',
          formatter: (p: unknown) => fmtNum((p as { value: number }).value),
          fontSize: 11,
        },
      }],
    }
  }, [se])

  return (
    <div className="rounded-lg border p-4">
      <BaseChart option={option} style={{ height: 350 }} />
    </div>
  )
}

// ─── 7. 行业分析（RankIC 柱 + 占比双柱 red/green） ───
function IndustryICCharts({ result }: { result: AnalysisResult }) {
  const data = result.industry_ic
  if (!data?.length) return null

  const icOption = useMemo<EChartsOption>(() => {
    const names = data.map((d) => d.name)
    return {
      backgroundColor: WHITE_BG,
      title: { text: '行业RankIC图', left: 'center', textStyle: TITLE_STYLE },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '8%', right: '4%', top: '18%', bottom: '15%', containLabel: true },
      xAxis: { type: 'category', data: names, axisLabel: { rotate: 45, fontSize: 11 } },
      yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
      series: [{
        type: 'bar',
        data: data.map((d) => d.rank_ic),
        label: {
          show: true,
          position: 'top',
          formatter: (p: unknown) => fmtNum((p as { value: number }).value),
          fontSize: 10,
        },
      }],
    }
  }, [data])

  const pctOption = useMemo<EChartsOption>(() => {
    const names = data.map((d) => d.name)
    return {
      backgroundColor: WHITE_BG,
      title: { text: '行业占比（可能会受到行业股票数量的影响）', left: 'center', textStyle: TITLE_STYLE },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: {
        data: ['因子第一组占比', '因子最后一组占比'],
        right: 20,
        top: 10,
        backgroundColor: 'white',
        borderColor: 'gray',
        borderWidth: 1,
      },
      grid: { left: '8%', right: '4%', top: '18%', bottom: '15%', containLabel: true },
      xAxis: { type: 'category', data: names, axisLabel: { rotate: 45, fontSize: 11 } },
      yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
      series: [
        {
          name: '因子第一组占比',
          type: 'bar',
          data: data.map((d) => d.top_pct),
          itemStyle: { color: 'red' },
          label: {
            show: true,
            position: 'top',
            formatter: (p: unknown) => fmtNum((p as { value: number }).value),
            fontSize: 10,
          },
        },
        {
          name: '因子最后一组占比',
          type: 'bar',
          data: data.map((d) => d.bottom_pct),
          itemStyle: { color: 'green' },
          label: {
            show: true,
            position: 'top',
            formatter: (p: unknown) => fmtNum((p as { value: number }).value),
            fontSize: 10,
          },
        },
      ],
    }
  }, [data])

  return (
    <>
      <div className="rounded-lg border p-4">
        <BaseChart option={icOption} style={{ height: 400 }} />
      </div>
      <div className="rounded-lg border p-4">
        <BaseChart option={pctOption} style={{ height: 400 }} />
      </div>
    </>
  )
}

// ─── 8. 市值分组分析（RankIC 柱 + 占比双柱 red/green + info） ───
function MarketCapICCharts({ result }: { result: AnalysisResult }) {
  const data = result.market_cap_ic
  if (!data?.length) return null

  const bins = data.length

  const icOption = useMemo<EChartsOption>(() => {
    const labels = data.map((d) => String(d.group))
    return {
      backgroundColor: WHITE_BG,
      title: { text: '市值分组RankIC', left: 'center', textStyle: TITLE_STYLE },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '8%', right: '4%', top: '18%', bottom: '10%', containLabel: true },
      xAxis: { type: 'category', data: labels },
      yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
      series: [{
        type: 'bar',
        data: data.map((d) => d.rank_ic),
        label: {
          show: true,
          position: 'top',
          formatter: (p: unknown) => fmtNum((p as { value: number }).value),
          fontSize: 11,
        },
      }],
    }
  }, [data])

  const pctOption = useMemo<EChartsOption>(() => {
    const labels = data.map((d) => String(d.group))
    return {
      backgroundColor: WHITE_BG,
      title: { text: '市值占比', left: 'center', textStyle: TITLE_STYLE },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: {
        data: ['因子第一组占比', '因子最后一组占比'],
        right: 20,
        top: 10,
        backgroundColor: 'white',
        borderColor: 'gray',
        borderWidth: 1,
      },
      graphic: [{
        type: 'text',
        left: '10%',
        top: '13%',
        style: {
          text: `1-${bins}代表市值从小到大分${bins}组`,
          fontSize: 16,
          fill: 'black',
        },
      }],
      grid: { left: '8%', right: '4%', top: '22%', bottom: '10%', containLabel: true },
      xAxis: { type: 'category', data: labels },
      yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
      series: [
        {
          name: '因子第一组占比',
          type: 'bar',
          data: data.map((d) => d.top_pct),
          itemStyle: { color: 'red' },
          label: {
            show: true,
            position: 'top',
            formatter: (p: unknown) => fmtNum((p as { value: number }).value),
            fontSize: 11,
          },
        },
        {
          name: '因子最后一组占比',
          type: 'bar',
          data: data.map((d) => d.bottom_pct),
          itemStyle: { color: 'green' },
          label: {
            show: true,
            position: 'top',
            formatter: (p: unknown) => fmtNum((p as { value: number }).value),
            fontSize: 11,
          },
        },
      ],
    }
  }, [data, bins])

  return (
    <>
      <div className="rounded-lg border p-4">
        <BaseChart option={icOption} style={{ height: 350 }} />
      </div>
      <div className="rounded-lg border p-4">
        <BaseChart option={pctOption} style={{ height: 350 }} />
      </div>
    </>
  )
}

// ─── 主组件 ───
export function Component() {
  const { t } = useTranslation()
  const { data: status, isLoading: statusLoading } = useStockStatus()
  const { data: backtestsData } = useAvailableBacktests()

  const [backtestName, setBacktestName] = useState<string>('')
  const [selectedFactor, setSelectedFactor] = useState('')
  const [periodPreset, setPeriodPreset] = useState<keyof typeof PERIOD_PRESETS>('5日单offset')
  const [rebalanceTime, setRebalanceTime] = useState('0955')
  const [bins, setBins] = useState(10)

  const { data: cachedFactors } = useCachedFactors(backtestName || undefined)
  const analysisTask = useEnhancedAnalysis()
  const evaluation = useAccumulatedEvaluations()
  const [expandedEvals, setExpandedEvals] = useState<Set<string>>(new Set())
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [editingPromptType, setEditingPromptType] = useState<EvaluationType | null>(null)

  const result = analysisTask.result

  const handleEvaluate = useCallback(
    (evalType: EvaluationType) => {
      if (!result) return
      evaluation.evaluate(evalType, result as AnalysisResult)
      // Auto-expand the eval section
      setExpandedEvals((prev) => new Set(prev).add(evalType))
    },
    [result, evaluation.evaluate],
  )

  const toggleExpand = useCallback((evalType: string) => {
    setExpandedEvals((prev) => {
      const next = new Set(prev)
      if (next.has(evalType)) next.delete(evalType)
      else next.add(evalType)
      return next
    })
  }, [])

  const handleSave = useCallback(async () => {
    if (!result) return
    setIsSaving(true)
    setSaveSuccess(false)
    try {
      await stockApi.saveEvaluation({
        factor_name: result.factor_name,
        title: `${result.factor_name} 评估 ${new Date().toLocaleDateString()}`,
        evaluations: evaluation.completedTexts,
        analysis_snapshot: result as unknown as Record<string, unknown>,
        tags: [],
      })
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err) {
      console.error('Save evaluation failed:', err)
    } finally {
      setIsSaving(false)
    }
  }, [result, evaluation.completedTexts])

  if (statusLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  if (!status?.analysis_ready) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4 text-muted-foreground">
        <p className="text-lg font-medium">{t('stockHub.notConfigured')}</p>
        <p className="text-sm">{t('stockHub.notConfiguredHint')}</p>
      </div>
    )
  }

  const backtests = backtestsData?.backtests ?? []
  const factors = cachedFactors ?? []

  const handleAnalysis = () => {
    if (!selectedFactor) return
    analysisTask.submit({
      factor_name: selectedFactor,
      period_offset_list: [...PERIOD_PRESETS[periodPreset]],
      rebalance_time: rebalanceTime,
      bins,
      backtest_name: backtestName || undefined,
    })
  }

  const isRunning = analysisTask.isSubmitting || analysisTask.isRunning

  const EVAL_BUTTONS: { type: EvaluationType; labelKey: string }[] = [
    { type: 'comprehensive', labelKey: 'stockHub.evalComprehensive' },
    { type: 'ic_performance', labelKey: 'stockHub.evalIcPerformance' },
    { type: 'grouping_ability', labelKey: 'stockHub.evalGroupingAbility' },
    { type: 'style_profile', labelKey: 'stockHub.evalStyleProfile' },
    { type: 'market_cap', labelKey: 'stockHub.evalMarketCap' },
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('stockHub.analysis')}</h1>

      {/* 配置区域 */}
      <div className="rounded-lg border p-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium">{t('stockHub.backtestSource')}</label>
            <select
              value={backtestName}
              onChange={(e) => { setBacktestName(e.target.value); setSelectedFactor('') }}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              <option value="">{t('stockHub.defaultSource')}</option>
              {backtests.map((bt) => (
                <option key={bt.name} value={bt.name}>
                  {bt.name} ({bt.factor_count}{t('stockHub.factorUnit')})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">{t('stockHub.selectFactor')}</label>
            <select
              value={selectedFactor}
              onChange={(e) => setSelectedFactor(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              <option value="">{t('stockHub.pleaseSelect')}</option>
              {factors.map((f) => (
                <option key={f.name} value={f.name}>{f.display_name || f.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="text-sm font-medium">{t('stockHub.periodPreset')}</label>
            <select
              value={periodPreset}
              onChange={(e) => setPeriodPreset(e.target.value as keyof typeof PERIOD_PRESETS)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              {Object.keys(PERIOD_PRESETS).map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">{t('stockHub.rebalanceTime')}</label>
            <select
              value={rebalanceTime}
              onChange={(e) => setRebalanceTime(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              {REBALANCE_TIMES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">{t('stockHub.groupCount')}</label>
            <input
              type="number"
              min={2}
              max={20}
              value={bins}
              onChange={(e) => setBins(Number(e.target.value))}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
            />
          </div>
        </div>

        <button
          onClick={handleAnalysis}
          disabled={!selectedFactor || isRunning}
          className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {t('stockHub.startAnalysis')}
        </button>

        {analysisTask.isRunning && (
          <p className="text-sm text-muted-foreground">{t('stockHub.analysisRunning')}</p>
        )}
        {analysisTask.error && (
          <p className="text-sm text-destructive">{analysisTask.error.message}</p>
        )}
      </div>

      {/* 结果展示 */}
      {result && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">{t('stockHub.analysisResult')}</h2>

          {/* 核心指标卡片 */}
          <div className="grid grid-cols-5 gap-3">
            {[
              { label: 'IC', value: result.ic_mean.toFixed(4) },
              { label: 'ICIR', value: result.icir.toFixed(4) },
              { label: '|ICIR|', value: result.abs_icir.toFixed(4) },
              { label: t('stockHub.icWinRate'), value: result.ic_ratio },
              { label: t('stockHub.factorScore'), value: result.score.toFixed(4) },
            ].map((item) => (
              <div key={item.label} className="rounded-lg border p-3 text-center">
                <div className="text-xs text-muted-foreground">{item.label}</div>
                <div className="mt-1 text-lg font-bold">{item.value}</div>
              </div>
            ))}
          </div>

          {/* 10 张图表，按原工具顺序 */}
          <ICSeriesChart result={result} />
          <ICHeatmapChart result={result} />
          <GroupNavChart result={result} />
          <GroupReturnSection result={result} />
          <GroupHoldingChart result={result} />
          <StyleExposureChart result={result} />
          <IndustryICCharts result={result} />
          <MarketCapICCharts result={result} />

          <p className="text-xs text-muted-foreground">
            {t('stockHub.elapsed', { seconds: result.elapsed_seconds })}
          </p>

          {/* AI 评估区 */}
          <div className="rounded-lg border p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4" />
                <h3 className="text-sm font-medium">{t('stockHub.aiEvaluation')}</h3>
              </div>
              <div className="flex items-center gap-2">
                {Object.keys(evaluation.completedTexts).length > 0 && (
                  <button
                    onClick={handleSave}
                    disabled={isSaving || evaluation.isAnyStreaming}
                    className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                  >
                    {isSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
                    {t('stockHub.saveToLibrary')}
                  </button>
                )}
              </div>
            </div>

            {saveSuccess && (
              <p className="text-xs text-green-600">{t('stockHub.saveSuccess')}</p>
            )}

            <div className="flex flex-wrap gap-2">
              {EVAL_BUTTONS.map(({ type, labelKey }) => {
                const entry = evaluation.evaluations[type]
                const isDone = entry && !entry.isStreaming && entry.text
                return (
                  <div key={type} className="flex items-center">
                    <button
                      onClick={() => handleEvaluate(type)}
                      disabled={evaluation.isAnyStreaming}
                      className={`rounded-l-md px-3 py-1.5 text-xs font-medium transition-colors ${
                        entry?.isStreaming
                          ? 'bg-primary text-primary-foreground animate-pulse'
                          : isDone
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-muted hover:bg-muted/80'
                      } disabled:opacity-50`}
                    >
                      {t(labelKey)}
                      {isDone && ' \u2713'}
                    </button>
                    <button
                      onClick={() => setEditingPromptType(type)}
                      className="rounded-r-md border-l px-1.5 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/80 bg-muted"
                      title={t('stockHub.editPrompt')}
                    >
                      <Settings className="h-3 w-3" />
                    </button>
                  </div>
                )
              })}
            </div>

            {evaluation.error && (
              <p className="text-xs text-destructive">
                {t('stockHub.evalError')}: {evaluation.error.message}
              </p>
            )}

            {/* Accumulated evaluation cards */}
            {EVAL_BUTTONS.map(({ type, labelKey }) => {
              const entry = evaluation.evaluations[type]
              if (!entry) return null
              const isExpanded = expandedEvals.has(type)

              return (
                <div key={type} className="rounded-md border">
                  <button
                    onClick={() => toggleExpand(type)}
                    className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium hover:bg-muted/50"
                  >
                    <span className="flex items-center gap-2">
                      {isExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                      {t(labelKey)}
                      {entry.isStreaming && <Loader2 className="h-3 w-3 animate-spin" />}
                      {entry.isEdited && <Edit3 className="h-3 w-3 text-amber-500" />}
                    </span>
                    {!entry.isStreaming && entry.text && (
                      <span className="text-xs text-muted-foreground">
                        {entry.text.length} {t('stockHub.chars')}
                      </span>
                    )}
                  </button>
                  {isExpanded && (
                    <div className="border-t px-3 py-2">
                      {entry.isStreaming ? (
                        <div className="text-sm leading-relaxed whitespace-pre-wrap">{entry.text}</div>
                      ) : (
                        <textarea
                          value={entry.text}
                          onChange={(e) => evaluation.updateText(type as EvaluationType, e.target.value)}
                          className="w-full min-h-[120px] rounded-md border bg-background p-2 text-sm leading-relaxed resize-y focus:outline-none focus:ring-1 focus:ring-primary"
                          placeholder={t('stockHub.evalPlaceholder')}
                        />
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      <PromptEditor
        evalType={editingPromptType}
        onClose={() => setEditingPromptType(null)}
      />
    </div>
  )
}
