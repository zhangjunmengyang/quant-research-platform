/**
 * Line Chart Component
 * 折线图组件 - 用于时序数据展示（如资金曲线、IC序列等）
 */

import { useMemo } from 'react'
import { BaseChart, echarts } from './BaseChart'
import { LineChart as ELineChart } from 'echarts/charts'
import type { EChartsOption } from 'echarts'

// Register line chart
echarts.use([ELineChart])

export interface LineSeriesData {
  name: string
  data: Array<{ time: string; value: number }>
  color?: string
  areaStyle?: boolean
}

interface LineChartProps {
  series: LineSeriesData[]
  title?: string
  height?: number
  loading?: boolean
  className?: string
  yAxisName?: string
  showLegend?: boolean
  showDataZoom?: boolean
}

export function LineChart({
  series,
  title,
  height = 300,
  loading = false,
  className,
  yAxisName,
  showLegend = true,
  showDataZoom = false,
}: LineChartProps) {
  const option = useMemo<EChartsOption>(() => {
    // Get all unique times
    const allTimes = Array.from(
      new Set(series.flatMap((s) => s.data.map((d) => d.time)))
    ).sort()

    // 预构建每个 series 的时间->值映射，避免 O(n²) 查找
    const seriesDataMaps = series.map((s) => {
      const map = new Map<string, number>()
      for (const d of s.data) {
        map.set(d.time, d.value)
      }
      return map
    })

    return {
      title: title
        ? {
            text: title,
            left: 'center',
            textStyle: { fontSize: 14, fontWeight: 500 },
          }
        : undefined,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      legend: showLegend
        ? {
            data: series.map((s) => s.name),
            bottom: 0,
          }
        : undefined,
      grid: {
        left: '3%',
        right: '4%',
        top: title ? '15%' : '10%',
        bottom: showDataZoom ? '20%' : showLegend ? '15%' : '10%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: allTimes,
        boundaryGap: false,
      },
      yAxis: {
        type: 'value',
        name: yAxisName,
        splitLine: {
          lineStyle: { type: 'dashed' },
        },
      },
      dataZoom: showDataZoom
        ? [
            {
              type: 'inside',
              start: 0,
              end: 100,
            },
            {
              show: true,
              type: 'slider',
              bottom: '5%',
              start: 0,
              end: 100,
            },
          ]
        : undefined,
      series: series.map((s, idx) => ({
        name: s.name,
        type: 'line' as const,
        data: allTimes.map((time) => seriesDataMaps[idx].get(time) ?? null),
        smooth: true,
        showSymbol: false,
        itemStyle: s.color ? { color: s.color } : undefined,
        areaStyle: s.areaStyle
          ? {
              opacity: 0.3,
            }
          : undefined,
      })),
    }
  }, [series, title, yAxisName, showLegend, showDataZoom])

  return (
    <BaseChart
      option={option}
      style={{ height }}
      loading={loading}
      className={className}
    />
  )
}

/**
 * Equity Curve Chart (specialized line chart for strategy performance)
 */
interface EquityCurveProps {
  data: Array<{ time: string; value: number }>
  benchmark?: Array<{ time: string; value: number }>
  title?: string
  height?: number
  loading?: boolean
  className?: string
}

export function EquityCurve({
  data,
  benchmark,
  title = '资金曲线',
  height = 300,
  loading = false,
  className,
}: EquityCurveProps) {
  const series: LineSeriesData[] = [
    {
      name: '策略收益',
      data,
      color: '#3b82f6',
      areaStyle: true,
    },
  ]

  if (benchmark) {
    series.push({
      name: '基准',
      data: benchmark,
      color: '#9ca3af',
    })
  }

  return (
    <LineChart
      series={series}
      title={title}
      height={height}
      loading={loading}
      className={className}
      yAxisName="收益率"
      showDataZoom={data.length > 100}
    />
  )
}

/**
 * IC Time Series Chart
 */
interface ICTimeSeriesProps {
  data: Array<{ time: string; ic: number; rankIC?: number }>
  title?: string
  height?: number
  loading?: boolean
  className?: string
}

export function ICTimeSeries({
  data,
  title = 'IC 时序',
  height = 300,
  loading = false,
  className,
}: ICTimeSeriesProps) {
  const series: LineSeriesData[] = [
    {
      name: 'IC',
      data: data.map((d) => ({ time: d.time, value: d.ic })),
      color: '#3b82f6',
    },
  ]

  if (data.some((d) => d.rankIC !== undefined)) {
    series.push({
      name: 'Rank IC',
      data: data
        .filter((d) => d.rankIC !== undefined)
        .map((d) => ({ time: d.time, value: d.rankIC! })),
      color: '#f59e0b',
    })
  }

  return (
    <LineChart
      series={series}
      title={title}
      height={height}
      loading={loading}
      className={className}
      yAxisName="IC"
      showDataZoom={data.length > 50}
    />
  )
}
