/**
 * Stock Hub React Query Hooks
 */

import { useQuery, useMutation, keepPreviousData } from '@tanstack/react-query'
import { stockApi } from './api'
import type {
  EnhancedAnalysisRequest,
  DualAnalysisRequest,
  StockFactorListParams,
} from './types'

const STALE_TIME = 5 * 60 * 1000

export const stockKeys = {
  all: ['stock'] as const,
  status: () => [...stockKeys.all, 'status'] as const,
  factors: () => [...stockKeys.all, 'factors'] as const,
  factorList: (params: StockFactorListParams) => [...stockKeys.factors(), 'list', params] as const,
  factorDetail: (name: string) => [...stockKeys.factors(), 'detail', name] as const,
  categories: () => [...stockKeys.factors(), 'categories'] as const,
  backtests: () => [...stockKeys.all, 'backtests'] as const,
  cachedFactors: (name?: string) => [...stockKeys.all, 'cached-factors', name] as const,
}

export function useStockStatus() {
  return useQuery({
    queryKey: stockKeys.status(),
    queryFn: stockApi.getStatus,
    staleTime: STALE_TIME,
  })
}

export function useStockFactors(params: StockFactorListParams = {}) {
  return useQuery({
    queryKey: stockKeys.factorList(params),
    queryFn: () => stockApi.listFactors(params),
    placeholderData: keepPreviousData,
    staleTime: STALE_TIME,
  })
}

export function useStockFactorDetail(name: string | null) {
  return useQuery({
    queryKey: stockKeys.factorDetail(name ?? ''),
    queryFn: () => stockApi.getFactorDetail(name!),
    enabled: !!name,
    staleTime: STALE_TIME,
  })
}

export function useStockCategories() {
  return useQuery({
    queryKey: stockKeys.categories(),
    queryFn: stockApi.getCategories,
    staleTime: STALE_TIME,
  })
}

export function useAvailableBacktests() {
  return useQuery({
    queryKey: stockKeys.backtests(),
    queryFn: stockApi.listAvailableBacktests,
    staleTime: STALE_TIME,
  })
}

export function useCachedFactors(backtestName?: string) {
  return useQuery({
    queryKey: stockKeys.cachedFactors(backtestName),
    queryFn: () => stockApi.listCachedFactors(backtestName),
    staleTime: STALE_TIME,
  })
}

export function useEnhancedAnalysis() {
  return useMutation({
    mutationFn: (req: EnhancedAnalysisRequest) => stockApi.runEnhancedAnalysis(req),
  })
}

export function useDualAnalysis() {
  return useMutation({
    mutationFn: (req: DualAnalysisRequest) => stockApi.runDualAnalysis(req),
  })
}
