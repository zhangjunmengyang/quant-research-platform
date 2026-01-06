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
  Conversation,
  Message,
  CreateConversationRequest,
  ChatRequest,
  ChatResponse,
  LLMModelsResponse,
} from './types'

const BASE_URL = '/research'

export const researchApi = {
  // ==================== LLM 配置 ====================

  /**
   * 获取可用的 LLM 模型列表
   */
  getModels: async (): Promise<LLMModelsResponse> => {
    const { data } = await apiClient.get<LLMModelsResponse>(`${BASE_URL}/llm/models`)
    return data
  },

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

  // ==================== 对话管理 ====================

  /**
   * 创建对话
   */
  createConversation: async (request: CreateConversationRequest): Promise<Conversation> => {
    const { data } = await apiClient.post<Conversation>(`${BASE_URL}/conversations`, request)
    return data
  },

  /**
   * 获取对话列表
   */
  listConversations: async (
    limit = 50,
    offset = 0
  ): Promise<Conversation[]> => {
    const { data } = await apiClient.get<Conversation[]>(`${BASE_URL}/conversations`, {
      params: { limit, offset },
    })
    return data
  },

  /**
   * 获取对话详情
   */
  getConversation: async (id: number): Promise<Conversation> => {
    const { data } = await apiClient.get<Conversation>(`${BASE_URL}/conversations/${id}`)
    return data
  },

  /**
   * 删除对话
   */
  deleteConversation: async (id: number): Promise<void> => {
    await apiClient.delete(`${BASE_URL}/conversations/${id}`)
  },

  /**
   * 获取对话消息
   */
  getMessages: async (conversationId: number, limit = 100): Promise<Message[]> => {
    const { data } = await apiClient.get<Message[]>(
      `${BASE_URL}/conversations/${conversationId}/messages`,
      { params: { limit } }
    )
    return data
  },

  /**
   * 发送消息 (同步)
   */
  chat: async (conversationId: number, request: ChatRequest): Promise<ChatResponse> => {
    const { data } = await apiClient.post<ChatResponse>(
      `${BASE_URL}/conversations/${conversationId}/chat`,
      request
    )
    return data
  },

  /**
   * 发送消息 (流式)
   */
  chatStream: (
    conversationId: number,
    request: ChatRequest,
    onChunk: (chunk: { type: string; content?: string; metadata?: Record<string, unknown> }) => void,
    onError?: (error: Error) => void,
    onDone?: () => void
  ): (() => void) => {
    const controller = new AbortController()

    const fetchStream = async () => {
      try {
        const response = await fetch(
          `/api/v1${BASE_URL}/conversations/${conversationId}/chat/stream`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
            signal: controller.signal,
          }
        )

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const reader = response.body?.getReader()
        if (!reader) throw new Error('No reader available')

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim()
              if (data === '[DONE]') {
                onDone?.()
                return
              }
              try {
                const chunk = JSON.parse(data)
                onChunk(chunk)
              } catch {
                // Ignore parse errors
              }
            }
          }
        }

        onDone?.()
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError') {
          onError?.(error)
        }
      }
    }

    fetchStream()

    return () => controller.abort()
  },
}
