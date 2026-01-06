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
}
