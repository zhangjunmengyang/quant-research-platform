/**
 * Graph Chart Component
 * 基于 ECharts 的知识图谱可视化组件
 *
 * 注意: 不使用 ResizeObserver，遵循项目约定
 */

import { useMemo, useCallback, useEffect, useRef } from 'react'
import { BaseChart, echarts } from './BaseChart'
import { GraphChart as EGraphChart } from 'echarts/charts'
import type { EChartsOption, GraphSeriesOption } from 'echarts'
import type { EChartsType } from 'echarts/core'
import { ZoomIn, ZoomOut, Locate } from 'lucide-react'

// 注册 Graph 图表类型
echarts.use([EGraphChart])

// 径向渐变颜色配置
interface RadialGradientColor {
  type: 'radial'
  x: number
  y: number
  r: number
  colorStops: Array<{ offset: number; color: string }>
}

export interface GraphNodeData {
  id: string
  name: string
  category: number // 对应 categories 索引
  value?: number // 节点大小
  symbolSize?: number
  x?: number // 固定位置 x
  y?: number // 固定位置 y
  fixed?: boolean // 是否固定位置
  itemStyle?: {
    color?: string | RadialGradientColor // 支持渐变
    borderColor?: string
    borderWidth?: number
    shadowBlur?: number
    shadowColor?: string
    shadowOffsetX?: number
    shadowOffsetY?: number
  }
  label?: {
    show?: boolean
    formatter?: string
  }
}

export interface GraphLinkData {
  source: string // 源节点 id
  target: string // 目标节点 id
  value?: number // 边权重
  relationLabel?: string // 关系标签（避免与 ECharts label 冲突）
  lineStyle?: {
    color?: string
    width?: number
    type?: 'solid' | 'dashed' | 'dotted'
    curveness?: number
  }
}

export interface GraphCategoryData {
  name: string
  itemStyle?: {
    color?: string
  }
}

interface GraphChartProps {
  nodes: GraphNodeData[]
  links: GraphLinkData[]
  categories: GraphCategoryData[]
  height?: number | string
  loading?: boolean
  className?: string
  // 布局配置
  layout?: 'force' | 'circular' | 'none'
  roam?: boolean | 'scale' | 'move'
  draggable?: boolean
  // 力导向布局参数
  repulsion?: number
  gravity?: number
  edgeLength?: number | [number, number]
  // 事件回调
  onNodeClick?: (node: GraphNodeData, event: { offsetX: number; offsetY: number }) => void
  onNodeDblClick?: (node: GraphNodeData) => void
  onChartReady?: (chart: EChartsType) => void
  // 聚焦节点
  focusNodeId?: string
  // 工具栏
  showToolbar?: boolean
}

