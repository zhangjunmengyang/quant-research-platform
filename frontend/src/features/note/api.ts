/**
 * Note API client
 */

import { apiClient, type ApiResponse, type PaginatedResponse } from '@/lib/api/client'
import type { Note, NoteCreate, NoteUpdate, NoteListParams, NoteStats } from './types'

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
}
