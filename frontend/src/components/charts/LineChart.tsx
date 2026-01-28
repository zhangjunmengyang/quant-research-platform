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
        data: allTimes.map((time) => seriesDataMaps[idx]?.get(time) ?? null),
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

/**
 * Equity Curve with Subplots (100% replicating core engine visualization)
 * 资金曲线多子图组件 - 完整还原 core 引擎的 figure.py 展示形式
 *
 * 布局:
 * - 主图 (70%): 资金曲线 (净值)
 * - 子图1 (10%): 仓位占比堆叠图 (多头/空头/空仓)
 * - 子图2 (10%): 选币数量 (多头/空头)
 * - 子图3 (10%): 单币最大持仓比例
 */
export interface EquityCurveDataPoint {
  candle_begin_time: string
  净值: number
  // 子图1: 仓位占比
  long_pos_value?: number
  short_pos_value?: number
  // 子图2: 选币数量
  symbol_long_num?: number
  symbol_short_num?: number
  // 子图3: 单币最大持仓
  long_max_ratio?: number
  short_max_ratio_abs?: number
  top3_long?: string
  top3_short?: string
  // 其他字段
  净值dd2here?: number
  涨跌幅?: number
  leverage_ratio?: number
  fee?: number
  是否爆仓?: number
  equity?: number
}

interface EquityCurveSubplotsProps {
  data: EquityCurveDataPoint[]
  title?: string
  height?: number
  loading?: boolean
  className?: string
}

