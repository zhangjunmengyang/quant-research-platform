/**
 * Graph React Query Hooks
 */

import { useQuery, useMutation } from '@tanstack/react-query'
import { graphApi } from './api'
import type { GraphNodeType } from './types'

// Query Keys
export const graphKeys = {
  all: ['graph'] as const,
  overview: (nodeLimit: number, edgeLimit: number) =>
    [...graphKeys.all, 'overview', nodeLimit, edgeLimit] as const,
  edges: (entityType: GraphNodeType, entityId: string) =>
    [...graphKeys.all, 'edges', entityType, entityId] as const,
  lineage: (entityType: GraphNodeType, entityId: string, direction: string) =>
    [...graphKeys.all, 'lineage', entityType, entityId, direction] as const,
  path: (
    sourceType: GraphNodeType,
    sourceId: string,
    targetType: GraphNodeType,
    targetId: string
  ) => [...graphKeys.all, 'path', sourceType, sourceId, targetType, targetId] as const,
  entityTags: (entityType: GraphNodeType, entityId: string) =>
    [...graphKeys.all, 'entityTags', entityType, entityId] as const,
  allTags: () => [...graphKeys.all, 'allTags'] as const,
  entitiesByTag: (tag: string, entityType?: GraphNodeType) =>
    [...graphKeys.all, 'entitiesByTag', tag, entityType] as const,
}

const DEFAULT_STALE_TIME = 5 * 60 * 1000 // 5 分钟

/**
 * Hook: 获取图谱概览 (全量数据带限制)
 */
export function useGraphOverview(nodeLimit = 500, edgeLimit = 1000) {
  return useQuery({
    queryKey: graphKeys.overview(nodeLimit, edgeLimit),
    queryFn: () => graphApi.getOverview(nodeLimit, edgeLimit),
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook: 获取实体的关联边
 */
export function useEntityEdges(
  entityType: GraphNodeType | null,
  entityId: string | null,
  options?: { enabled?: boolean; includeBidirectional?: boolean }
) {
  return useQuery({
    queryKey: graphKeys.edges(entityType!, entityId!),
    queryFn: () =>
      graphApi.getEdges(entityType!, entityId!, options?.includeBidirectional ?? true),
    enabled: !!entityType && !!entityId && (options?.enabled !== false),
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook: 追溯知识链路
 */
export function useLineage(
  entityType: GraphNodeType | null,
  entityId: string | null,
  direction: 'forward' | 'backward' = 'backward',
  maxDepth = 5
) {
  return useQuery({
    queryKey: graphKeys.lineage(entityType!, entityId!, direction),
    queryFn: () => graphApi.traceLineage(entityType!, entityId!, direction, maxDepth),
    enabled: !!entityType && !!entityId,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook: 查找路径 (使用 mutation 因为参数复杂)
 */
export function useFindPath() {
  return useMutation({
    mutationFn: (params: {
      sourceType: GraphNodeType
      sourceId: string
      targetType: GraphNodeType
      targetId: string
      maxDepth?: number
    }) =>
      graphApi.findPath(
        params.sourceType,
        params.sourceId,
        params.targetType,
        params.targetId,
        params.maxDepth
      ),
  })
}

/**
 * Hook: 获取实体标签
 */
export function useEntityTags(entityType: GraphNodeType | null, entityId: string | null) {
  return useQuery({
    queryKey: graphKeys.entityTags(entityType!, entityId!),
    queryFn: () => graphApi.getEntityTags(entityType!, entityId!),
    enabled: !!entityType && !!entityId,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook: 获取所有标签
 */
export function useAllTags() {
  return useQuery({
    queryKey: graphKeys.allTags(),
    queryFn: graphApi.listAllTags,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook: 按标签获取实体
 */
export function useEntitiesByTag(tag: string | null, entityType?: GraphNodeType) {
  return useQuery({
    queryKey: graphKeys.entitiesByTag(tag!, entityType),
    queryFn: () => graphApi.getEntitiesByTag(tag!, entityType),
    enabled: !!tag,
    staleTime: DEFAULT_STALE_TIME,
  })
}
