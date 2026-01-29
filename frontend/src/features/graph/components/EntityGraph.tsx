/**
 * Entity Graph Component
 * 实体关联子图组件 - 用于详情页内嵌展示
 *
 * 功能:
 * - 以当前实体为中心展示关联
 * - 点击中心实体不跳转
 * - 点击周围实体跳转到对应详情页
 * - 提供「在大图中查看」按钮
 */

import { useMemo, useCallback, useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { ExternalLink, Loader2, Network, Maximize2, Minimize2 } from 'lucide-react'
import {
  GraphChart,
  type GraphNodeData,
  type GraphLinkData,
  type GraphCategoryData,
} from '@/components/charts/GraphChart'
import { useEntityEdges } from '../hooks'
import {
  NODE_TYPE_CONFIG,
  RELATION_TYPE_LABELS,
  type GraphNodeType,
  buildNodeKey,
  parseNodeKey,
} from '../types'
import { createNodeStyle, createLinkStyle } from '../utils/graphStyles'
import { Button } from '@/components/ui/button'
import { NodePreviewCard } from './NodePreviewCard'

// 稳定的配置常量，避免每次渲染创建新引用
const EDGE_LENGTH_NORMAL: [number, number] = [60, 120]
const EDGE_LENGTH_FULLSCREEN: [number, number] = [80, 180]

interface EntityGraphProps {
  entityType: GraphNodeType
  entityId: string
  entityName?: string // 中心实体显示名称
  height?: number
  className?: string
  showViewInGraph?: boolean // 是否显示「在大图中查看」按钮
}

export function EntityGraph({
  entityType,
  entityId,
  entityName,
  height = 350,
  className,
  showViewInGraph = true,
}: EntityGraphProps) {
  const navigate = useNavigate()
  const [isFullscreen, setIsFullscreen] = useState(false)
  const { data: edgesData, isLoading, isError } = useEntityEdges(entityType, entityId)

  // 预览卡片状态
  const graphContainerRef = useRef<HTMLDivElement>(null)
  const fullscreenContainerRef = useRef<HTMLDivElement>(null)
  const [previewState, setPreviewState] = useState<{
    nodeKey: string
    position: { x: number; y: number }
  } | null>(null)

  // 构建图数据
  const { nodes, links, categories } = useMemo(() => {
    if (!edgesData || edgesData.edges.length === 0) {
      return { nodes: [], links: [], categories: [] }
    }

    const nodeMap = new Map<string, GraphNodeData>()
    const linkList: GraphLinkData[] = []
    const categorySet = new Set<GraphNodeType>()

    // 添加中心节点
    const centerKey = buildNodeKey(entityType, entityId)
    categorySet.add(entityType)
    nodeMap.set(centerKey, {
      id: centerKey,
      name: entityName || entityId,
      category: 0, // 后面重新计算
      symbolSize: 45, // 中心节点更大
      itemStyle: createNodeStyle(NODE_TYPE_CONFIG[entityType].color, { isCenter: true }),
    })

    // 处理边，添加关联节点
    for (const edge of edgesData.edges) {
      const isSource =
        edge.source_type === entityType && edge.source_id === entityId
      const otherType = isSource ? edge.target_type : edge.source_type
      const otherId = isSource ? edge.target_id : edge.source_id
      const otherKey = buildNodeKey(otherType, otherId)

      categorySet.add(otherType as GraphNodeType)

      if (!nodeMap.has(otherKey)) {
        // 显示名称处理
        let displayName = otherId
        // 对于 factor 类型，去掉 .py 后缀
        if (otherType === 'factor' && displayName.endsWith('.py')) {
          displayName = displayName.slice(0, -3)
        }

        const nodeColor = NODE_TYPE_CONFIG[otherType as GraphNodeType]?.color || '#6b7280'
        nodeMap.set(otherKey, {
          id: otherKey,
          name: displayName,
          category: 0, // 后面重新计算
          symbolSize: 30,
          itemStyle: createNodeStyle(nodeColor),
        })
      }

      linkList.push({
        source: buildNodeKey(edge.source_type, edge.source_id),
        target: buildNodeKey(edge.target_type, edge.target_id),
        relationLabel: RELATION_TYPE_LABELS[edge.relation] || edge.relation,
        lineStyle: createLinkStyle(),
      })
    }

    // 构建 categories 并更新节点的 category 索引
    const categoryList: GraphCategoryData[] = []
    const categoryIndexMap = new Map<GraphNodeType, number>()

    Array.from(categorySet).forEach((type, index) => {
      categoryIndexMap.set(type, index)
      categoryList.push({
        name: NODE_TYPE_CONFIG[type]?.label || type,
        itemStyle: { color: NODE_TYPE_CONFIG[type]?.color },
      })
    })

    // 更新节点 category
    nodeMap.forEach((node) => {
      const { type } = parseNodeKey(node.id)
      node.category = categoryIndexMap.get(type) || 0
    })

    return {
      nodes: Array.from(nodeMap.values()),
      links: linkList,
      categories: categoryList,
    }
  }, [edgesData, entityType, entityId, entityName])

  // 节点点击处理 - 显示预览卡片
  const handleNodeClick = useCallback(
    (node: GraphNodeData, event: { offsetX: number; offsetY: number }) => {
      const { type, id } = parseNodeKey(node.id)

      // 中心节点不显示预览卡片
      if (type === entityType && id === entityId) {
        return
      }

      setPreviewState({
        nodeKey: node.id,
        position: { x: event.offsetX, y: event.offsetY },
      })
    },
    [entityType, entityId]
  )

  // 跳转到大图
  const handleViewInGraph = useCallback(() => {
    navigate(`/graph?focus=${encodeURIComponent(buildNodeKey(entityType, entityId))}`)
  }, [navigate, entityType, entityId])

  // 关闭预览卡片
  const handleClosePreview = useCallback(() => {
    setPreviewState(null)
  }, [])

  // 从预览卡片跳转详情
  const handlePreviewViewDetail = useCallback(() => {
    if (!previewState) return
    const { type, id } = parseNodeKey(previewState.nodeKey)
    const config = NODE_TYPE_CONFIG[type]
    if (config) {
      navigate(config.getRoute(id))
    }
    setPreviewState(null)
  }, [previewState, navigate])

  // 从预览卡片跳转到大图查看该节点
  const handlePreviewViewInGraph = useCallback(() => {
    if (!previewState) return
    navigate(`/graph?focus=${encodeURIComponent(previewState.nodeKey)}`)
    setPreviewState(null)
  }, [previewState, navigate])

  // ESC 键退出全屏 - 必须在条件返回之前调用
  useEffect(() => {
    if (!isFullscreen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsFullscreen(false)
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isFullscreen])

  if (isLoading) {
    return (
      <div
        className={`flex items-center justify-center rounded-lg border bg-card ${className}`}
        style={{ height }}
      >
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (isError || nodes.length === 0) {
    return (
      <div
        className={`flex flex-col items-center justify-center rounded-lg border bg-card text-muted-foreground ${className}`}
        style={{ height }}
      >
        <Network className="h-8 w-8 mb-2 opacity-50" />
        <p className="text-sm">暂无关联数据</p>
      </div>
    )
  }

  // 全屏模式 - 使用 Portal 渲染到 body
  // 注意：全屏和非全屏使用独立的 GraphChart 实例，避免 Portal 切换导致组件重建
  if (isFullscreen) {
    const fullscreenContent = (
      <div
        className="fixed inset-0 bg-background flex flex-col"
        style={{ zIndex: 9999 }}
      >
        {/* 顶部工具栏 */}
        <div className="flex items-center justify-between px-4 py-2 border-b bg-card shrink-0">
          <h4 className="text-sm font-medium flex items-center gap-1.5">
            <Network className="h-4 w-4 text-muted-foreground" />
            知识关联
            <span className="text-muted-foreground font-normal">
              ({edgesData?.count || 0})
            </span>
          </h4>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">ESC 退出</span>
            {showViewInGraph && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={handleViewInGraph}
              >
                <ExternalLink className="h-3 w-3 mr-1" />
                在大图中查看
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => setIsFullscreen(false)}
            >
              <Minimize2 className="h-3 w-3 mr-1" />
              退出全屏
            </Button>
          </div>
        </div>
        {/* 画布区域 - 完全填充 */}
        <div ref={fullscreenContainerRef} className="flex-1 min-h-0 relative">
          <GraphChart
            nodes={nodes}
            links={links}
            categories={categories}
            height="100%"
            layout="force"
            roam={true}
            draggable={true}
            repulsion={400}
            gravity={0.08}
            edgeLength={EDGE_LENGTH_FULLSCREEN}
            onNodeClick={handleNodeClick}
            showToolbar={true}
          />

          {/* 节点预览卡片 */}
          {previewState && (
            <NodePreviewCard
              nodeKey={previewState.nodeKey}
              position={previewState.position}
              containerRect={fullscreenContainerRef.current?.getBoundingClientRect() ?? null}
              onClose={handleClosePreview}
              onViewDetail={handlePreviewViewDetail}
              onExpandInGraph={handlePreviewViewInGraph}
            />
          )}
        </div>
      </div>
    )

    return (
      <>
        {/* 占位元素保持原有布局 */}
        <div className={className} style={{ height: height + 32 }} />
        {/* Portal 渲染到 body */}
        {createPortal(fullscreenContent, document.body)}
      </>
    )
  }

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium flex items-center gap-1.5">
          <Network className="h-4 w-4 text-muted-foreground" />
          知识关联
          <span className="text-muted-foreground font-normal">
            ({edgesData?.count || 0})
          </span>
        </h4>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => setIsFullscreen(true)}
            title="全屏查看"
          >
            <Maximize2 className="h-3 w-3" />
          </Button>
          {showViewInGraph && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={handleViewInGraph}
            >
              <ExternalLink className="h-3 w-3 mr-1" />
              在大图中查看
            </Button>
          )}
        </div>
      </div>
      <div
        ref={graphContainerRef}
        className="rounded-lg border bg-card overflow-hidden relative"
        style={{ touchAction: 'none', overscrollBehavior: 'contain' }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <GraphChart
          nodes={nodes}
          links={links}
          categories={categories}
          height={height}
          layout="force"
          roam={true}
          draggable={true}
          repulsion={250}
          gravity={0.15}
          edgeLength={EDGE_LENGTH_NORMAL}
          onNodeClick={handleNodeClick}
          showToolbar={true}
        />

        {/* 节点预览卡片 */}
        {previewState && (
          <NodePreviewCard
            nodeKey={previewState.nodeKey}
            position={previewState.position}
            containerRect={graphContainerRef.current?.getBoundingClientRect() ?? null}
            onClose={handleClosePreview}
            onViewDetail={handlePreviewViewDetail}
            onExpandInGraph={handlePreviewViewInGraph}
          />
        )}
      </div>
    </div>
  )
}
