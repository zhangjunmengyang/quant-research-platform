/**
 * Experience API client
 * 简化版本: 移除 validate/deprecate/curate，以标签为核心管理
 */

import { apiClient, type ApiResponse, type PaginatedResponse } from '@/lib/api/client'
import type {
  Experience,
  ExperienceCreate,
  ExperienceUpdate,
  ExperienceListParams,
  ExperienceStats,
  ExperienceQueryParams,
  ExperienceLinkRequest,
  ExperienceLinkResponse,
  ExperienceLink,
} from './types'

const BASE_URL = '/experiences'

export const experienceApi = {
  /**
   * Get paginated experience list
   */
  list: async (params: ExperienceListParams = {}): Promise<PaginatedResponse<Experience>> => {
    const { data } = await apiClient.get<ApiResponse<PaginatedResponse<Experience>>>(
      `${BASE_URL}`,
      { params }
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch experiences')
    }
    return data.data
  },

  /**
   * Get experience by id
   */
  get: async (id: number): Promise<Experience> => {
    const { data } = await apiClient.get<ApiResponse<Experience>>(`${BASE_URL}/${id}`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Experience not found')
    }
    return data.data
  },

  /**
   * Create new experience
   */
  create: async (experience: ExperienceCreate): Promise<Experience> => {
    const { data } = await apiClient.post<ApiResponse<Experience>>(`${BASE_URL}`, experience)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to create experience')
    }
    return data.data
  },

  /**
   * Update experience
   */
  update: async (id: number, update: ExperienceUpdate): Promise<Experience> => {
    const { data } = await apiClient.patch<ApiResponse<Experience>>(`${BASE_URL}/${id}`, update)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to update experience')
    }
    return data.data
  },

  /**
   * Delete experience
   */
  delete: async (id: number): Promise<void> => {
    const { data } = await apiClient.delete<ApiResponse<null>>(`${BASE_URL}/${id}`)
    if (!data.success) {
      throw new Error(data.error || 'Failed to delete experience')
    }
  },

  /**
   * Semantic query experiences
   */
  query: async (params: ExperienceQueryParams): Promise<Experience[]> => {
    const { data } = await apiClient.post<ApiResponse<Experience[]>>(`${BASE_URL}/query`, params)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to query experiences')
    }
    return data.data
  },

  /**
   * Get experience statistics
   */
  getStats: async (): Promise<ExperienceStats> => {
    const { data } = await apiClient.get<ApiResponse<ExperienceStats>>(`${BASE_URL}/stats`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch stats')
    }
    return data.data
  },

  /**
   * Link experience to entity
   */
  link: async (id: number, request: ExperienceLinkRequest): Promise<ExperienceLinkResponse> => {
    const { data } = await apiClient.post<ApiResponse<ExperienceLinkResponse>>(
      `${BASE_URL}/${id}/link`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to link experience')
    }
    return data.data
  },

  /**
   * Get experience links
   */
  getLinks: async (id: number): Promise<ExperienceLink[]> => {
    const { data } = await apiClient.get<ApiResponse<ExperienceLink[]>>(`${BASE_URL}/${id}/links`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to get links')
    }
    return data.data
  },
}
