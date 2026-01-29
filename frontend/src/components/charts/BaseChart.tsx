/**
 * Base ECharts Wrapper Component
 * 提供统一的图表容器和响应式处理
 *
 * 注意: 不要使用 ResizeObserver 监听容器大小变化！
 * ECharts 的 dataZoom slider 等组件在 hover 时会触发微小的尺寸变化，
 * 导致 ResizeObserver 回调被触发，进而 chart.resize() 触发重绘，形成无限循环卡死。
 * 应该使用 window resize 事件来处理窗口大小变化。
 */

import { useEffect, useRef, type CSSProperties } from 'react'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
} from 'echarts/components'
import type { EChartsOption } from 'echarts'
import type { EChartsType } from 'echarts/core'

// Register ECharts components
echarts.use([
  CanvasRenderer,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
])

export interface BaseChartProps {
  option: EChartsOption
  style?: CSSProperties
  className?: string
  loading?: boolean
  theme?: 'light' | 'dark'
  onChartReady?: (chart: EChartsType) => void
  /** 更新时是否完全替换配置（默认 true）。设为 false 可保留 roam 等用户状态 */
  notMerge?: boolean
}

export function BaseChart({
  option,
  style,
  className,
  loading = false,
  theme = 'light',
  onChartReady,
  notMerge = true,
}: BaseChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<EChartsType | null>(null)
  const onChartReadyRef = useRef(onChartReady)
  const isFirstOptionSet = useRef(true)
  const prevOptionStrRef = useRef<string>('')

  // 保持 onChartReady 的最新引用，但不触发重新初始化
  useEffect(() => {
    onChartReadyRef.current = onChartReady
  }, [onChartReady])

  // Initialize chart - 只在 mount 和 theme 变化时执行
  useEffect(() => {
    if (!containerRef.current) return

    // 如果已存在图表实例，先销毁
    if (chartRef.current) {
      chartRef.current.dispose()
    }

    // 重新初始化时重置标志
    isFirstOptionSet.current = true
    prevOptionStrRef.current = ''

    const chart = echarts.init(containerRef.current, theme)
    chartRef.current = chart

    onChartReadyRef.current?.(chart)

    // 使用 window resize 事件，不要用 ResizeObserver
    // ResizeObserver 会被 ECharts 内部 UI 变化触发，导致无限循环
    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.dispose()
      chartRef.current = null
    }
  }, [theme])

  // Update option
  // 首次必须用 notMerge=true 完整初始化
  // 后续只有 option 内容真正变化时才调用 setOption，避免干扰 roam 等用户状态
  useEffect(() => {
    if (!chartRef.current) return

    // 首次设置必须调用
    if (isFirstOptionSet.current) {
      chartRef.current.setOption(option, true)
      isFirstOptionSet.current = false
      prevOptionStrRef.current = JSON.stringify(option)
      return
    }

    // 后续只有 option 真正变化时才调用
    const optionStr = JSON.stringify(option)
    if (optionStr !== prevOptionStrRef.current) {
      chartRef.current.setOption(option, notMerge)
      prevOptionStrRef.current = optionStr
    }
  }, [option, notMerge])

  // Handle loading state
  useEffect(() => {
    if (!chartRef.current) return
    if (loading) {
      chartRef.current.showLoading('default', {
        text: '加载中...',
        maskColor: 'rgba(255, 255, 255, 0.8)',
        textColor: '#666',
      })
    } else {
      chartRef.current.hideLoading()
    }
  }, [loading])

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ width: '100%', height: '300px', ...style }}
    />
  )
}

// Re-export echarts for convenience
export { echarts }
