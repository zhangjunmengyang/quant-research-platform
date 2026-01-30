/**
 * Graph Explorer Component
 * 知识图谱全局探索组件
 *
 * 功能:
 * - 全局图谱可视化
 * - 节点类型筛选
 * - 搜索定位
 * - 聚焦节点高亮
 * - 链路追溯视图
 */

import { useState, useMemo, useCallback, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Search,
  Filter,
  Network,
  ArrowLeft,
  ArrowRight,
  RefreshCw,
  Loader2,
  X,
  Terminal,
  Tag,
} from 'lucide-react'
import {
  GraphChart,
  type GraphNodeData,
  type GraphLinkData,
  type GraphCategoryData,
} from '@/components/charts/GraphChart'
import {
  useEntityEdges,
  useLineage,
  useAllTags,
  useEntitiesByTag,
  useGraphOverview,
  useCypherQuery,
} from '../hooks'
import {
  NODE_TYPE_CONFIG,
  RELATION_TYPE_LABELS,
  type GraphNodeType,
  type CypherQueryResponse,
  buildNodeKey,
  parseNodeKey,
} from '../types'
import { createNodeStyle, createLinkStyle } from '../utils/graphStyles'
import { NodePreviewCard } from './NodePreviewCard'
import { CypherEditor } from './CypherEditor'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Collapsible, CollapsibleContent } from '@/components/ui/collapsible'
import { cn } from '@/lib/utils'

interface GraphExplorerProps {
  className?: string
}

// 可筛选的实体类型（排除 data 和 tag）
const FILTERABLE_TYPES: GraphNodeType[] = [
  'factor',
  'strategy',
  'note',
  'research',
  'experience',
]

// 稳定的 GraphChart 配置常量
const GRAPH_EDGE_LENGTH: [number, number] = [100, 300]