export function EquityCurveSubplots({
  data,
  title,
  height = 600,
  loading = false,
  className,
}: EquityCurveSubplotsProps) {
  // 检测是否有子图数据
  const hasPositionData = data.some(d => d.long_pos_value !== undefined || d.short_pos_value !== undefined)
  const hasSymbolNumData = data.some(d => d.symbol_long_num !== undefined || d.symbol_short_num !== undefined)
  const hasMaxRatioData = data.some(d => d.long_max_ratio !== undefined || d.short_max_ratio_abs !== undefined)

  // 计算需要的子图数量
  const subplotCount = [hasPositionData, hasSymbolNumData, hasMaxRatioData].filter(Boolean).length

  // 动态计算高度比例
  const getGridHeights = () => {
    if (subplotCount === 0) return [{ height: '75%', top: '10%' }]
    const mainHeight = 70
    const subHeight = 30 / subplotCount
    const heights: Array<{ height: string; top: string }> = []
    let currentTop = 8

    // 主图
    heights.push({ height: `${mainHeight - 5}%`, top: `${currentTop}%` })
    currentTop += mainHeight

    // 子图
    for (let i = 0; i < subplotCount; i++) {
      heights.push({ height: `${subHeight - 3}%`, top: `${currentTop}%` })
      currentTop += subHeight
    }
    return heights
  }

  const gridHeights = getGridHeights()

  const option = useMemo<EChartsOption>(() => {
    const times = data.map(d => d.candle_begin_time)
    const netValues = data.map(d => d.净值)

    // 计算仓位占比 (需要 equity 或从 long_pos_value + short_pos_value 推算)
    const positionRatios = data.map(d => {
      if (d.long_pos_value === undefined && d.short_pos_value === undefined) {
        return { long: 0, short: 0, empty: 1 }
      }
      const equity = d.equity || (d.净值 * 10000) // 假设初始资金 10000
      const longRatio = equity > 0 ? (d.long_pos_value || 0) / equity : 0
      const shortRatio = equity > 0 ? (d.short_pos_value || 0) / equity : 0
      const emptyRatio = Math.max(0, 1 - longRatio - shortRatio)
      return { long: longRatio, short: shortRatio, empty: emptyRatio }
    })

    // 构建 grid 配置
    const grids: EChartsOption['grid'] = gridHeights.map((g) => ({
      left: '3%',
      right: '4%',
      height: g.height,
      top: g.top,
      containLabel: true,
    }))

    // 构建 xAxis 配置
    const xAxes: EChartsOption['xAxis'] = gridHeights.map((_, idx) => ({
      type: 'category' as const,
      data: times,
      gridIndex: idx,
      boundaryGap: false,
      axisLine: { show: idx === gridHeights.length - 1 },
      axisTick: { show: idx === gridHeights.length - 1 },
      axisLabel: { show: idx === gridHeights.length - 1 },
    }))

    // 构建 yAxis 配置
    const yAxes: EChartsOption['yAxis'] = []
    let gridIdx = 0

    // 主图 y 轴
    yAxes.push({
      type: 'value' as const,
      gridIndex: gridIdx,
      name: '净值',
      nameLocation: 'end',
      splitLine: { lineStyle: { type: 'dashed' as const } },
    })

    // 子图 y 轴
    if (hasPositionData) {
      gridIdx++
      yAxes.push({
        type: 'value' as const,
        gridIndex: gridIdx,
        name: '仓位占比',
        nameLocation: 'end',
        max: 1,
        min: 0,
        splitLine: { show: false },
        axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` },
      })
    }

    if (hasSymbolNumData) {
      gridIdx++
      yAxes.push({
        type: 'value' as const,
        gridIndex: gridIdx,
        name: '选币数量',
        nameLocation: 'end',
        splitLine: { show: false },
      })
    }

    if (hasMaxRatioData) {
      gridIdx++
      yAxes.push({
        type: 'value' as const,
        gridIndex: gridIdx,
        name: '单币持仓(max)',
        nameLocation: 'end',
        splitLine: { show: false },
        axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` },
      })
    }

    // 构建 series 配置
    const seriesList: EChartsOption['series'] = []

    // 主图: 资金曲线
    seriesList.push({
      name: '净值',
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: netValues,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#3b82f6', width: 2 },
      areaStyle: { color: 'rgba(59, 130, 246, 0.2)' },
    })

    // 子图1: 仓位占比堆叠图
    if (hasPositionData) {
      const posGridIdx = 1 // 第二个 grid

      seriesList.push({
        name: '多头仓位',
        type: 'line',
        xAxisIndex: posGridIdx,
        yAxisIndex: posGridIdx,
        data: positionRatios.map(r => r.long),
        stack: 'position',
        areaStyle: { color: 'rgba(30, 177, 0, 0.6)' },
        lineStyle: { width: 0 },
        showSymbol: false,
      })

      seriesList.push({
        name: '空头仓位',
        type: 'line',
        xAxisIndex: posGridIdx,
        yAxisIndex: posGridIdx,
        data: positionRatios.map(r => r.short),
        stack: 'position',
        areaStyle: { color: 'rgba(255, 99, 77, 0.6)' },
        lineStyle: { width: 0 },
        showSymbol: false,
      })

      seriesList.push({
        name: '空仓',
        type: 'line',
        xAxisIndex: posGridIdx,
        yAxisIndex: posGridIdx,
        data: positionRatios.map(r => r.empty),
        stack: 'position',
        areaStyle: { color: 'rgba(0, 46, 77, 0.6)' },
        lineStyle: { width: 0 },
        showSymbol: false,
      })
    }

    // 子图2: 选币数量
    if (hasSymbolNumData) {
      const symGridIdx = hasPositionData ? 2 : 1

      seriesList.push({
        name: '多头选币数量',
        type: 'line',
        xAxisIndex: symGridIdx,
        yAxisIndex: symGridIdx,
        data: data.map(d => d.symbol_long_num ?? null),
        lineStyle: { color: 'rgba(30, 177, 0, 0.8)', width: 2 },
        showSymbol: false,
      })

      seriesList.push({
        name: '空头选币数量',
        type: 'line',
        xAxisIndex: symGridIdx,
        yAxisIndex: symGridIdx,
        data: data.map(d => d.symbol_short_num ?? null),
        lineStyle: { color: 'rgba(255, 99, 77, 0.8)', width: 2 },
        showSymbol: false,
      })
    }

    // 子图3: 单币最大持仓
    if (hasMaxRatioData) {
      const maxGridIdx = gridHeights.length - 1

      seriesList.push({
        name: '多头单币最大持仓',
        type: 'line',
        xAxisIndex: maxGridIdx,
        yAxisIndex: maxGridIdx,
        data: data.map(d => d.long_max_ratio ?? null),
        lineStyle: { color: 'rgba(30, 177, 0, 0.8)', width: 2 },
        showSymbol: false,
      })

      seriesList.push({
        name: '空头单币最大持仓',
        type: 'line',
        xAxisIndex: maxGridIdx,
        yAxisIndex: maxGridIdx,
        data: data.map(d => d.short_max_ratio_abs ?? null),
        lineStyle: { color: 'rgba(255, 99, 77, 0.8)', width: 2 },
        showSymbol: false,
      })
    }

    return {
      title: title ? {
        text: title,
        left: 'center',
        textStyle: { fontSize: 14, fontWeight: 500 },
      } : undefined,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross', link: [{ xAxisIndex: 'all' }] },
        formatter: (params: unknown) => {
          if (!Array.isArray(params) || params.length === 0) return ''
          const time = (params[0] as { axisValue?: string }).axisValue || ''
          const dataIdx = (params[0] as { dataIndex?: number }).dataIndex ?? 0
          const d = data[dataIdx]
          if (!d) return ''

          let html = `<div style="font-weight:bold;margin-bottom:4px">${time}</div>`

          // 主图数据
          html += `<div>净值: <span style="color:#3b82f6;font-weight:bold">${d.净值?.toFixed(4) ?? '-'}</span></div>`
          if (d.涨跌幅 !== undefined) {
            const color = d.涨跌幅 >= 0 ? '#22c55e' : '#ef4444'
            html += `<div>涨跌幅: <span style="color:${color}">${(d.涨跌幅 * 100).toFixed(2)}%</span></div>`
          }
          if (d.净值dd2here !== undefined) {
            html += `<div>回撤: <span style="color:#ef4444">${(d.净值dd2here * 100).toFixed(2)}%</span></div>`
          }

          // 仓位数据
          if (d.long_pos_value !== undefined || d.short_pos_value !== undefined) {
            html += `<div style="margin-top:4px;border-top:1px solid #eee;padding-top:4px">`
            if (d.long_pos_value !== undefined) {
              html += `<div>多头持仓: <span style="color:#1eb100">${d.long_pos_value.toFixed(2)}</span></div>`
            }
            if (d.short_pos_value !== undefined) {
              html += `<div>空头持仓: <span style="color:#ff634d">${d.short_pos_value.toFixed(2)}</span></div>`
            }
            if (d.leverage_ratio !== undefined) {
              html += `<div>杠杆率: ${d.leverage_ratio.toFixed(2)}x</div>`
            }
            html += `</div>`
          }

          // 选币数量
          if (d.symbol_long_num !== undefined || d.symbol_short_num !== undefined) {
            html += `<div style="margin-top:4px;border-top:1px solid #eee;padding-top:4px">`
            if (d.symbol_long_num !== undefined) {
              html += `<div>多头选币: <span style="color:#1eb100">${d.symbol_long_num}</span></div>`
            }
            if (d.symbol_short_num !== undefined) {
              html += `<div>空头选币: <span style="color:#ff634d">${d.symbol_short_num}</span></div>`
            }
            html += `</div>`
          }

          // 最大持仓
          if (d.long_max_ratio !== undefined || d.short_max_ratio_abs !== undefined) {
            html += `<div style="margin-top:4px;border-top:1px solid #eee;padding-top:4px">`
            if (d.long_max_ratio !== undefined) {
              html += `<div>多头最大持仓: <span style="color:#1eb100">${(d.long_max_ratio * 100).toFixed(2)}%</span></div>`
              if (d.top3_long) {
                html += `<div style="font-size:11px;color:#666">前3: ${d.top3_long}</div>`
              }
            }
            if (d.short_max_ratio_abs !== undefined) {
              html += `<div>空头最大持仓: <span style="color:#ff634d">${(d.short_max_ratio_abs * 100).toFixed(2)}%</span></div>`
              if (d.top3_short) {
                html += `<div style="font-size:11px;color:#666">前3: ${d.top3_short}</div>`
              }
            }
            html += `</div>`
          }

          return html
        },
      },
      legend: {
        data: ['净值', '多头仓位', '空头仓位', '空仓', '多头选币数量', '空头选币数量', '多头单币最大持仓', '空头单币最大持仓'],
        bottom: 0,
        type: 'scroll',
      },
      axisPointer: {
        link: [{ xAxisIndex: 'all' }],
      },
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: gridHeights.map((_, i) => i),
          start: 0,
          end: 100,
        },
        {
          show: true,
          type: 'slider',
          xAxisIndex: gridHeights.map((_, i) => i),
          bottom: '3%',
          height: 20,
          start: 0,
          end: 100,
        },
      ],
      grid: grids,
      xAxis: xAxes,
      yAxis: yAxes,
      series: seriesList,
    }
  }, [data, title, gridHeights, hasPositionData, hasSymbolNumData, hasMaxRatioData])

  return (
    <BaseChart
      option={option}
      style={{ height }}
      loading={loading}
      className={className}
    />
  )
}
