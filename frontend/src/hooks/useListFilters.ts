/**
 * 通用列表筛选 Hook
 * 统一管理 URL params 筛选状态，支持书签、分享、后退导航
 */

import { useState, useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'

/**
 * 筛选字段配置
 */
export interface FilterFieldConfig {
  name: string
  type: 'string' | 'number' | 'boolean' | 'enum'
  defaultValue?: any
  // 枚举类型的可选值
  options?: Array<{ value: string; label: string }>
}

/**
 * 列表筛选配置
 */
export interface ListFiltersConfig<T extends Record<string, any>> {
  // 默认筛选值
  defaultFilters: Partial<T>
  // 筛选字段配置
  fields?: FilterFieldConfig[]
  // 是否启用搜索（默认 true）
  searchEnabled?: boolean
  // 分页配置
  pagination?: {
    defaultPageSize?: number
    pageSizeOptions?: number[]
  }
}

/**
 * 解析 URL 参数为筛选值
 */
function parseParams<T extends Record<string, any>>(
  searchParams: URLSearchParams,
  config: ListFiltersConfig<T>
): Partial<T> {
  const params: any = {}

  for (const [key, value] of searchParams.entries()) {
    if (value === '') continue

    // 处理布尔值
    if (value === 'true') {
      params[key] = true
    } else if (value === 'false') {
      params[key] = false
    }
    // 处理数字
    else if (!isNaN(Number(value))) {
      params[key] = Number(value)
    }
    // 字符串
    else {
      params[key] = value
    }
  }

  return params as Partial<T>
}

/**
 * 将筛选值转换为 URL 参数
 */
function paramsToRecord<T extends Record<string, any>>(filters: Partial<T>): Record<string, string> {
  const params: Record<string, string> = {}

  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null) continue
    params[key] = String(value)
  }

  return params
}

/**
 * 通用列表筛选 Hook
 */
export function useListFilters<T extends Record<string, any>>(config: ListFiltersConfig<T>) {
  const [searchParams, setSearchParams] = useSearchParams()
  const { defaultFilters, fields = [], pagination = {} } = config

  // 从 URL 解析当前筛选值
  const urlFilters = parseParams<T>(searchParams, config)

  // 合并默认值和 URL 值
  const [filters, setFiltersState] = useState<Partial<T>>(() => ({
    ...defaultFilters,
    ...urlFilters,
  }))

  // 同步 URL 变化到 state
  useEffect(() => {
    const newUrlFilters = parseParams<T>(searchParams, config)
    setFiltersState((prev) => ({
      ...defaultFilters,
      ...newUrlFilters,
    }))
  }, [searchParams])

  // 更新筛选并同步到 URL
  const setFilters = useCallback((newFilters: Partial<T> | ((prev: Partial<T>) => Partial<T>)) => {
    setFiltersState((prev) => {
      const updated = typeof newFilters === 'function' ? newFilters(prev) : newFilters
      const merged = { ...prev, ...updated }

      // 同步到 URL
      const params = paramsToRecord(merged)
      // 移除与默认值相同的参数以简化 URL
      for (const [key, value] of Object.entries(params)) {
        if (String(value) === String(defaultFilters[key as keyof T])) {
          delete params[key]
        }
      }
      setSearchParams(params)

      return merged
    })
  }, [defaultFilters, setSearchParams])

  // 更新单个筛选字段
  const setFilter = useCallback(<K extends keyof T>(key: K, value: T[K]) => {
    setFilters({ [key]: value } as Partial<T>)
  }, [setFilters])

  // 重置筛选
  const resetFilters = useCallback(() => {
    setFilters(defaultFilters)
  }, [defaultFilters, setFilters])

  // 搜索功能
  const searchValue = (filters as any).search || ''
  const setSearch = useCallback((value: string) => {
    setFilters({ search: value } as Partial<T>)
  }, [setFilters])

  // 分页
  const page = (filters as any).page ?? defaultFilters.page ?? 1
  const pageSize = (filters as any).page_size ?? defaultFilters.page_size ?? pagination.defaultPageSize ?? 20
  const setPage = useCallback((newPage: number) => {
    setFilters({ page: newPage } as Partial<T>)
  }, [setFilters])

  const setPageSize = useCallback((newPageSize: number) => {
    setFilters({ page_size: newPageSize, page: 1 } as Partial<T>)
  }, [setFilters])

  // 检查是否有活跃筛选（排除分页）
  const hasActiveFilters = useCallback(() => {
    const { page, page_size, search, ...rest } = filters as any
    return Object.keys(rest).some((key) => {
      const value = rest[key]
      return value !== undefined && value !== null && value !== '' && value !== defaultFilters[key]
    }) || (search && search !== defaultFilters.search)
  }, [filters, defaultFilters])

  return {
    // 当前筛选状态
    filters,
    // 筛选操作
    setFilters,
    setFilter,
    resetFilters,
    // 搜索
    searchValue,
    setSearch,
    // 分页
    page,
    pageSize,
    setPage,
    setPageSize,
    // 状态 - 返回函数本身，由调用方决定何时执行
    hasActiveFilters,
  }
}
