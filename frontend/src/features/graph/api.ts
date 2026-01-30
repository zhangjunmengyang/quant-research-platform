/**
 * Graph API 客户端
 */

import { apiClient, type ApiResponse } from '@/lib/api/client'
import type {
  GraphNodeType,
  GraphRelationType,
  GetEdgesResponse,
  GraphOverviewResponse,
  LineageResult,
  PathResult,
  TagInfo,
  TaggedEntity,
  EntityTagsResponse,
  CypherQueryRequest,
  CypherQueryResponse,
} from './types'

/**
 * CreateLink Request
 */
export interface CreateLinkRequest {
  sourceType: GraphNodeType
  sourceId: string
  targetType: GraphNodeType
  targetId: string
  relation?: GraphRelationType
  subtype?: string
  isBidirectional?: boolean
  metadata?: Record<string, unknown>
}

/**
 * DeleteLink Request
 */
export interface DeleteLinkRequest {
  sourceType: GraphNodeType
  sourceId: string
  targetType: GraphNodeType
  targetId: string
  relation: GraphRelationType
}

const BASE_URL = '/graph'

export const graphApi = {
  /**
   * 获取图谱概览 (全量数据带限制)
   */
  getOverview: async (nodeLimit = 500, edgeLimit = 1000): Promise<GraphOverviewResponse> => {
    const { data } = await apiClient.get<ApiResponse<GraphOverviewResponse>>(`${BASE_URL}/overview`, {
      params: {
        node_limit: nodeLimit,
        edge_limit: edgeLimit,
      },
    })
    if (!data.success || !data.data) {
      throw new Error(data.error || '获取图谱概览失败')
    }
    return data.data
  },

  /**
   * 获取实体的所有关联边
   */
  getEdges: async (
    entityType: GraphNodeType,
    entityId: string,
    includeBidirectional = true
  ): Promise<GetEdgesResponse> => {
    const { data } = await apiClient.get<ApiResponse<GetEdgesResponse>>(`${BASE_URL}/edges`, {
      params: {
        entity_type: entityType,
        entity_id: entityId,
        include_bidirectional: includeBidirectional,
      },
    })
    if (!data.success || !data.data) {
      throw new Error(data.error || '获取关联失败')
    }
    return data.data
  },

  /**
   * 追溯知识链路
   */
  traceLineage: async (
    entityType: GraphNodeType,
    entityId: string,
    direction: 'forward' | 'backward' = 'backward',
    maxDepth = 5
  ): Promise<LineageResult> => {
    const { data } = await apiClient.get<ApiResponse<LineageResult>>(`${BASE_URL}/lineage`, {
      params: {
        entity_type: entityType,
        entity_id: entityId,
        direction,
        max_depth: maxDepth,
      },
    })
    if (!data.success || !data.data) {
      throw new Error(data.error || '追溯链路失败')
    }
    return data.data
  },

  /**
   * 查找两实体间最短路径
   */
  findPath: async (
    sourceType: GraphNodeType,
    sourceId: string,
    targetType: GraphNodeType,
    targetId: string,
    maxDepth = 5
  ): Promise<PathResult> => {
    const { data } = await apiClient.get<ApiResponse<PathResult>>(`${BASE_URL}/path`, {
      params: {
        source_type: sourceType,
        source_id: sourceId,
        target_type: targetType,
        target_id: targetId,
        max_depth: maxDepth,
      },
    })
    if (!data.success || !data.data) {
      throw new Error(data.error || '查找路径失败')
    }
    return data.data
  },

  /**
   * 获取实体标签
   */
  getEntityTags: async (
    entityType: GraphNodeType,
    entityId: string
  ): Promise<EntityTagsResponse> => {
    const { data } = await apiClient.get<ApiResponse<EntityTagsResponse>>(`${BASE_URL}/tags`, {
      params: {
        entity_type: entityType,
        entity_id: entityId,
      },
    })
    if (!data.success || !data.data) {
      throw new Error(data.error || '获取标签失败')
    }
    return data.data
  },

  /**
   * 列出所有标签
   */
  listAllTags: async (): Promise<TagInfo[]> => {
    const { data } = await apiClient.get<ApiResponse<TagInfo[]>>(`${BASE_URL}/tags/all`)
    if (!data.success || !data.data) {
      throw new Error(data.error || '获取标签列表失败')
    }
    return data.data
  },

  /**
   * 按标签获取实体
   */
  getEntitiesByTag: async (
    tag: string,
    entityType?: GraphNodeType
  ): Promise<TaggedEntity[]> => {
    const { data } = await apiClient.get<ApiResponse<TaggedEntity[]>>(
      `${BASE_URL}/tags/${encodeURIComponent(tag)}/entities`,
      {
        params: entityType ? { entity_type: entityType } : undefined,
      }
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || '获取实体失败')
    }
    return data.data
  },

  /**
   * 执行 Cypher 查询
   */
  executeCypher: async (request: CypherQueryRequest): Promise<CypherQueryResponse> => {
    const { data } = await apiClient.post<ApiResponse<CypherQueryResponse>>(
      `${BASE_URL}/cypher`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Cypher 查询执行失败')
    }
    return data.data
  },

  /**
   * 创建关联
   */
  createLink: async (request: CreateLinkRequest): Promise<void> => {
    const { data } = await apiClient.post<ApiResponse<{ message: string }>>(
      `${BASE_URL}/links`,
      {
        source_type: request.sourceType,
        source_id: request.sourceId,
        target_type: request.targetType,
        target_id: request.targetId,
        relation: request.relation || 'relates',
        subtype: request.subtype || '',
        is_bidirectional: request.isBidirectional,
        metadata: request.metadata || {},
      }
    )
    if (!data.success) {
      throw new Error(data.error || '创建关联失败')
    }
  },

  /**
   * 删除关联
   */
  deleteLink: async (request: DeleteLinkRequest): Promise<void> => {
    const { data } = await apiClient.delete<ApiResponse<{ message: string }>>(
      `${BASE_URL}/links`,
      {
        params: {
          source_type: request.sourceType,
          source_id: request.sourceId,
          target_type: request.targetType,
          target_id: request.targetId,
          relation: request.relation,
        },
      }
    )
    if (!data.success) {
      throw new Error(data.error || '删除关联失败')
    }
  },
}
