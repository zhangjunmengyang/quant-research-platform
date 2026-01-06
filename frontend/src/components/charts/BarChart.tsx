/**
 * Bar Chart Component
 * 柱状图组件 - 用于分组收益、评分分布等
 */

import { useMemo } from 'react'
import { BaseChart, echarts } from './BaseChart'
import { BarChart as EBarChart } from 'echarts/charts'
import type { EChartsOption } from 'echarts'

// Register bar chart
echarts.use([EBarChart])

export interface BarSeriesData {
  name: string
  data: Array<{ category: string; value: number }>
  color?: string
}

interface BarChartProps {
  series: BarSeriesData[]
  title?: string
  height?: number
  loading?: boolean
  className?: string
  yAxisName?: string
  showLegend?: boolean
  horizontal?: boolean
  stack?: boolean
}

export function BarChart({
  series,
  title,
  height = 300,
  loading = false,
  className,
  yAxisName,
  showLegend = true,
  horizontal = false,
  stack = false,
}: BarChartProps) {
  const option = useMemo<EChartsOption>(() => {
    // Get all unique categories
    const categories = Array.from(
      new Set(series.flatMap((s) => s.data.map((d) => d.category)))
    )

    const categoryAxis = {
      type: 'category' as const,
      data: categories,
      axisLabel: horizontal
        ? { fontSize: 11 }
        : { rotate: categories.length > 5 ? 45 : 0, fontSize: 11 },
    }

    const valueAxis = {
      type: 'value' as const,
      name: yAxisName,
      splitLine: {
        lineStyle: { type: 'dashed' as const },
      },
    }

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
        axisPointer: { type: 'shadow' },
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
        bottom: showLegend ? '15%' : '10%',
        containLabel: true,
      },
      xAxis: horizontal ? valueAxis : categoryAxis,
      yAxis: horizontal ? categoryAxis : valueAxis,
      series: series.map((s) => ({
        name: s.name,
        type: 'bar' as const,
        data: categories.map((cat) => {
          const point = s.data.find((d) => d.category === cat)
          return point?.value ?? 0
        }),
        itemStyle: s.color ? { color: s.color } : undefined,
        stack: stack ? 'total' : undefined,
      })),
    }
  }, [series, title, yAxisName, showLegend, horizontal, stack])

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
 * Group Return Chart (specialized bar chart for factor quintile analysis)
 */
interface GroupReturnProps {
  groups: string[]
  returns: number[]
  title?: string
  height?: number
  loading?: boolean
  className?: string
}

export function GroupReturnChart({
  groups,
  returns,
  title = '分组收益',
  height = 300,
  loading = false,
  className,
}: GroupReturnProps) {
  const series: BarSeriesData[] = [
    {
      name: '收益',
      data: groups.map((group, i) => ({
        category: group,
        value: returns[i] ?? 0,
      })),
    },
  ]

  return (
    <BarChart
      series={series}
      title={title}
      height={height}
      loading={loading}
      className={className}
      yAxisName="收益率 (%)"
      showLegend={false}
    />
  )
}

/**
 * Distribution Chart (for score/value distribution)
 */
interface DistributionChartProps {
  bins: string[]
  counts: number[]
  title?: string
  height?: number
  loading?: boolean
  className?: string
}

export function DistributionChart({
  bins,
  counts,
  title = '分布',
  height = 300,
  loading = false,
  className,
}: DistributionChartProps) {
  const series: BarSeriesData[] = [
    {
      name: '数量',
      data: bins.map((bin, i) => ({
        category: bin,
        value: counts[i] ?? 0,
      })),
      color: '#3b82f6',
    },
  ]

  return (
    <BarChart
      series={series}
      title={title}
      height={height}
      loading={loading}
      className={className}
      yAxisName="数量"
      showLegend={false}
    />
  )
}
