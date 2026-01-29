/**
 * Graph 模块类型定义
 *
 * 与后端 graph_hub 数据模型对应。
 */

// ==================== 枚举定义 ====================

/**
 * 节点类型
 */
export type GraphNodeType =
  | 'data'
  | 'factor'
  | 'strategy'
  | 'note'
  | 'research'
  | 'experience'
  | 'tag'

/**
 * 关系类型
 */
export type GraphRelationType =
  | 'derived_from'
  | 'applied_to'
  | 'verifies'
  | 'references'
  | 'summarizes'
  | 'has_tag'
  | 'related'

// ==================== 数据结构 ====================

/**
 * 图边
 */
export interface GraphEdge {
  source_type: GraphNodeType
  source_id: string
  target_type: GraphNodeType
  target_id: string
  relation: GraphRelationType
  is_bidirectional: boolean
  metadata?: Record<string, unknown>
  created_at?: string
}

/**
 * 获取边响应
 */
export interface GetEdgesResponse {
  entity_type: GraphNodeType
  entity_id: string
  count: number
  edges: GraphEdge[]
}

/**
 * 链路节点
 */
export interface LineageNode {
  depth: number
  node_type: GraphNodeType
  node_id: string
  relation: GraphRelationType
  direction: 'forward' | 'backward'
}

/**
 * 链路追溯结果
 */
export interface LineageResult {
  start_type: GraphNodeType
  start_id: string
  direction: 'forward' | 'backward'
  max_depth: number
  count: number
  nodes: LineageNode[]
}

/**
 * 路径元素
 */
export interface PathElement {
  type: 'node' | 'relationship'
  label?: string
  id?: string
  relation?: string
  position: number
}

/**
 * 路径查找结果
 */
export interface PathResult {
  source_type: GraphNodeType
  source_id: string
  target_type: GraphNodeType
  target_id: string
  count: number
  paths: Record<string, unknown>[][]
}

/**
 * 标签信息
 */
export interface TagInfo {
  name: string
  count: number
}

/**
 * 带标签的实体
 */
export interface TaggedEntity {
  entity_type: GraphNodeType
  entity_id: string
}

/**
 * 实体标签响应
 */
export interface EntityTagsResponse {
  entity_type: GraphNodeType
  entity_id: string
  tags: string[]
  count: number
}

/**
 * 图节点 (概览)
 */
export interface GraphNode {
  type: GraphNodeType
  id: string
  degree: number
}

/**
 * 图谱统计信息
 */
export interface GraphOverviewStats {
  total_nodes: number
  total_edges: number
  node_counts: Record<string, number>
  returned_nodes: number
  returned_edges: number
}

/**
 * 概览边 (简化版)
 */
export interface GraphOverviewEdge {
  source_type: GraphNodeType
  source_id: string
  target_type: GraphNodeType
  target_id: string
  relation: GraphRelationType
  is_bidirectional: boolean
}

/**
 * 图谱概览响应
 */
export interface GraphOverviewResponse {
  nodes: GraphNode[]
  edges: GraphOverviewEdge[]
  stats: GraphOverviewStats
}

// ==================== UI 辅助类型 ====================

/**
 * 节点类型显示配置
 */
export interface NodeTypeConfig {
  label: string
  color: string
  icon: string
  getRoute: (id: string) => string
}

/**
 * 节点类型配置映射
 */
export const NODE_TYPE_CONFIG: Record<GraphNodeType, NodeTypeConfig> = {
  data: {
    label: '数据',
    color: '#10b981', // emerald
    icon: 'Database',
    getRoute: () => '/data',
  },
  factor: {
    label: '因子',
    color: '#3b82f6', // blue
    icon: 'FlaskConical',
    getRoute: (id) => `/factors?focus=${encodeURIComponent(id)}`,
  },
  strategy: {
    label: '策略',
    color: '#8b5cf6', // violet
    icon: 'Target',
    getRoute: (id) => `/strategies/${encodeURIComponent(id)}`,
  },
  note: {
    label: '笔记',
    color: '#f59e0b', // amber
    icon: 'BookOpen',
    getRoute: (id) => `/notes/${encodeURIComponent(id)}`,
  },
  research: {
    label: '研报',
    color: '#ef4444', // red
    icon: 'FileText',
    getRoute: (id) => `/research/${encodeURIComponent(id)}`,
  },
  experience: {
    label: '经验',
    color: '#ec4899', // pink
    icon: 'Lightbulb',
    getRoute: (id) => `/experiences?focus=${encodeURIComponent(id)}`,
  },
  tag: {
    label: '标签',
    color: '#6b7280', // gray
    icon: 'Tag',
    getRoute: (name) => `/graph?tag=${encodeURIComponent(name)}`,
  },
}

/**
 * 关系类型显示名称
 */
export const RELATION_TYPE_LABELS: Record<GraphRelationType, string> = {
  derived_from: '派生自',
  applied_to: '应用于',
  verifies: '验证',
  references: '引用',
  summarizes: '总结为',
  has_tag: '拥有标签',
  related: '关联',
}

/**
 * 解析节点 key (格式: type:id)
 */
export function parseNodeKey(key: string): { type: GraphNodeType; id: string } {
  const colonIndex = key.indexOf(':')
  if (colonIndex === -1) {
    return { type: 'data', id: key }
  }
  return {
    type: key.substring(0, colonIndex) as GraphNodeType,
    id: key.substring(colonIndex + 1),
  }
}

/**
 * 构建节点 key
 */
export function buildNodeKey(type: GraphNodeType, id: string): string {
  return `${type}:${id}`
}
