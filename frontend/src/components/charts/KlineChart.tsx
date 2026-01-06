/**
 * K-Line (Candlestick) Chart Component
 * K线图组件 - 用于展示OHLC数据
 * 使用美股配色：绿涨红跌
 * 成交额柱状图整合在主图底部，共享同一坐标轴
 *
 * 性能优化:
 * - 使用 large: true 启用大数据量渲染优化
 * - 使用 useMemo 缓存数据处理结果
 * - 使用 notMerge: false 启用增量更新
 */

import { useEffect, useRef, useMemo } from 'react'
import * as echarts from 'echarts'

export interface KlineData {
  time: string
  open: number
  close: number
  high: number
  low: number
  volume?: number
  quote_volume?: number  // 成交额
  taker_buy_quote_asset_volume?: number  // 主动买入成交额
}

interface KlineChartProps {
  data: KlineData[]
  title?: string
  height?: number
  showVolume?: boolean
  loading?: boolean
  className?: string
}

export function KlineChart({
  data,
  height = 400,
  showVolume = true,
  className,
}: KlineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)

  // 初始化图表 - 只执行一次
  useEffect(() => {
    if (!containerRef.current) return

    const chart = echarts.init(containerRef.current)
    chartRef.current = chart

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.dispose()
      chartRef.current = null
    }
  }, [])

  // 格式化数字显示
  const formatNumber = (num: number): string => {
    if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B'
    if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M'
    if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K'
    return num.toFixed(2)
  }

  // 使用 useMemo 缓存处理后的数据，避免每次渲染重复计算
  const processedData = useMemo(() => {
    if (data.length === 0) return null

    const times = data.map((d) => d.time)
    // ECharts candlestick 格式: [open, close, lowest, highest]
    const ohlc = data.map((d) => [d.open, d.close, d.low, d.high])

    // 成交额数据 - 带颜色标记（1: 涨, -1: 跌）
    const quoteVolumes = data.map((d) => ({
      value: d.quote_volume || 0,
      itemStyle: {
        color: d.close >= d.open ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)',
      },
    }))

    return { times, ohlc, quoteVolumes }
  }, [data])

  // 更新数据
  useEffect(() => {
    if (!chartRef.current || !processedData) return

    const { times, ohlc, quoteVolumes } = processedData

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          link: [{ xAxisIndex: 'all' }],
          crossStyle: {
            color: '#999',
          },
        },
        formatter: (params: unknown) => {
          const paramArray = params as Array<{
            axisValue: string
            dataIndex: number
            data: number[] | { value: number }
            seriesType: string
          }>
          if (!paramArray || paramArray.length === 0) return ''

          const firstParam = paramArray[0]
          if (!firstParam) return ''
          const time = firstParam.axisValue
          const dataIndex = firstParam.dataIndex
          const candleData = paramArray.find(p => p.seriesType === 'candlestick')

          // 从原始数据获取额外字段
          const originalData = data[dataIndex]

          let html = `<div style="font-weight:600;margin-bottom:8px">${time}</div>`

          if (candleData && Array.isArray(candleData.data)) {
            const [open, close, low, high] = candleData.data as number[]

            html += `<div style="display:flex;justify-content:space-between;gap:20px;margin:4px 0">
              <span>开盘</span><span style="font-weight:500">${formatNumber(open ?? 0)}</span>
            </div>`
            html += `<div style="display:flex;justify-content:space-between;gap:20px;margin:4px 0">
              <span>收盘</span><span style="font-weight:500">${formatNumber(close ?? 0)}</span>
            </div>`
            html += `<div style="display:flex;justify-content:space-between;gap:20px;margin:4px 0">
              <span>最高</span><span style="font-weight:500">${formatNumber(high ?? 0)}</span>
            </div>`
            html += `<div style="display:flex;justify-content:space-between;gap:20px;margin:4px 0">
              <span>最低</span><span style="font-weight:500">${formatNumber(low ?? 0)}</span>
            </div>`
          }

          // 显示成交额
          if (originalData?.quote_volume != null) {
            html += `<div style="display:flex;justify-content:space-between;gap:20px;margin:4px 0">
              <span>成交额</span><span style="font-weight:500">${formatNumber(originalData.quote_volume)}</span>
            </div>`
          }

          // 显示买入额
          if (originalData?.taker_buy_quote_asset_volume != null) {
            html += `<div style="display:flex;justify-content:space-between;gap:20px;margin:4px 0">
              <span>买入额</span><span style="font-weight:500">${formatNumber(originalData.taker_buy_quote_asset_volume)}</span>
            </div>`
          }

          return html
        },
      },
      axisPointer: {
        link: [{ xAxisIndex: 'all' }],
        label: {
          show: false,  // 隐藏悬浮时的坐标轴标签
        },
      },
      grid: showVolume
        ? [
            {
              left: 60,
              right: 60,
              top: 30,
              height: '55%',
              backgroundColor: 'rgba(0,0,0,0.02)',
              show: true,
              borderWidth: 0,
            },
            {
              left: 60,
              right: 60,
              top: '72%',
              height: '13%',
              backgroundColor: 'rgba(0,0,0,0.02)',
              show: true,
              borderWidth: 0,
            },
          ]
        : [
            {
              left: 60,
              right: 60,
              top: 30,
              bottom: 80,
              backgroundColor: 'rgba(0,0,0,0.02)',
              show: true,
              borderWidth: 0,
            },
          ],
      xAxis: showVolume
        ? [
            {
              type: 'category',
              data: times,
              boundaryGap: true,
              axisLine: { lineStyle: { color: '#ddd' } },
              splitLine: { show: false },
              axisLabel: { show: false },
              axisTick: { show: false },
              axisPointer: {
                label: { show: false },
              },
            },
            {
              type: 'category',
              gridIndex: 1,
              data: times,
              boundaryGap: true,
              axisLine: { lineStyle: { color: '#ddd' } },
              splitLine: { show: false },
              axisTick: { show: false },
              axisLabel: {
                color: '#666',
                fontSize: 11,
              },
              axisPointer: {
                label: { show: false },
              },
            },
          ]
        : [
            {
              type: 'category',
              data: times,
              boundaryGap: true,
              axisLine: { lineStyle: { color: '#ddd' } },
              splitLine: { show: false },
              axisLabel: {
                color: '#666',
                fontSize: 11,
              },
              axisPointer: {
                label: { show: false },
              },
            },
          ],
      yAxis: showVolume
        ? [
            {
              scale: true,
              splitArea: { show: false },
              splitLine: { lineStyle: { color: '#eee', type: 'dashed' } },
              axisLine: { show: false },
              axisTick: { show: false },
              axisLabel: {
                color: '#666',
                fontSize: 11,
              },
              axisPointer: {
                label: { show: false },
              },
            },
            {
              scale: true,
              gridIndex: 1,
              splitNumber: 2,
              axisLine: { show: false },
              axisTick: { show: false },
              splitLine: { show: false },
              axisLabel: {
                color: '#666',
                fontSize: 11,
                formatter: (value: number) => formatNumber(value),
              },
              axisPointer: {
                label: { show: false },
              },
            },
          ]
        : [
            {
              scale: true,
              splitArea: { show: false },
              splitLine: { lineStyle: { color: '#eee', type: 'dashed' } },
              axisLine: { show: false },
              axisTick: { show: false },
              axisLabel: {
                color: '#666',
                fontSize: 11,
              },
              axisPointer: {
                label: { show: false },
              },
            },
          ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: showVolume ? [0, 1] : [0],
          start: 70,
          end: 100,
        },
        {
          type: 'slider',
          xAxisIndex: showVolume ? [0, 1] : [0],
          start: 70,
          end: 100,
          top: '88%',
          height: 20,
          borderColor: '#ddd',
          backgroundColor: '#fafafa',
          fillerColor: 'rgba(0,0,0,0.05)',
          handleStyle: {
            color: '#fff',
            borderColor: '#ccc',
          },
          textStyle: {
            color: '#666',
            fontSize: 10,
          },
        },
      ],
      series: [
        {
          type: 'candlestick',
          name: 'K线',
          data: ohlc,
          large: true, // 启用大数据量优化
          largeThreshold: 500, // 超过 500 条数据时启用
          itemStyle: {
            // 美股模式：绿涨红跌
            color: '#22c55e',      // 涨（收盘 >= 开盘）填充色
            color0: '#ef4444',     // 跌（收盘 < 开盘）填充色
            borderColor: '#22c55e', // 涨边框色
            borderColor0: '#ef4444', // 跌边框色
          },
        },
        ...(showVolume
          ? [
              {
                type: 'bar' as const,
                name: '成交额',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: quoteVolumes,
                barWidth: '60%',
                large: true, // 启用大数据量优化
                largeThreshold: 500,
              },
            ]
          : []),
      ],
    }

    // 使用 notMerge: false 允许增量更新（更高效）
    chartRef.current.setOption(option, { notMerge: false, lazyUpdate: true })
  }, [processedData, showVolume])

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ width: '100%', height }}
    />
  )
}
