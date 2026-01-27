/**
 * Data React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dataApi } from './api'
import type { FactorCalcRequest } from './types'

// 默认 stale time: 5 分钟
const DEFAULT_STALE_TIME = 5 * 60 * 1000

// Query Keys
export const dataKeys = {
  all: ['data'] as const,
  overview: () => [...dataKeys.all, 'overview'] as const,
  symbols: () => [...dataKeys.all, 'symbols'] as const,
  symbol: (symbol: string) => [...dataKeys.all, 'symbol', symbol] as const,
  kline: (symbol: string, dataType: 'spot' | 'swap', params?: { start_date?: string; end_date?: string }) =>
    [...dataKeys.all, 'kline', symbol, dataType, params] as const,
  factors: () => [...dataKeys.all, 'factors'] as const,
  // 标签相关
  tags: () => [...dataKeys.all, 'tags'] as const,
  allSymbolTags: () => [...dataKeys.all, 'allSymbolTags'] as const,
  symbolTags: (symbol: string) => [...dataKeys.all, 'symbolTags', symbol] as const,
  symbolsByTag: (tag: string) => [...dataKeys.all, 'symbolsByTag', tag] as const,
}

/**
 * Hook to fetch data overview
 */
export function useDataOverview() {
  return useQuery({
    queryKey: dataKeys.overview(),
    queryFn: dataApi.getOverview,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch available symbols
 */
export function useSymbols() {
  return useQuery({
    queryKey: dataKeys.symbols(),
    queryFn: dataApi.getSymbols,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch symbol info
 */
export function useSymbolInfo(symbol: string) {
  return useQuery({
    queryKey: dataKeys.symbol(symbol),
    queryFn: () => dataApi.getSymbolInfo(symbol),
    enabled: !!symbol,
  })
}

/**
 * Hook to fetch K-line data
 * 默认限制 1500 条数据，有日期范围时限制 2000 条
 */
export function useKline(
  symbol: string,
  dataType: 'spot' | 'swap' = 'swap',
  params?: { start_date?: string; end_date?: string; limit?: number }
) {
  // 有日期范围时使用较大的 limit，否则使用较小的默认值
  const hasDateRange = params?.start_date || params?.end_date
  const defaultLimit = hasDateRange ? 2000 : 1500
  const effectiveParams = {
    ...params,
    limit: params?.limit ?? defaultLimit,
  }

  return useQuery({
    queryKey: dataKeys.kline(symbol, dataType, effectiveParams),
    queryFn: () => dataApi.getKline(symbol, { data_type: dataType, ...effectiveParams }),
    enabled: !!symbol,
    staleTime: DEFAULT_STALE_TIME, // 5 分钟缓存
    gcTime: 1000 * 60 * 30, // 30 分钟后垃圾回收（K 线数据较大）
  })
}

/**
 * Hook to fetch available factors for calculation
 */
export function useAvailableFactors() {
  return useQuery({
    queryKey: dataKeys.factors(),
    queryFn: dataApi.getAvailableFactors,
  })
}

/**
 * Hook for factor calculation
 */
export function useFactorCalculation() {
  return useMutation({
    mutationFn: (request: FactorCalcRequest) => dataApi.calculateFactor(request),
  })
}

// ==================== 标签 Hooks ====================

/**
 * Hook to fetch all tags
 */
export function useAllTags() {
  return useQuery({
    queryKey: dataKeys.tags(),
    queryFn: dataApi.getAllTags,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch all symbols' tags mapping
 */
export function useAllSymbolTags() {
  return useQuery({
    queryKey: dataKeys.allSymbolTags(),
    queryFn: dataApi.getAllSymbolTags,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch tags for a symbol
 */
export function useSymbolTags(symbol: string) {
  return useQuery({
    queryKey: dataKeys.symbolTags(symbol),
    queryFn: () => dataApi.getSymbolTags(symbol),
    enabled: !!symbol,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch symbols by tag
 */
export function useSymbolsByTag(tag: string) {
  return useQuery({
    queryKey: dataKeys.symbolsByTag(tag),
    queryFn: () => dataApi.getSymbolsByTag(tag),
    enabled: !!tag,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook for adding tag to a symbol
 */
export function useAddSymbolTag() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ symbol, tag }: { symbol: string; tag: string }) =>
      dataApi.addSymbolTag(symbol, tag),
    onSuccess: (_, { symbol }) => {
      // Invalidate symbol tags and all tags
      queryClient.invalidateQueries({ queryKey: dataKeys.symbolTags(symbol) })
      queryClient.invalidateQueries({ queryKey: dataKeys.tags() })
    },
  })
}

/**
 * Hook for removing tag from a symbol
 */
export function useRemoveSymbolTag() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ symbol, tag }: { symbol: string; tag: string }) =>
      dataApi.removeSymbolTag(symbol, tag),
    onSuccess: (_, { symbol }) => {
      // Invalidate symbol tags and all tags
      queryClient.invalidateQueries({ queryKey: dataKeys.symbolTags(symbol) })
      queryClient.invalidateQueries({ queryKey: dataKeys.tags() })
    },
  })
}
