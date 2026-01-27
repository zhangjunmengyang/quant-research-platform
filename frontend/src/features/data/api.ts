/**
 * Data API client
 */

import { apiClient, type ApiResponse } from '@/lib/api/client'
import type {
  Symbol,
  KlineData,
  DataOverview,
  FactorCalcRequest,
  FactorCalcResult,
  AvailableFactor,
  TagInfo,
} from './types'

const BASE_URL = '/data'

export const dataApi = {
  /**
   * Get data overview
   */
  getOverview: async (): Promise<DataOverview> => {
    const { data } = await apiClient.get<ApiResponse<DataOverview>>(`${BASE_URL}/overview`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch overview')
    }
    return data.data
  },

  /**
   * Get available symbols
   */
  getSymbols: async (): Promise<Symbol[]> => {
    const { data } = await apiClient.get<ApiResponse<Symbol[]>>(`${BASE_URL}/symbols`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch symbols')
    }
    return data.data
  },

  /**
   * Get symbol info
   */
  getSymbolInfo: async (symbol: string): Promise<Symbol> => {
    const { data } = await apiClient.get<ApiResponse<Symbol>>(`${BASE_URL}/symbols/${symbol}`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Symbol not found')
    }
    return data.data
  },

  /**
   * Get K-line data for a symbol
   */
  getKline: async (
    symbol: string,
    params?: { data_type?: 'spot' | 'swap'; start_date?: string; end_date?: string; limit?: number }
  ): Promise<KlineData[]> => {
    const { data } = await apiClient.get<ApiResponse<KlineData[]>>(
      `${BASE_URL}/kline/${symbol}`,
      { params }
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch kline data')
    }
    return data.data
  },

  /**
   * Get available factors for calculation
   */
  getAvailableFactors: async (): Promise<AvailableFactor[]> => {
    const { data } = await apiClient.get<ApiResponse<AvailableFactor[]>>(`${BASE_URL}/factors`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch factors')
    }
    return data.data
  },

  /**
   * Calculate factor for a symbol
   */
  calculateFactor: async (request: FactorCalcRequest): Promise<FactorCalcResult> => {
    // 确保 params 是整数数组（后端 rolling 需要整数）
    const requestWithIntParams = {
      ...request,
      params: request.params.map((p) => Math.floor(p)),
    }
    const { data } = await apiClient.post<ApiResponse<FactorCalcResult>>(
      `${BASE_URL}/calculate-factor`,
      requestWithIntParams
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to calculate factor')
    }
    return data.data
  },

  // ==================== 标签 API ====================

  /**
   * Get all tags with counts
   */
  getAllTags: async (): Promise<TagInfo[]> => {
    const { data } = await apiClient.get<ApiResponse<TagInfo[]>>(`${BASE_URL}/tags`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch tags')
    }
    return data.data
  },

  /**
   * Get all symbols' tags mapping
   */
  getAllSymbolTags: async (): Promise<Record<string, string[]>> => {
    const { data } = await apiClient.get<ApiResponse<Record<string, string[]>>>(`${BASE_URL}/tags/all-symbols`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch all symbol tags')
    }
    return data.data
  },

  /**
   * Get symbols by tag
   */
  getSymbolsByTag: async (tag: string): Promise<string[]> => {
    const { data } = await apiClient.get<ApiResponse<string[]>>(`${BASE_URL}/tags/${encodeURIComponent(tag)}/symbols`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch symbols by tag')
    }
    return data.data
  },

  /**
   * Get tags for a symbol
   */
  getSymbolTags: async (symbol: string): Promise<string[]> => {
    const { data } = await apiClient.get<ApiResponse<string[]>>(`${BASE_URL}/symbol/${symbol}/tags`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch symbol tags')
    }
    return data.data
  },

  /**
   * Add tag to a symbol
   */
  addSymbolTag: async (symbol: string, tag: string): Promise<void> => {
    const { data } = await apiClient.post<ApiResponse<unknown>>(`${BASE_URL}/symbol/${symbol}/tags`, { symbol, tag })
    if (!data.success) {
      throw new Error(data.error || 'Failed to add tag')
    }
  },

  /**
   * Remove tag from a symbol
   */
  removeSymbolTag: async (symbol: string, tag: string): Promise<void> => {
    const { data } = await apiClient.delete<ApiResponse<unknown>>(`${BASE_URL}/symbol/${symbol}/tags/${encodeURIComponent(tag)}`)
    if (!data.success) {
      throw new Error(data.error || 'Failed to remove tag')
    }
  },
}