export function GraphChart({
  nodes,
  links,
  categories,
  height = 400,
  loading = false,
  className,
  layout = 'force',
  roam = true,
  draggable = true,
  repulsion = 500,
  gravity = 0.1,
  edgeLength = [50, 200],
  onNodeClick,
  onNodeDblClick,
  onChartReady,
  focusNodeId,
  showToolbar = false,
}: GraphChartProps) {
  const chartRef = useRef<EChartsType | null>(null)
  const zoomRef = useRef(1)
  // 画布拖动状态
  const centerRef = useRef<[number, number] | null>(null)
  const isDraggingCanvasRef = useRef(false)
  const dragStartRef = useRef<{ x: number; y: number } | null>(null)

  // 工具栏操作 - 通过修改 series.zoom 实现缩放
  const handleZoomIn = useCallback(() => {
    if (!chartRef.current) return
    zoomRef.current = Math.min(zoomRef.current * 1.3, 5)
    chartRef.current.setOption({
      series: [{ zoom: zoomRef.current }],
    })
  }, [])

  const handleZoomOut = useCallback(() => {
    if (!chartRef.current) return
    zoomRef.current = Math.max(zoomRef.current / 1.3, 0.2)
    chartRef.current.setOption({
      series: [{ zoom: zoomRef.current }],
    })
  }, [])

  const handleResetView = useCallback(() => {
    if (!chartRef.current) return
    zoomRef.current = 1
    centerRef.current = null
    // 重置 zoom 和 center
    chartRef.current.setOption({
      series: [{ zoom: 1, center: undefined }],
    })
  }, [])

  // 处理聚焦节点样式
  const processedNodes = useMemo(() => {
    if (!focusNodeId) return nodes

    return nodes.map((node) => ({
      ...node,
      // 聚焦节点放大并增强发光效果
      symbolSize:
        node.id === focusNodeId ? (node.symbolSize || 40) * 1.3 : node.symbolSize,
      itemStyle:
        node.id === focusNodeId
          ? {
              ...node.itemStyle,
              // 增强阴影发光，不使用边框
              shadowBlur: 25,
              shadowColor: 'rgba(251, 191, 36, 0.7)',
            }
          : node.itemStyle,
    }))
  }, [nodes, focusNodeId])

  const option = useMemo<EChartsOption>(() => {
    const seriesOption: GraphSeriesOption = {
      type: 'graph',
      layout,
      data: processedNodes,
      links: links.map((link) => ({
        ...link,
        symbol: ['none', 'arrow'],
        symbolSize: [0, 8],
      })),
      categories,
      roam,
      draggable,
      // 缩放限制
      scaleLimit: {
        min: 0.2,
        max: 5,
      },
      label: {
        show: true,
        position: 'bottom',
        fontSize: 11,
        color: '#374151',
        formatter: (params) => {
          const name = (params as { name?: string }).name || ''
          // 截断过长的名称
          return name.length > 12 ? name.slice(0, 12) + '...' : name
        },
      },
      edgeLabel: {
        show: true,
        fontSize: 9,
        color: '#6b7280',
        formatter: (params) => {
          const p = params as { data?: { relationLabel?: string } }
          return p.data?.relationLabel || ''
        },
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: {
          width: 2.5,
          color: 'rgba(59, 130, 246, 0.6)',
        },
        itemStyle: {
          shadowBlur: 25,
          shadowColor: 'rgba(59, 130, 246, 0.5)',
        },
        label: {
          fontWeight: 600,
        },
      },
      lineStyle: {
        color: 'rgba(148, 163, 184, 0.45)',
        width: 1.5,
        curveness: 0.15,
      },
    }

    // 力导向布局参数
    if (layout === 'force') {
      seriesOption.force = {
        repulsion,
        gravity,
        edgeLength,
        layoutAnimation: true,
      }
    }

    // 环形布局参数
    if (layout === 'circular') {
      seriesOption.circular = {
        rotateLabel: true,
      }
    }

    return {
      // 设置 grid 背景色为透明，启用整个画布的 roam 响应区域
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: (params) => {
          const p = params as {
            dataType?: string
            data?: GraphNodeData | GraphLinkData
            name?: string
          }
          if (p.dataType === 'node') {
            const node = p.data as GraphNodeData
            const category = categories[node.category]
            return `<strong>${node.name}</strong><br/>类型: ${category?.name || '-'}`
          }
          if (p.dataType === 'edge') {
            const link = p.data as GraphLinkData
            return `${link.source} -> ${link.target}<br/>关系: ${link.relationLabel || '-'}`
          }
          return p.name || ''
        },
      },
      legend: {
        data: categories.map((c) => c.name),
        orient: 'vertical',
        right: 10,
        top: 20,
        itemWidth: 10,
        itemHeight: 10,
        textStyle: { fontSize: 11 },
      },
      series: [seriesOption],
    }
  }, [
    processedNodes,
    links,
    categories,
    layout,
    roam,
    draggable,
    repulsion,
    gravity,
    edgeLength,
  ])

  // 处理图表事件
  const handleChartReady = useCallback(
    (chart: EChartsType) => {
      chartRef.current = chart

      if (onNodeClick) {
        chart.on('click', 'series.graph', (params) => {
          const p = params as {
            dataType?: string
            data?: GraphNodeData
            event?: { offsetX?: number; offsetY?: number }
          }
          if (p.dataType === 'node' && p.data) {
            onNodeClick(p.data, {
              offsetX: p.event?.offsetX ?? 0,
              offsetY: p.event?.offsetY ?? 0,
            })
          }
        })
      }

      if (onNodeDblClick) {
        chart.on('dblclick', 'series.graph', (params) => {
          const p = params as { dataType?: string; data?: GraphNodeData }
          if (p.dataType === 'node' && p.data) {
            onNodeDblClick(p.data)
          }
        })
      }

      // 节点拖动结束后固定位置，防止力导向布局将其拉回
      // 注意：必须使用 dragend 事件而不是 mouseup，因为 mouseup 在画布拖动时也会触发
      // 导致画布拖动功能失效
      if (draggable) {
        chart.on('dragend', (params) => {
          const p = params as {
            dataType?: string
            seriesType?: string
            data?: GraphNodeData & { x?: number; y?: number }
          }
          // 确保是 graph 系列的节点拖动
          if (p.seriesType === 'graph' && p.dataType === 'node' && p.data) {
            const nodeData = p.data
            // 通过 setOption 更新节点的 fixed 状态
            const currentOption = chart.getOption() as { series?: Array<{ data?: GraphNodeData[] }> }
            const seriesData = currentOption.series?.[0]?.data
            if (seriesData && nodeData.id) {
              const nodeIndex = seriesData.findIndex((n) => n.id === nodeData.id)
              if (nodeIndex !== -1 && seriesData[nodeIndex]) {
                const existingNode = seriesData[nodeIndex]
                seriesData[nodeIndex] = {
                  ...existingNode,
                  id: existingNode.id, // 保证 id 存在
                  name: existingNode.name, // 保证 name 存在
                  category: existingNode.category, // 保证 category 存在
                  fixed: true,
                  x: nodeData.x,
                  y: nodeData.y,
                }
                chart.setOption({ series: [{ data: seriesData }] }, false)
              }
            }
          }
        })
      }

      // 通过 ZRender 事件实现整个画布的拖动
      // ECharts graph 系列的 roam 默认只在有图形元素的区域响应
      // 需要自定义事件处理来支持空白区域的拖动
      if (roam === true || roam === 'move') {
        const zr = chart.getZr()

        zr.on('mousedown', (e) => {
          // 只响应左键，且不在节点上（节点有自己的拖动逻辑）
          if (e.which === 1 && !e.target) {
            isDraggingCanvasRef.current = true
            dragStartRef.current = { x: e.offsetX, y: e.offsetY }
            // 获取当前 center，如果没有则使用画布中心
            const currentOption = chart.getOption() as { series?: Array<{ center?: [number, number] }> }
            const chartWidth = chart.getWidth()
            const chartHeight = chart.getHeight()
            centerRef.current = currentOption.series?.[0]?.center || [chartWidth / 2, chartHeight / 2]
          }
        })

        zr.on('mousemove', (e) => {
          if (isDraggingCanvasRef.current && dragStartRef.current && centerRef.current) {
            const dx = e.offsetX - dragStartRef.current.x
            const dy = e.offsetY - dragStartRef.current.y
            // 计算新的 center（反向移动，因为拖动画布是移动视口）
            const newCenter: [number, number] = [
              centerRef.current[0] - dx / zoomRef.current,
              centerRef.current[1] - dy / zoomRef.current,
            ]
            chart.setOption({
              series: [{ center: newCenter }],
            }, false)
            // 更新起始点和 center 以实现连续拖动
            dragStartRef.current = { x: e.offsetX, y: e.offsetY }
            centerRef.current = newCenter
          }
        })

        zr.on('mouseup', () => {
          isDraggingCanvasRef.current = false
          dragStartRef.current = null
        })

        // 鼠标离开画布时也要重置状态
        zr.on('globalout', () => {
          isDraggingCanvasRef.current = false
          dragStartRef.current = null
        })
      }

      onChartReady?.(chart)
    },
    [onNodeClick, onNodeDblClick, onChartReady, draggable, roam]
  )

  // 聚焦节点时触发高亮
  useEffect(() => {
    if (chartRef.current && focusNodeId && processedNodes.length > 0) {
      const focusIndex = processedNodes.findIndex((n) => n.id === focusNodeId)
      if (focusIndex !== -1) {
        // 延迟执行以等待布局稳定
        const timer = setTimeout(() => {
          chartRef.current?.dispatchAction({
            type: 'highlight',
            seriesIndex: 0,
            dataIndex: focusIndex,
          })
        }, 500)
        return () => clearTimeout(timer)
      }
    }
  }, [focusNodeId, processedNodes])

  // 计算容器高度样式
  const containerStyle = typeof height === 'number' ? { height: `${height}px` } : { height }

  return (
    <div className="relative" style={containerStyle}>
      {showToolbar && (
        <div className="absolute left-2 top-2 z-10 flex flex-col gap-1 rounded-md border bg-background/95 p-1 shadow-sm backdrop-blur-sm">
          <button
            type="button"
            onClick={handleZoomIn}
            className="flex h-7 w-7 items-center justify-center rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            title="放大"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={handleZoomOut}
            className="flex h-7 w-7 items-center justify-center rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            title="缩小"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <div className="h-px bg-border" />
          <button
            type="button"
            onClick={handleResetView}
            className="flex h-7 w-7 items-center justify-center rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            title="重置视图"
          >
            <Locate className="h-4 w-4" />
          </button>
        </div>
      )}
      <BaseChart
        option={option}
        style={{ height: '100%' }}
        loading={loading}
        className={className}
        onChartReady={handleChartReady}
        notMerge={false}
      />
    </div>
  )
}