export function GraphExplorer({ className }: GraphExplorerProps) {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  // URL 参数
  const focusParam = searchParams.get('focus') // 格式: type:id
  const tagParam = searchParams.get('tag')

  // 解析聚焦节点
  const focusEntity = useMemo(() => {
    if (!focusParam) return null
    return parseNodeKey(focusParam)
  }, [focusParam])

  // 状态
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTypes, setSelectedTypes] = useState<Set<GraphNodeType>>(
    new Set(FILTERABLE_TYPES)
  )
  const [viewMode, setViewMode] = useState<'graph' | 'lineage'>('graph')
  const [lineageDirection, setLineageDirection] = useState<'forward' | 'backward'>(
    'backward'
  )

  // 预览卡片状态
  const graphContainerRef = useRef<HTMLDivElement>(null)
  const [previewState, setPreviewState] = useState<{
    nodeKey: string
    position: { x: number; y: number }
  } | null>(null)

  // Cypher 查询状态
  const [cypherPanelOpen, setCypherPanelOpen] = useState(false)
  const [cypherResult, setCypherResult] = useState<CypherQueryResponse | null>(null)
  const cypherMutation = useCypherQuery()

  // 数据获取
  // 1. 全量概览 (无聚焦时使用)
  const { data: overviewData, isLoading: overviewLoading } = useGraphOverview(500, 1000)

  // 2. 聚焦实体的边
  const {
    data: edgesData,
    isLoading: edgesLoading,
    refetch: refetchEdges,
  } = useEntityEdges(focusEntity?.type || null, focusEntity?.id || null, {
    enabled: !!focusEntity,
  })

  // 3. 链路追溯
  const { data: lineageData, isLoading: lineageLoading } = useLineage(
    viewMode === 'lineage' && focusEntity ? focusEntity.type : null,
    viewMode === 'lineage' && focusEntity ? focusEntity.id : null,
    lineageDirection
  )

  const { data: allTags } = useAllTags()
  const { data: tagEntities } = useEntitiesByTag(tagParam)

  // 构建图数据
  const { nodes, links, categories } = useMemo(() => {
    const nodeMap = new Map<string, GraphNodeData>()
    const linkList: GraphLinkData[] = []
    const categorySet = new Set<GraphNodeType>()

    // 根据视图模式和数据源构建图
    if (viewMode === 'lineage' && lineageData && focusEntity) {
      // 链路视图
      const entityKey = buildNodeKey(lineageData.start_type, lineageData.start_id)
      categorySet.add(lineageData.start_type as GraphNodeType)

      const startColor = NODE_TYPE_CONFIG[lineageData.start_type as GraphNodeType]?.color || '#6b7280'
      nodeMap.set(entityKey, {
        id: entityKey,
        name: lineageData.start_id,
        category: 0,
        symbolSize: 50,
        itemStyle: createNodeStyle(startColor, { isCenter: true }),
      })

      // 按深度组织节点
      const nodesByDepth = new Map<number, typeof lineageData.nodes>()
      for (const node of lineageData.nodes) {
        const depthNodes = nodesByDepth.get(node.depth) || []
        depthNodes.push(node)
        nodesByDepth.set(node.depth, depthNodes)
      }

      // 添加链路节点
      let prevDepthNodes: string[] = [entityKey]
      for (let depth = 1; depth <= lineageData.max_depth; depth++) {
        const currentDepthNodes = nodesByDepth.get(depth) || []
        const currentKeys: string[] = []

        for (const node of currentDepthNodes) {
          const nodeKey = buildNodeKey(node.node_type, node.node_id)
          categorySet.add(node.node_type as GraphNodeType)
          currentKeys.push(nodeKey)

          if (!nodeMap.has(nodeKey)) {
            const nodeColor = NODE_TYPE_CONFIG[node.node_type as GraphNodeType]?.color || '#6b7280'
            nodeMap.set(nodeKey, {
              id: nodeKey,
              name: node.node_id,
              category: 0,
              symbolSize: Math.max(20, 45 - depth * 8),
              itemStyle: createNodeStyle(nodeColor),
            })
          }

          // 连接到上一层（简化：连接到中心）
          if (prevDepthNodes.length > 0 && prevDepthNodes[0]) {
            const sourceKey =
              lineageDirection === 'backward' ? nodeKey : prevDepthNodes[0]
            const targetKey =
              lineageDirection === 'backward' ? prevDepthNodes[0] : nodeKey
            linkList.push({
              source: sourceKey,
              target: targetKey,
              relationLabel: RELATION_TYPE_LABELS[node.relation],
              lineStyle: createLinkStyle(),
            })
          }
        }

        if (currentKeys.length > 0) {
          prevDepthNodes = currentKeys
        }
      }
    } else if (edgesData && focusEntity) {
      // 普通图视图
      const centerKey = buildNodeKey(edgesData.entity_type, edgesData.entity_id)
      categorySet.add(edgesData.entity_type as GraphNodeType)

      const centerColor = NODE_TYPE_CONFIG[edgesData.entity_type as GraphNodeType]?.color || '#6b7280'
      nodeMap.set(centerKey, {
        id: centerKey,
        name: edgesData.entity_id,
        category: 0,
        symbolSize: 50,
        itemStyle: createNodeStyle(centerColor, { isCenter: true }),
      })

      for (const edge of edgesData.edges) {
        const srcKey = buildNodeKey(edge.source_type, edge.source_id)
        const tgtKey = buildNodeKey(edge.target_type, edge.target_id)

        categorySet.add(edge.source_type as GraphNodeType)
        categorySet.add(edge.target_type as GraphNodeType)

        if (!nodeMap.has(srcKey)) {
          const srcColor = NODE_TYPE_CONFIG[edge.source_type as GraphNodeType]?.color || '#6b7280'
          nodeMap.set(srcKey, {
            id: srcKey,
            name: edge.source_id,
            category: 0,
            symbolSize: 35,
            itemStyle: createNodeStyle(srcColor),
          })
        }

        if (!nodeMap.has(tgtKey)) {
          const tgtColor = NODE_TYPE_CONFIG[edge.target_type as GraphNodeType]?.color || '#6b7280'
          nodeMap.set(tgtKey, {
            id: tgtKey,
            name: edge.target_id,
            category: 0,
            symbolSize: 35,
            itemStyle: createNodeStyle(tgtColor),
          })
        }

        linkList.push({
          source: srcKey,
          target: tgtKey,
          relationLabel: RELATION_TYPE_LABELS[edge.relation],
          lineStyle: createLinkStyle(),
        })
      }
    }

    // 按标签筛选时添加节点
    if (tagEntities && !focusEntity) {
      for (const entity of tagEntities) {
        const key = buildNodeKey(entity.entity_type, entity.entity_id)
        categorySet.add(entity.entity_type as GraphNodeType)

        if (!nodeMap.has(key)) {
          const entityColor = NODE_TYPE_CONFIG[entity.entity_type as GraphNodeType]?.color || '#6b7280'
          nodeMap.set(key, {
            id: key,
            name: entity.entity_id,
            category: 0,
            symbolSize: 35,
            itemStyle: createNodeStyle(entityColor),
          })
        }
      }
    }

    // 全量概览 (无聚焦、无标签筛选时)
    if (overviewData && !focusEntity && !tagParam) {
      // 添加节点
      for (const node of overviewData.nodes) {
        const key = buildNodeKey(node.type, node.id)
        categorySet.add(node.type as GraphNodeType)

        if (!nodeMap.has(key)) {
          const nodeColor = NODE_TYPE_CONFIG[node.type as GraphNodeType]?.color || '#6b7280'
          // 根据连接度设置节点大小
          const size = Math.min(50, Math.max(20, 15 + node.degree * 3))
          nodeMap.set(key, {
            id: key,
            name: node.id,
            category: 0,
            symbolSize: size,
            itemStyle: createNodeStyle(nodeColor),
          })
        }
      }

      // 添加边
      for (const edge of overviewData.edges) {
        const srcKey = buildNodeKey(edge.source_type, edge.source_id)
        const tgtKey = buildNodeKey(edge.target_type, edge.target_id)

        linkList.push({
          source: srcKey,
          target: tgtKey,
          relationLabel: RELATION_TYPE_LABELS[edge.relation],
          lineStyle: createLinkStyle(),
        })
      }
    }

    // Cypher 查询结果 (优先级最高)
    if (cypherResult && cypherResult.nodes.length > 0) {
      // 清空之前的数据，使用 Cypher 结果
      nodeMap.clear()
      linkList.length = 0
      categorySet.clear()

      for (const node of cypherResult.nodes) {
        const key = buildNodeKey(node.type, node.id)
        categorySet.add(node.type as GraphNodeType)

        if (!nodeMap.has(key)) {
          const nodeColor = NODE_TYPE_CONFIG[node.type as GraphNodeType]?.color || '#6b7280'
          nodeMap.set(key, {
            id: key,
            name: node.id,
            category: 0,
            symbolSize: 35,
            itemStyle: createNodeStyle(nodeColor),
          })
        }
      }

      for (const edge of cypherResult.edges) {
        const srcKey = buildNodeKey(edge.source_type, edge.source_id)
        const tgtKey = buildNodeKey(edge.target_type, edge.target_id)

        linkList.push({
          source: srcKey,
          target: tgtKey,
          relationLabel: RELATION_TYPE_LABELS[edge.relation] || edge.relation,
          lineStyle: createLinkStyle(),
        })
      }
    }

    // 类型筛选
    const filteredNodes = Array.from(nodeMap.values()).filter((node) => {
      const { type } = parseNodeKey(node.id)
      // data 和 tag 类型不参与筛选
      if (type === 'data' || type === 'tag') return true
      return selectedTypes.has(type)
    })

    // 构建 categories
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
    filteredNodes.forEach((node) => {
      const { type } = parseNodeKey(node.id)
      node.category = categoryIndexMap.get(type) || 0
    })

    // 过滤边（两端节点都在筛选结果中）
    const nodeIds = new Set(filteredNodes.map((n) => n.id))
    const filteredLinks = linkList.filter(
      (link) => nodeIds.has(link.source) && nodeIds.has(link.target)
    )

    return {
      nodes: filteredNodes,
      links: filteredLinks,
      categories: categoryList,
    }
  }, [edgesData, lineageData, tagEntities, overviewData, selectedTypes, viewMode, focusEntity, lineageDirection, tagParam, cypherResult])

  // 节点点击 - 显示预览卡片
  const handleNodeClick = useCallback(
    (node: GraphNodeData, event: { offsetX: number; offsetY: number }) => {
      setPreviewState({
        nodeKey: node.id,
        position: { x: event.offsetX, y: event.offsetY },
      })
    },
    []
  )

  // 节点双击 - 跳转详情
  const handleNodeDblClick = useCallback(
    (node: GraphNodeData) => {
      const { type, id } = parseNodeKey(node.id)
      // 检查 id 是否有效
      if (!id) {
        console.warn('Invalid node id for navigation:', node.id)
        return
      }
      const config = NODE_TYPE_CONFIG[type]
      if (config) {
        navigate(config.getRoute(id))
      }
    },
    [navigate]
  )

  // 关闭预览卡片
  const handleClosePreview = useCallback(() => {
    setPreviewState(null)
  }, [])

  // 从预览卡片跳转详情
  const handleViewDetail = useCallback(() => {
    if (!previewState) return
    const { type, id } = parseNodeKey(previewState.nodeKey)
    // 检查 id 是否有效
    if (!id) {
      console.warn('Invalid node id for navigation:', previewState.nodeKey)
      setPreviewState(null)
      return
    }
    const config = NODE_TYPE_CONFIG[type]
    if (config) {
      navigate(config.getRoute(id))
    }
    setPreviewState(null)
  }, [previewState, navigate])

  // 类型筛选切换
  const toggleType = (type: GraphNodeType) => {
    const newSet = new Set(selectedTypes)
    if (newSet.has(type)) {
      newSet.delete(type)
    } else {
      newSet.add(type)
    }
    setSelectedTypes(newSet)
  }

  // 清除聚焦
  const clearFocus = () => {
    const newParams = new URLSearchParams(searchParams)
    newParams.delete('focus')
    setSearchParams(newParams)
  }

  // 清除标签筛选
  const clearTag = () => {
    const newParams = new URLSearchParams(searchParams)
    newParams.delete('tag')
    setSearchParams(newParams)
  }

  // 清除 Cypher 结果
  const clearCypherResult = useCallback(() => {
    setCypherResult(null)
  }, [])

  // 执行 Cypher 查询
  const handleCypherExecute = useCallback(
    async (query: string) => {
      try {
        const result = await cypherMutation.mutateAsync({ query })
        setCypherResult(result)
        // 清除聚焦和标签筛选，显示 Cypher 结果
        const newParams = new URLSearchParams()
        setSearchParams(newParams)
      } catch {
        // 错误已由 mutation 处理
      }
    },
    [cypherMutation, setSearchParams]
  )

  const isLoading = overviewLoading || edgesLoading || lineageLoading || cypherMutation.isPending

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* 工具栏 */}
      <div className="flex items-center gap-4 p-4 border-b bg-card flex-wrap">
        {/* 搜索 */}
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索节点 ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && searchQuery.trim()) {
                // 简单搜索：假设是 factor
                setSearchParams({ focus: `factor:${searchQuery.trim()}` })
              }
            }}
            className="pl-9"
          />
        </div>

        {/* 类型筛选 */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          {FILTERABLE_TYPES.map((type) => {
            const config = NODE_TYPE_CONFIG[type]
            return (
              <button
                key={type}
                onClick={() => toggleType(type)}
                className={cn(
                  'px-2 py-1 text-xs rounded-full transition-colors',
                  selectedTypes.has(type)
                    ? 'text-white'
                    : 'bg-muted text-muted-foreground'
                )}
                style={{
                  backgroundColor: selectedTypes.has(type)
                    ? config.color
                    : undefined,
                }}
              >
                {config.label}
              </button>
            )
          })}
        </div>

        {/* 视图模式 */}
        {focusEntity && (
          <div className="flex items-center gap-1 border rounded-md p-1">
            <button
              onClick={() => setViewMode('graph')}
              className={cn(
                'px-2 py-1 text-xs rounded transition-colors',
                viewMode === 'graph'
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted'
              )}
            >
              关联图
            </button>
            <button
              onClick={() => setViewMode('lineage')}
              className={cn(
                'px-2 py-1 text-xs rounded transition-colors',
                viewMode === 'lineage'
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted'
              )}
            >
              链路追溯
            </button>
          </div>
        )}

        {/* 链路方向 */}
        {viewMode === 'lineage' && focusEntity && (
          <div className="flex items-center gap-1">
            <button
              onClick={() => setLineageDirection('backward')}
              className={cn(
                'p-1.5 rounded transition-colors',
                lineageDirection === 'backward'
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted'
              )}
              title="向上追溯源头"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setLineageDirection('forward')}
              className={cn(
                'p-1.5 rounded transition-colors',
                lineageDirection === 'forward'
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted'
              )}
              title="向下追溯影响"
            >
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* 刷新 */}
        {focusEntity && (
          <Button variant="ghost" size="sm" onClick={() => refetchEdges()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        )}

        {/* 聚焦信息 - Badge 形式 */}
        {focusEntity && (
          <Badge variant="outline" className="gap-1.5 pl-1.5 pr-1">
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: NODE_TYPE_CONFIG[focusEntity.type]?.color }}
            />
            <span className="text-muted-foreground text-xs">聚焦</span>
            <span className="font-medium">{focusEntity.id}</span>
            <button
              className="ml-0.5 rounded-sm hover:bg-muted p-0.5"
              onClick={clearFocus}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        )}

        {/* 标签筛选 - Badge 形式 */}
        {tagParam && (
          <Badge variant="secondary" className="gap-1.5 pr-1">
            <Tag className="h-3 w-3" />
            <span>{tagParam}</span>
            <button
              className="ml-0.5 rounded-sm hover:bg-muted/50 p-0.5"
              onClick={clearTag}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        )}

        {/* Cypher 结果提示 */}
        {cypherResult && (
          <Badge variant="info" className="gap-1.5 pr-1">
            <Terminal className="h-3 w-3" />
            <span>Cypher: {cypherResult.record_count} 条</span>
            <button
              className="ml-0.5 rounded-sm hover:bg-info/20 p-0.5"
              onClick={clearCypherResult}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        )}

        {/* Cypher 查询按钮 */}
        <Button
          variant={cypherPanelOpen ? 'secondary' : 'outline'}
          size="sm"
          onClick={() => setCypherPanelOpen(!cypherPanelOpen)}
        >
          <Terminal className="h-4 w-4 mr-1" />
          Cypher
        </Button>

        {/* 统计信息 */}
        {!focusEntity && !tagParam && !cypherResult && overviewData && (
          <div className="ml-auto text-xs text-muted-foreground">
            {overviewData.stats.returned_nodes} 节点 / {overviewData.stats.returned_edges} 边
            {overviewData.stats.total_nodes > overviewData.stats.returned_nodes && (
              <span className="ml-1">
                (共 {overviewData.stats.total_nodes})
              </span>
            )}
          </div>
        )}
      </div>

      {/* Cypher 查询面板 */}
      <Collapsible open={cypherPanelOpen}>
        <CollapsibleContent className="border-b bg-muted/30">
          <div className="p-4">
            <CypherEditor
              onExecute={handleCypherExecute}
              isLoading={cypherMutation.isPending}
              error={cypherMutation.error?.message}
              executionTime={cypherResult?.execution_time_ms}
            />
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* 图表区域 */}
      <div ref={graphContainerRef} className="flex-1 relative">
        {isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-background/50">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : nodes.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
            <Network className="h-12 w-12 mb-4 opacity-50" />
            <p className="text-lg font-medium">
              {focusEntity ? '暂无关联数据' : '知识图谱为空'}
            </p>
            <p className="text-sm mt-1">
              {focusEntity
                ? '该实体暂无关联数据'
                : '图谱中还没有节点，请先添加数据'}
            </p>
          </div>
        ) : (
          <GraphChart
            nodes={nodes}
            links={links}
            categories={categories}
            height="100%"
            layout="force"
            roam={true}
            draggable={true}
            repulsion={600}
            gravity={0.05}
            edgeLength={GRAPH_EDGE_LENGTH}
            onNodeClick={handleNodeClick}
            onNodeDblClick={handleNodeDblClick}
            focusNodeId={
              focusEntity ? buildNodeKey(focusEntity.type, focusEntity.id) : undefined
            }
          />
        )}

        {/* 节点预览卡片 */}
        {previewState && (
          <NodePreviewCard
            nodeKey={previewState.nodeKey}
            position={previewState.position}
            containerRect={graphContainerRef.current?.getBoundingClientRect() ?? null}
            onClose={handleClosePreview}
            onViewDetail={handleViewDetail}
          />
        )}
      </div>

      {/* 标签侧边栏 */}
      {allTags && allTags.length > 0 && (
        <div className="absolute right-4 bottom-4 w-48 max-h-64 overflow-auto rounded-lg border bg-card shadow-lg p-3">
          <h4 className="text-xs font-medium text-muted-foreground mb-2">标签</h4>
          <div className="flex flex-wrap gap-1">
            {allTags.slice(0, 20).map((tag, index) => (
              <button
                key={`${tag.name}-${index}`}
                onClick={() => {
                  const newParams = new URLSearchParams()
                  newParams.set('tag', tag.name)
                  setSearchParams(newParams)
                }}
                className={cn(
                  'px-2 py-0.5 text-xs rounded-full transition-colors',
                  tagParam === tag.name
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted hover:bg-muted/80'
                )}
              >
                {tag.name} ({tag.count})
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
