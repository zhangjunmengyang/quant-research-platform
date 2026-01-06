/**
 * Pie Chart Component
 */

import { useRef, useEffect } from 'react'
import { BaseChart } from './BaseChart'
import type { EChartsOption } from 'echarts'
import type { EChartsType } from 'echarts/core'

export interface PieData {
  name: string
  value: number
}

export interface PieChartProps {
  data: PieData[]
  title?: string
  height?: number
  showLegend?: boolean
  radius?: [string, string]
  colors?: string[]
}

export function PieChart({
  data,
  title,
  height = 300,
  showLegend = true,
  radius = ['40%', '70%'],
  colors,
}: PieChartProps) {
  const chartRef = useRef<EChartsType | null>(null)

  useEffect(() => {
    if (!chartRef.current) return

    const option: EChartsOption = {
      title: title
        ? {
            text: title,
            left: 'center',
            textStyle: {
              fontSize: 14,
              fontWeight: 500,
            },
          }
        : undefined,
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)',
      },
      legend: showLegend
        ? {
            orient: 'vertical',
            right: 10,
            top: 'center',
            type: 'scroll',
          }
        : undefined,
      color: colors,
      series: [
        {
          name: title || 'Data',
          type: 'pie',
          radius: radius,
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 4,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: {
            show: false,
            position: 'center',
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 16,
              fontWeight: 'bold',
            },
          },
          labelLine: {
            show: false,
          },
          data: data,
        },
      ],
    }

    chartRef.current.setOption(option)
  }, [data, title, showLegend, radius, colors])

  return (
    <BaseChart
      option={{}}
      style={{ height }}
      onChartReady={(chart) => {
        chartRef.current = chart
      }}
    />
  )
}
