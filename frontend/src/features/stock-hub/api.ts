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
  AnalysisTaskResult,
  AnalysisTaskStatus,
  AnalysisTaskSubmit,
  DualAnalysisRequest,
  DualAnalysisResult,
  StockFactorListParams,
  EvaluationType,
  PromptConfig,
  FactorEvaluationItem,
  FactorEvaluationListResponse,
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

  runEnhancedAnalysis: async (req: EnhancedAnalysisRequest): Promise<AnalysisTaskSubmit> => {
    const { data } = await apiClient.post<ApiResponse<AnalysisTaskSubmit>>(
      `${BASE}/analysis/enhanced`,
      req
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Analysis failed')
    return data.data
  },

  runDualAnalysis: async (req: DualAnalysisRequest): Promise<AnalysisTaskSubmit> => {
    const { data } = await apiClient.post<ApiResponse<AnalysisTaskSubmit>>(
      `${BASE}/analysis/dual`,
      req
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Dual analysis failed')
    return data.data
  },

  getAnalysisTaskStatus: async (taskId: string): Promise<AnalysisTaskStatus> => {
    const { data } = await apiClient.get<ApiResponse<AnalysisTaskStatus>>(
      `${BASE}/analysis/tasks/${encodeURIComponent(taskId)}/status`
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Failed to get task status')
    return data.data
  },

  getAnalysisTaskResult: async <T extends AnalysisResult | DualAnalysisResult>(
    taskId: string
  ): Promise<AnalysisTaskResult<T>> => {
    const { data } = await apiClient.get<ApiResponse<AnalysisTaskResult<T>>>(
      `${BASE}/analysis/tasks/${encodeURIComponent(taskId)}/result`
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Failed to get task result')
    return data.data
  },

  evaluateAnalysis: async (
    evalType: EvaluationType,
    analysisResult: AnalysisResult,
    onChunk: (text: string) => void,
    signal?: AbortSignal,
    modelKey?: string,
  ): Promise<void> => {
    const baseUrl = apiClient.defaults.baseURL || '/api/v1'
    const response = await fetch(`${baseUrl}${BASE}/analysis/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        evaluation_type: evalType,
        analysis_result: analysisResult,
        model_key: modelKey,
      }),
      signal,
    })

    if (!response.ok) throw new Error(`Evaluation request failed: ${response.status}`)
    if (!response.body) throw new Error('No response body')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const payload = line.slice(6).trim()
        if (payload === '[DONE]') return
        let parsed: { content?: string; error?: string }
        try {
          parsed = JSON.parse(payload)
        } catch {
          continue // skip malformed SSE lines
        }
        if (parsed.error) throw new Error(parsed.error)
        if (parsed.content) onChunk(parsed.content)
      }
    }
  },

  // ── 提示词管理 ──

  getPrompt: async (evalType: EvaluationType): Promise<PromptConfig> => {
    const { data } = await apiClient.get<ApiResponse<PromptConfig>>(
      `${BASE}/prompts/${encodeURIComponent(evalType)}`
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Failed to get prompt')
    return data.data
  },

  updatePrompt: async (evalType: EvaluationType, system: string, user: string): Promise<void> => {
    const { data } = await apiClient.put<ApiResponse<{ updated: boolean }>>(
      `${BASE}/prompts/${encodeURIComponent(evalType)}`,
      { system, user }
    )
    if (!data.success) throw new Error(data.error || 'Failed to update prompt')
  },

  // ── 因子评估库 ──

  saveEvaluation: async (params: {
    factor_name: string
    title: string
    evaluations: Record<string, string>
    analysis_snapshot: Record<string, unknown>
    tags: string[]
  }): Promise<FactorEvaluationItem> => {
    const { data } = await apiClient.post<ApiResponse<FactorEvaluationItem>>(
      `${BASE}/evaluations`,
      params
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Failed to save evaluation')
    return data.data
  },

  listEvaluations: async (params: {
    factor_name?: string
    tags?: string
    search?: string
    page?: number
    page_size?: number
  } = {}): Promise<FactorEvaluationListResponse> => {
    const { data } = await apiClient.get<ApiResponse<FactorEvaluationListResponse>>(
      `${BASE}/evaluations`,
      { params }
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Failed to list evaluations')
    return data.data
  },

  getEvaluation: async (uuid: string): Promise<FactorEvaluationItem> => {
    const { data } = await apiClient.get<ApiResponse<FactorEvaluationItem>>(
      `${BASE}/evaluations/${encodeURIComponent(uuid)}`
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Failed to get evaluation')
    return data.data
  },

  updateEvaluation: async (uuid: string, params: {
    title?: string
    evaluations?: Record<string, string>
    tags?: string[]
  }): Promise<void> => {
    const { data } = await apiClient.put<ApiResponse<{ updated: boolean }>>(
      `${BASE}/evaluations/${encodeURIComponent(uuid)}`,
      params
    )
    if (!data.success) throw new Error(data.error || 'Failed to update evaluation')
  },

  deleteEvaluation: async (uuid: string): Promise<void> => {
    const { data } = await apiClient.delete<ApiResponse<{ deleted: boolean }>>(
      `${BASE}/evaluations/${encodeURIComponent(uuid)}`
    )
    if (!data.success) throw new Error(data.error || 'Failed to delete evaluation')
  },

  getEvaluationTags: async (): Promise<string[]> => {
    const { data } = await apiClient.get<ApiResponse<string[]>>(
      `${BASE}/evaluations/tags`
    )
    if (!data.success || !data.data) throw new Error(data.error || 'Failed to get tags')
    return data.data
  },
}
