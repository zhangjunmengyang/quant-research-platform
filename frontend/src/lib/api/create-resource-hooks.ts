/**
 * 通用 React Query Hooks 工厂
 *
 * 用于创建标准的 CRUD hooks，减少重复代码
 *
 * @example
 * ```ts
 * import { createResourceHooks } from '@/lib/api/create-resource-hooks'
 * import { factorApi } from './api'
 * import type { Factor, FactorListParams, FactorUpdate } from './types'
 *
 * export const factorKeys = createResourceKeys('factors')
 *
 * export const {
 *   useList,
 *   useItem,
 *   useStats,
 *   useMutations,
 * } = createResourceHooks({
 *   resourceName: 'factors',
 *   keys: factorKeys,
 *   api: factorApi,
 *   listItem: (params) => factorApi.list(params),
 *   getItem: (filename) => factorApi.get(filename),
 *   getStats: () => factorApi.getStats(),
 *   updateItem: ({ filename, update }) => factorApi.update(filename, update),
 *   deleteItem: (filename) => factorApi.delete(filename),
 *   itemKeyParam: 'filename',
 * })
 * ```
 */

import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'

// 默认缓存时间: 5 分钟
export const DEFAULT_STALE_TIME = 5 * 60 * 1000

/**
 * Query Keys 工厂
 */
export interface QueryKeys<T extends string> {
  all: readonly [T]
  lists: () => readonly [T, 'list']
  list: (params: unknown) => readonly [T, 'list', unknown]
  details: () => readonly [T, 'detail']
  detail: (id: string) => readonly [T, 'detail', string]
  stats: () => readonly [T, 'stats']
}

/**
 * 创建标准的 Query Keys
 */
export function createResourceKeys<T extends string>(resourceName: T): QueryKeys<T> {
  return {
    all: [resourceName] as const,
    lists: () => [resourceName, 'list'] as const,
    list: (params: unknown) => [resourceName, 'list', params] as const,
    details: () => [resourceName, 'detail'] as const,
    detail: (id: string) => [resourceName, 'detail', id] as const,
    stats: () => [resourceName, 'stats'] as const,
  }
}

/**
 * 创建资源 hooks 的配置
 */
export interface CreateResourceHooksConfig<
  T,
  ListParams,
  UpdateData,
  DeleteResponse = void
> {
  /** 资源名称（用于生成 query keys） */
  resourceName: string
  /** Query keys */
  keys: QueryKeys<string>
  /** 列表 API */
  listItem: (params: ListParams) => Promise<{ items: T[]; total: number }>
  /** 详情 API */
  getItem: (id: string) => Promise<T>
  /** 统计 API (可选) */
  getStats?: () => Promise<unknown>
  /** 更新 API (可选) */
  updateItem?: (data: { id: string; update: UpdateData }) => Promise<T>
  /** 删除 API (可选) */
  deleteItem?: (id: string) => Promise<DeleteResponse>
  /** 其他自定义 API (可选) */
  customActions?: Record<string, (args: unknown) => Promise<unknown>>
  /** 列表缓存时间 (可选) */
  staleTime?: number
  /** ID 参数名称 (默认 'id') */
  itemKeyParam?: string
  /** 提取更新后的 ID (默认从返回值中取 'id' 字段) */
  extractId?: (item: T) => string
}

/**
 * 创建资源 hooks 的结果
 */
export interface ResourceHooks<
  T,
  ListParams,
  UpdateData,
  DeleteResponse = void
> {
  /** 列表 hook */
  useList: (params: ListParams) => ReturnType<typeof useQuery>
  /** 详情 hook */
  useItem: (id: string) => ReturnType<typeof useQuery>
  /** 统计 hook (如果配置了 getStats) */
  useStats?: () => ReturnType<typeof useQuery>
}

/**
 * Mutations hooks 的返回类型
 */
interface ResourceMutations<
  T,
  ListParams,
  UpdateData,
  DeleteResponse = void
> {
  /** Mutations hooks */
  useMutations: () => {
    update?: ReturnType<typeof useMutation>
    delete?: ReturnType<typeof useMutation>
    [key: string]: ReturnType<typeof useMutation> | undefined
  }
}

/**
 * 完整的资源 hooks (包含 mutations)
 */
export type ResourceHooksWithMutations<
  T,
  ListParams,
  UpdateData,
  DeleteResponse = void
> = ResourceHooks<T, ListParams, UpdateData, DeleteResponse> & ResourceMutations<T, ListParams, UpdateData, DeleteResponse>

/**
 * 创建标准的 CRUD hooks
 */
export function createResourceHooks<
  T extends Record<string, unknown>,
  ListParams,
  UpdateData = never,
  DeleteResponse = void
>(
  config: CreateResourceHooksConfig<T, ListParams, UpdateData, DeleteResponse>
): ResourceHooksWithMutations<T, ListParams, UpdateData, DeleteResponse> {
  const {
    keys,
    listItem,
    getItem,
    getStats,
    updateItem,
    deleteItem,
    customActions,
    staleTime = DEFAULT_STALE_TIME,
    extractId = (item) => String(item.id ?? ''),
  } = config

  /**
   * 获取列表数据
   */
  const useList = (params: ListParams) =>
    useQuery({
      queryKey: keys.list(params),
      queryFn: () => listItem(params),
      placeholderData: keepPreviousData,
      staleTime,
    })

  /**
   * 获取单条数据
   */
  const useItem = (id: string) =>
    useQuery({
      queryKey: keys.detail(id),
      queryFn: () => getItem(id),
      enabled: !!id,
      staleTime,
    })

  const hooks: ResourceHooksWithMutations<T, ListParams, UpdateData, DeleteResponse> = {
    useList,
    useItem,
    useMutations: (() => {
      const queryClient = useQueryClient()

      const invalidateListAndStats = () => {
        queryClient.invalidateQueries({ queryKey: keys.lists() })
        queryClient.invalidateQueries({ queryKey: keys.stats() })
      }

      const invalidateAll = () => {
        queryClient.invalidateQueries({ queryKey: keys.all })
      }

      const mutations: Record<string, ReturnType<typeof useMutation> | undefined> = {}

      // 更新 mutation
      if (updateItem) {
        mutations.update = useMutation({
          mutationFn: updateItem,
          onSuccess: (data) => {
            const itemId = extractId(data as T)
            queryClient.setQueryData(keys.detail(itemId), data)
            invalidateListAndStats()
          },
        })
      }

      // 删除 mutation
      if (deleteItem) {
        mutations.delete = useMutation({
          mutationFn: deleteItem,
          onSuccess: () => {
            invalidateAll()
          },
        })
      }

      // 自定义 actions
      if (customActions) {
        Object.entries(customActions).forEach(([name, actionFn]) => {
          mutations[name] = useMutation({
            mutationFn: actionFn,
            onSuccess: () => {
              invalidateListAndStats()
            },
          })
        })
      }

      return mutations as ResourceHooksWithMutations<T, ListParams, UpdateData, DeleteResponse>['useMutations'] extends () => infer R ? R : never
    }) as () => ResourceHooksWithMutations<T, ListParams, UpdateData, DeleteResponse>['useMutations'] extends () => infer R ? R : never,
  }

  /**
   * 获取统计数据 (可选)
   */
  if (getStats) {
    hooks.useStats = () =>
      useQuery({
        queryKey: keys.stats(),
        queryFn: getStats,
        staleTime,
      })
  }

  return hooks
}
