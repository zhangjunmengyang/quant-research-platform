/**
 * Research API client
 */

import { apiClient } from '@/lib/api/client'
import type {
  Report,
  ReportUploadResponse,
  ReportListParams,
  ReportListResponse,
  ProcessingStatus,
  ScanUploadRequest,
  ScanUploadResponse,
  ChunkListResponse,
  SearchRequest,
  SearchResponse,
  AskRequest,
  AskResponse,
  SimilarChunksRequest,
  SimilarChunksResponse,
} from './types'

const BASE_URL = '/research'

export const researchApi = {
  /**
   * 获取 PDF 文件 URL
   */
  getPdfUrl: (reportId: number): string => {
    return `/api/v1${BASE_URL}/reports/${reportId}/pdf`
  },

  // ==================== 研报管理 ====================

  /**
   * 获取研报列表
   */
  listReports: async (params: ReportListParams = {}): Promise<ReportListResponse> => {
    const { data } = await apiClient.get<ReportListResponse>(`${BASE_URL}/reports`, { params })
    return data
  },

  /**
   * 获取研报详情
   */
  getReport: async (id: number): Promise<Report> => {
    const { data } = await apiClient.get<Report>(`${BASE_URL}/reports/${id}`)
    return data
  },

  /**
   * 上传研报
   */
  uploadReport: async (
    file: File,
    options?: { title?: string; author?: string; source_url?: string }
  ): Promise<ReportUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    if (options?.title) formData.append('title', options.title)
    if (options?.author) formData.append('author', options.author)
    if (options?.source_url) formData.append('source_url', options.source_url)

    const { data } = await apiClient.post<ReportUploadResponse>(`${BASE_URL}/reports`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  /**
   * 处理研报
   */
  processReport: async (
    id: number,
    pipeline?: string
  ): Promise<{ message: string; report_id: number }> => {
    const { data } = await apiClient.post<{ message: string; report_id: number }>(
      `${BASE_URL}/reports/${id}/process`,
      null,
      { params: pipeline ? { pipeline } : undefined }
    )
    return data
  },

  /**
   * 获取处理状态
   */
  getProcessingStatus: async (id: number): Promise<ProcessingStatus> => {
    const { data } = await apiClient.get<ProcessingStatus>(`${BASE_URL}/reports/${id}/status`)
    return data
  },

  /**
   * 删除研报
   */
  deleteReport: async (id: number): Promise<void> => {
    await apiClient.delete(`${BASE_URL}/reports/${id}`)
  },

  /**
   * 扫描目录上传
   */
  scanAndUpload: async (request: ScanUploadRequest): Promise<ScanUploadResponse> => {
    const { data } = await apiClient.post<ScanUploadResponse>(`${BASE_URL}/reports/scan`, request)
    return data
  },

  // ==================== 切块管理 ====================

  /**
   * 获取研报切块列表
   */
  getReportChunks: async (
    reportId: number,
    params: { page?: number; page_size?: number } = {}
  ): Promise<ChunkListResponse> => {
    const { data } = await apiClient.get<ChunkListResponse>(
      `${BASE_URL}/reports/${reportId}/chunks`,
      { params }
    )
    return data
  },

  /**
   * 获取相似切块
   */
  getSimilarChunks: async (request: SimilarChunksRequest): Promise<SimilarChunksResponse> => {
    const { data } = await apiClient.post<SimilarChunksResponse>(
      `${BASE_URL}/chunks/similar`,
      request
    )
    return data
  },

  // ==================== 语义搜索 ====================

  /**
   * 语义搜索研报内容
   */
  search: async (request: SearchRequest): Promise<SearchResponse> => {
    const { data } = await apiClient.post<SearchResponse>(`${BASE_URL}/search`, request)
    return data
  },

  // ==================== RAG 问答 ====================

  /**
   * 基于研报知识库问答
   */
  ask: async (request: AskRequest): Promise<AskResponse> => {
    const { data } = await apiClient.post<AskResponse>(`${BASE_URL}/ask`, request)
    return data
  },
}
