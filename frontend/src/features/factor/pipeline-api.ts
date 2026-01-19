/**
 * Pipeline API client
 * Factor data cleaning pipeline operations
 */

import { apiClient, type ApiResponse } from '@/lib/api/client'

const BASE_URL = '/pipeline'

// ==================== Types ====================

export interface PipelineStatus {
  total: number
  scored: number
  unscored: number
  verified: number
  pending: number
  score_distribution: Record<string, number>
  style_distribution: Record<string, number>
  field_coverage: Record<string, { filled: number; empty: number }>
}

export interface DiscoverResult {
  cataloged: string[]
  pending: string[]
  excluded: string[]
  missing_files: string[]
  pending_time_series: string[]
  pending_cross_section: string[]
}

export type FillableField =
  | 'style'
  | 'tags'
  | 'formula'
  | 'input_data'
  | 'value_range'
  | 'description'
  | 'analysis'
  | 'llm_score'

export type FillMode = 'incremental' | 'full'

export interface FillRequest {
  factors?: string[] | null  // 指定因子列表，null 表示全部
  fields: FillableField[]
  mode?: FillMode
  delay?: number  // 请求间隔时间（秒），用于适应低 RPM 场景
  concurrency?: number  // 并发数，默认 1
  dry_run?: boolean  // 只统计，不调用 LLM
  preview?: boolean  // 预览模式：生成内容但不保存到数据库
}

export interface FillResult {
  total_factors: number
  factors?: string[]  // 实际填充的因子列表
  fields: string[]
  result?: Record<string, unknown>
  dry_run?: boolean
  to_fill?: Record<string, number>
  // preview 模式返回
  preview?: boolean
  generated?: Record<string, Record<string, string>>  // {filename: {field: value}}
  // 异步任务模式返回
  task_id?: string
  status?: string
}

// SSE 进度相关类型
export type FillTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface FillProgress {
  task_id: string
  status: FillTaskStatus
  progress: number  // 0-100
  message: string
  current_step: string | null  // 当前字段名
  total_steps: number | null   // 总待填充数量
  current_step_num: number | null  // 当前已完成数量
  data?: FillProgressData | null
  error: string | null
  created_at: string
  updated_at: string
}

export interface FillProgressData {
  type: 'factor_completed' | 'completed'
  factor?: string
  field?: string
  success?: boolean
  value?: string | null
  error?: string | null
  // completed 类型
  success_count?: number
  fail_count?: number
  fields?: string[]
}

export interface FillLog {
  factor: string
  field: string
  success: boolean
  value?: string | null
  error?: string | null
  timestamp: Date
}

export interface IngestRequest {
  factors?: string[] | null
  fill_fields?: boolean
  dry_run?: boolean
}

export interface IngestResult {
  total: number
  ingested: number
  skipped: number
  failed: number
  factors: string[]
}

export interface ReviewRequest {
  factors?: string[] | null
  fields?: string[]
  filter_verified?: boolean | null
  filter_score_min?: number | null
  filter_score_max?: number | null
  delay?: number  // 请求间隔时间（秒），用于适应低 RPM 场景
  concurrency?: number  // 并发数，默认 1
  dry_run?: boolean
}

export interface ReviewResult {
  total: number
  reviewed: number
  revised: number
  details: Array<Record<string, unknown>>
}

export interface ModelConfig {
  name: string           // 模型 key（引用 llm_configs）
  temperature: number    // 温度参数 (0-2)
  max_tokens: number     // 最大输出 token 数
}

export interface PromptConfig {
  field: string
  description: string
  system: string
  user: string
  output_format: string
  max_length: number    // 已废弃，使用 model.max_tokens
  model: ModelConfig    // 模型配置
}

export interface ModelConfigUpdate {
  name?: string
  temperature?: number
  max_tokens?: number
}

export interface PromptConfigUpdate {
  system?: string
  user?: string
  description?: string
  output_format?: string
  max_length?: number
  model?: ModelConfigUpdate
}

export interface PromptVariable {
  name: string
  desc: string
  type: string
}

