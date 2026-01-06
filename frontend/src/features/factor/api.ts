/**
 * Factor API client
 */

import { apiClient, type ApiResponse, type PaginatedResponse } from '@/lib/api/client'
import type {
  Factor,
  FactorUpdate,
  FactorListParams,
  FactorStats,
  FactorVerifyRequest,
  FactorGroupAnalysisRequest,
  FactorGroupAnalysisResponse,
  FactorCreateRequest,
  FactorCreateResponse,
} from './types'

const BASE_URL = '/factors'

export const factorApi = {
  /**
   * Get paginated factor list
   */
  list: async (params: FactorListParams = {}): Promise<PaginatedResponse<Factor>> => {
    const { data } = await apiClient.get<ApiResponse<PaginatedResponse<Factor>>>(`${BASE_URL}/`, {
      params,
    })
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch factors')
    }
    return data.data
  },

  /**
   * Get factor by filename
   */
  get: async (filename: string): Promise<Factor> => {
    const { data } = await apiClient.get<ApiResponse<Factor>>(`${BASE_URL}/${filename}`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Factor not found')
    }
    return data.data
  },

  /**
   * Update factor fields
   */
  update: async (filename: string, update: FactorUpdate): Promise<Factor> => {
    const { data } = await apiClient.patch<ApiResponse<Factor>>(`${BASE_URL}/${filename}`, update)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to update factor')
    }
    return data.data
  },

  /**
   * Delete factor
   */
  delete: async (filename: string): Promise<void> => {
    const { data } = await apiClient.delete<ApiResponse<null>>(`${BASE_URL}/${filename}`)
    if (!data.success) {
      throw new Error(data.error || 'Failed to delete factor')
    }
  },

  /**
   * Verify factor
   */
  verify: async (filename: string, request?: FactorVerifyRequest): Promise<Factor> => {
    const { data } = await apiClient.post<ApiResponse<Factor>>(
      `${BASE_URL}/${filename}/verify`,
      request || {}
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to verify factor')
    }
    return data.data
  },

  /**
   * Unverify factor
   */
  unverify: async (filename: string): Promise<Factor> => {
    const { data } = await apiClient.post<ApiResponse<Factor>>(`${BASE_URL}/${filename}/unverify`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to unverify factor')
    }
    return data.data
  },

  /**
   * Get factor statistics
   */
  getStats: async (): Promise<FactorStats> => {
    const { data } = await apiClient.get<ApiResponse<FactorStats>>(`${BASE_URL}/stats`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch stats')
    }
    return data.data
  },

  /**
   * Get all styles
   */
  getStyles: async (): Promise<string[]> => {
    const { data } = await apiClient.get<ApiResponse<string[]>>(`${BASE_URL}/styles`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch styles')
    }
    return data.data
  },

  /**
   * Run factor group analysis
   */
  analyzeGroups: async (
    request: FactorGroupAnalysisRequest
  ): Promise<FactorGroupAnalysisResponse[]> => {
    const { data } = await apiClient.post<ApiResponse<FactorGroupAnalysisResponse[]>>(
      '/analysis/factor-group',
      request,
      { timeout: 600000 } // 10 minutes for long-running analysis
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to run factor group analysis')
    }
    return data.data
  },

  /**
   * Create new factor
   */
  create: async (request: FactorCreateRequest): Promise<FactorCreateResponse> => {
    const { data } = await apiClient.post<ApiResponse<FactorCreateResponse>>(
      `${BASE_URL}/`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to create factor')
    }
    return data.data
  },

  /**
   * Update factor code
   */
  updateCode: async (filename: string, code_content: string): Promise<Factor> => {
    const { data } = await apiClient.patch<ApiResponse<Factor>>(`${BASE_URL}/${filename}/code`, {
      code_content,
    })
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to update factor code')
    }
    return data.data
  },

  /**
   * Exclude factor
   */
  exclude: async (filename: string, reason?: string): Promise<Factor> => {
    const { data } = await apiClient.post<ApiResponse<Factor>>(
      `${BASE_URL}/${filename}/exclude`,
      { reason }
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to exclude factor')
    }
    return data.data
  },

  /**
   * Unexclude factor
   */
  unexclude: async (filename: string): Promise<Factor> => {
    const { data } = await apiClient.post<ApiResponse<Factor>>(`${BASE_URL}/${filename}/unexclude`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to unexclude factor')
    }
    return data.data
  },
}
