/**
 * Stock Hub API 客户端
 */

import { apiClient, type ApiResponse, type PaginatedResponse } from '@/lib/api/client'
import type {
  StockStatus,
  StockFactorSummary,
  StockFactorDetail,
  AvailableBacktestsResponse,
  CachedFactorInfo,
  EnhancedAnalysisRequest,
  AnalysisResult,
  DualAnalysisRequest,
  DualAnalysisResult,
  StockFactorListParams,
} from './types'

const BASE = '/stock'

export const stockApi = {
  getStatus: async (): Promise<StockStatus> => {
    const { data } = await apiClient.get<ApiResponse<StockStatus>>(`${BASE}/status`)
    if (!data.success || !data.data) throw new Error(data.error || 'Failed to get status')
    return data.data
  },

  listFactors: async (
    params: StockFactorListParams = {}
  ): Promise<PaginatedResponse<StockFactorSummary>> => {
    const { data } = await apiClient.get<ApiResponse<PaginatedResponse<StockFactorSummary>>>(
      `${BASE}/factors`,
      { params }
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Failed to list factors')
    return data.data
  },

  getFactorDetail: async (name: string): Promise<StockFactorDetail> => {
    const { data } = await apiClient.get<ApiResponse<StockFactorDetail>>(
      `${BASE}/factors/${encodeURIComponent(name)}`
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Factor not found')
    return data.data
  },

  getCategories: async (): Promise<Record<string, number>> => {
    const { data } = await apiClient.get<ApiResponse<Record<string, number>>>(
      `${BASE}/factors/categories`
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Failed to get categories')
    return data.data
  },

  refreshFactors: async (): Promise<{ total: number }> => {
    const { data } = await apiClient.post<ApiResponse<{ total: number }>>(
      `${BASE}/factors/refresh`
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Failed to refresh')
    return data.data
  },

  listAvailableBacktests: async (): Promise<AvailableBacktestsResponse> => {
    const { data } = await apiClient.get<ApiResponse<AvailableBacktestsResponse>>(
      `${BASE}/analysis/available-backtests`
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Failed to list backtests')
    return data.data
  },

  listCachedFactors: async (backtestName?: string): Promise<CachedFactorInfo[]> => {
    const { data } = await apiClient.get<ApiResponse<CachedFactorInfo[]>>(
      `${BASE}/analysis/cached-factors`,
      { params: backtestName ? { backtest_name: backtestName } : {} }
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Failed to list cached factors')
    return data.data
  },

  runEnhancedAnalysis: async (req: EnhancedAnalysisRequest): Promise<AnalysisResult> => {
    const { data } = await apiClient.post<ApiResponse<AnalysisResult>>(
      `${BASE}/analysis/enhanced`,
      req,
      { timeout: 600000 }
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Analysis failed')
    return data.data
  },

  runDualAnalysis: async (req: DualAnalysisRequest): Promise<DualAnalysisResult> => {
    const { data } = await apiClient.post<ApiResponse<DualAnalysisResult>>(
      `${BASE}/analysis/dual`,
      req,
      { timeout: 600000 }
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Dual analysis failed')
    return data.data
  },
}
