/**
 * Heatmap Chart Component
 * 热力图组件 - 用于相关性矩阵展示
 */

import { useMemo } from 'react'
import { BaseChart, echarts } from './BaseChart'
import { HeatmapChart as EHeatmapChart } from 'echarts/charts'
import { VisualMapComponent } from 'echarts/components'
import type { EChartsOption } from 'echarts'

// Register heatmap chart
echarts.use([EHeatmapChart, VisualMapComponent])

export interface HeatmapData {
  x: string
  y: string
  value: number
}

interface HeatmapChartProps {
  data: HeatmapData[]
  xLabels: string[]
  yLabels: string[]
  title?: string
  height?: number
  loading?: boolean
  className?: string
  minValue?: number
  maxValue?: number
  colorRange?: [string, string, string]
}

export function HeatmapChart({
  data,
  xLabels,
  yLabels,
  title,
  height = 400,
  loading = false,
  className,
  minValue = -1,
  maxValue = 1,
  colorRange = ['#3b82f6', '#ffffff', '#ef4444'],
}: HeatmapChartProps) {
  const option = useMemo<EChartsOption>(() => {
    // Convert data to [xIndex, yIndex, value] format
    const seriesData = data.map((d) => {
      const xIndex = xLabels.indexOf(d.x)
      const yIndex = yLabels.indexOf(d.y)
      return [xIndex, yIndex, d.value]
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
        position: 'top',
        formatter: (params: any) => {
          const [xIdx, yIdx, value] = params.data
          return `${xLabels[xIdx]} - ${yLabels[yIdx]}<br/>相关系数: ${value.toFixed(3)}`
        },
      },
      grid: {
        left: '15%',
        right: '10%',
        top: title ? '15%' : '10%',
        bottom: '15%',
      },
      xAxis: {
        type: 'category',
        data: xLabels,
        splitArea: { show: true },
        axisLabel: {
          rotate: 45,
          fontSize: 11,
        },
      },
      yAxis: {
        type: 'category',
        data: yLabels,
        splitArea: { show: true },
        axisLabel: {
          fontSize: 11,
        },
      },
      visualMap: {
        min: minValue,
        max: maxValue,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '0%',
        inRange: {
          color: colorRange,
        },
      },
      series: [
        {
          name: '相关性',
          type: 'heatmap',
          data: seriesData,
          label: {
            show: xLabels.length <= 10,
            formatter: (params: any) => params.data[2].toFixed(2),
            fontSize: 10,
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
            },
          },
        },
      ],
    }
  }, [data, xLabels, yLabels, title, minValue, maxValue, colorRange])

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
 * Correlation Matrix Chart (specialized heatmap for factor correlations)
 */
interface CorrelationMatrixProps {
  factors: string[]
  correlations: number[][]
  title?: string
  height?: number
  loading?: boolean
  className?: string
}

export function CorrelationMatrix({
  factors,
  correlations,
  title = '因子相关性矩阵',
  height = 400,
  loading = false,
  className,
}: CorrelationMatrixProps) {
  const data = useMemo<HeatmapData[]>(() => {
    const result: HeatmapData[] = []
    for (let i = 0; i < factors.length; i++) {
      for (let j = 0; j < factors.length; j++) {
        result.push({
          x: factors[i] ?? '',
          y: factors[j] ?? '',
          value: correlations[i]?.[j] ?? 0,
        })
      }
    }
    return result
  }, [factors, correlations])

  return (
    <HeatmapChart
      data={data}
      xLabels={factors}
      yLabels={factors}
      title={title}
      height={height}
      loading={loading}
      className={className}
    />
  )
}