export interface LLMModelInfo {
  key: string           // 模型 key（用于 Prompt 配置引用）
  provider: string      // API 提供商类型
  model: string         // 实际模型标识符
  temperature: number   // 默认温度
  max_tokens: number    // 默认 max_tokens
}

export interface LLMModelsResponse {
  models: LLMModelInfo[]
  default: string       // 默认模型 key
}

// ==================== API Client ====================

export const pipelineApi = {
  /**
   * Get pipeline status and statistics
   */
  getStatus: async (): Promise<PipelineStatus> => {
    const { data } = await apiClient.get<ApiResponse<PipelineStatus>>(`${BASE_URL}/status`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch pipeline status')
    }
    return data.data
  },

  /**
   * Discover new factors not yet in database
   */
  discover: async (): Promise<DiscoverResult> => {
    const { data } = await apiClient.get<ApiResponse<DiscoverResult>>(`${BASE_URL}/discover`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to discover factors')
    }
    return data.data
  },

  /**
   * Get list of fillable fields
   */
  getFields: async (): Promise<string[]> => {
    const { data } = await apiClient.get<ApiResponse<string[]>>(`${BASE_URL}/fields`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to get fields')
    }
    return data.data
  },

  /**
   * Ingest new factors into database
   */
  ingest: async (request: IngestRequest): Promise<IngestResult> => {
    const { data } = await apiClient.post<ApiResponse<IngestResult>>(`${BASE_URL}/ingest`, request)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to ingest factors')
    }
    return data.data
  },

  /**
   * Fill fields using LLM
   *
   * 统一填充接口：
   * - factors: 指定因子列表，不传则填充全部
   * - fields: 要填充的字段列表
   * - mode: incremental 只填空值，full 全量覆盖
   */
  fill: async (request: FillRequest): Promise<FillResult> => {
    const { data } = await apiClient.post<ApiResponse<FillResult>>(`${BASE_URL}/fill`, request)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fill fields')
    }
    return data.data
  },

  /**
   * Review factors using LLM
   */
  review: async (request: ReviewRequest): Promise<ReviewResult> => {
    const { data } = await apiClient.post<ApiResponse<ReviewResult>>(`${BASE_URL}/review`, request)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to review factors')
    }
    return data.data
  },

  /**
   * Get all prompt configurations
   */
  getPrompts: async (): Promise<PromptConfig[]> => {
    const { data } = await apiClient.get<ApiResponse<PromptConfig[]>>(`${BASE_URL}/prompts`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch prompts')
    }
    return data.data
  },

  /**
   * Get a single prompt configuration
   */
  getPrompt: async (field: string): Promise<PromptConfig> => {
    const { data } = await apiClient.get<ApiResponse<PromptConfig>>(`${BASE_URL}/prompts/${field}`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch prompt')
    }
    return data.data
  },

  /**
   * Update a prompt configuration
   */
  updatePrompt: async (field: string, update: PromptConfigUpdate): Promise<PromptConfig> => {
    const { data } = await apiClient.put<ApiResponse<PromptConfig>>(`${BASE_URL}/prompts/${field}`, update)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to update prompt')
    }
    return data.data
  },

  /**
   * Get available variables for prompt templates
   */
  getVariables: async (): Promise<PromptVariable[]> => {
    const { data } = await apiClient.get<ApiResponse<PromptVariable[]>>(`${BASE_URL}/variables`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch variables')
    }
    return data.data
  },

  /**
   * Get available LLM models for prompt configuration
   */
  getModels: async (): Promise<LLMModelsResponse> => {
    const { data } = await apiClient.get<ApiResponse<LLMModelsResponse>>(`${BASE_URL}/models`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch models')
    }
    return data.data
  },

  /**
   * Get active fill task (running or pending)
   */
  getActiveFillTask: async (): Promise<FillProgress | null> => {
    const { data } = await apiClient.get<ApiResponse<FillProgress | null>>(`${BASE_URL}/fill/active`)
    if (!data.success) {
      throw new Error(data.error || 'Failed to get active fill task')
    }
    return data.data
  },
}
