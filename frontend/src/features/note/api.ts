/**
 * Note API client
 */

import { apiClient, type ApiResponse, type PaginatedResponse } from '@/lib/api/client'
import type {
  Note,
  NoteCreate,
  NoteUpdate,
  NoteListParams,
  NoteStats,
  ObservationCreate,
  HypothesisCreate,
  VerificationCreate,
  PromoteRequest,
  ResearchTrail,
} from './types'

const BASE_URL = '/notes'

export const noteApi = {
  /**
   * Get paginated note list
   */
  list: async (params: NoteListParams = {}): Promise<PaginatedResponse<Note>> => {
    const { data } = await apiClient.get<ApiResponse<PaginatedResponse<Note>>>(`${BASE_URL}/`, {
      params,
    })
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch notes')
    }
    return data.data
  },

  /**
   * Get note by id
   */
  get: async (id: number): Promise<Note> => {
    const { data } = await apiClient.get<ApiResponse<Note>>(`${BASE_URL}/${id}`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Note not found')
    }
    return data.data
  },

  /**
   * Create new note
   */
  create: async (note: NoteCreate): Promise<Note> => {
    const { data } = await apiClient.post<ApiResponse<Note>>(`${BASE_URL}/`, note)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to create note')
    }
    return data.data
  },

  /**
   * Update note
   */
  update: async (id: number, update: NoteUpdate): Promise<Note> => {
    const { data } = await apiClient.patch<ApiResponse<Note>>(`${BASE_URL}/${id}`, update)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to update note')
    }
    return data.data
  },

  /**
   * Delete note
   */
  delete: async (id: number): Promise<void> => {
    const { data } = await apiClient.delete<ApiResponse<null>>(`${BASE_URL}/${id}`)
    if (!data.success) {
      throw new Error(data.error || 'Failed to delete note')
    }
  },

  /**
   * Get note statistics
   */
  getStats: async (): Promise<NoteStats> => {
    const { data } = await apiClient.get<ApiResponse<NoteStats>>(`${BASE_URL}/stats`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch stats')
    }
    return data.data
  },

  /**
   * Get all tags
   */
  getTags: async (): Promise<string[]> => {
    const { data } = await apiClient.get<ApiResponse<string[]>>(`${BASE_URL}/tags`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch tags')
    }
    return data.data
  },

  // ==================== 研究记录相关 API ====================

  /**
   * 记录观察
   */
  recordObservation: async (request: ObservationCreate): Promise<Note> => {
    const { data } = await apiClient.post<ApiResponse<Note>>(`${BASE_URL}/observation`, request)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to record observation')
    }
    return data.data
  },

  /**
   * 记录假设
   */
  recordHypothesis: async (request: HypothesisCreate): Promise<Note> => {
    const { data } = await apiClient.post<ApiResponse<Note>>(`${BASE_URL}/hypothesis`, request)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to record hypothesis')
    }
    return data.data
  },

  /**
   * 记录检验
   */
  recordVerification: async (request: VerificationCreate): Promise<Note> => {
    const { data } = await apiClient.post<ApiResponse<Note>>(`${BASE_URL}/verification`, request)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to record verification')
    }
    return data.data
  },

  /**
   * 获取假设的所有验证笔记
   * 通过 Edge 系统查找关联关系
   */
  getVerifications: async (hypothesisId: number, includeArchived = false): Promise<Note[]> => {
    const { data } = await apiClient.get<ApiResponse<Note[]>>(
      `${BASE_URL}/${hypothesisId}/verifications`,
      { params: { include_archived: includeArchived } }
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch verifications')
    }
    return data.data
  },

  /**
   * @deprecated Use getVerifications instead
   * 获取关联到指定笔记的所有笔记 (legacy)
   */
  getLinkedNotes: async (noteId: number, _noteType?: string, includeArchived = false): Promise<Note[]> => {
    // Redirect to verifications endpoint
    return noteApi.getVerifications(noteId, includeArchived)
  },

  /**
   * 获取研究轨迹
   */
  getResearchTrail: async (sessionId: string, includeArchived = false): Promise<ResearchTrail> => {
    const { data } = await apiClient.get<ApiResponse<ResearchTrail>>(
      `${BASE_URL}/trail/${sessionId}`,
      { params: { include_archived: includeArchived } }
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch research trail')
    }
    return data.data
  },

  /**
   * 归档笔记
   */
  archive: async (id: number): Promise<Note> => {
    const { data } = await apiClient.post<ApiResponse<Note>>(`${BASE_URL}/${id}/archive`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to archive note')
    }
    return data.data
  },

  /**
   * 取消归档笔记
   */
  unarchive: async (id: number): Promise<Note> => {
    const { data } = await apiClient.post<ApiResponse<Note>>(`${BASE_URL}/${id}/unarchive`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to unarchive note')
    }
    return data.data
  },

  /**
   * 提炼为经验
   */
  promoteToExperience: async (id: number, request: PromoteRequest): Promise<Note> => {
    const { data } = await apiClient.post<ApiResponse<Note>>(
      `${BASE_URL}/${id}/promote`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to promote note to experience')
    }
    return data.data
  },
}
