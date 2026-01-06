/**
 * Research module type definitions
 * Mirrors backend Pydantic models for type safety
 */

// 研报状态
export type ReportStatus =
  | 'uploaded'
  | 'parsing'
  | 'parsed'
  | 'chunking'
  | 'chunked'
  | 'embedding'
  | 'embedded'
  | 'indexing'
  | 'ready'
  | 'failed'

// 状态标签映射
export const STATUS_LABELS: Record<ReportStatus, string> = {
  uploaded: '已上传',
  parsing: '解析中',
  parsed: '已解析',
  chunking: '切块中',
  chunked: '已切块',
  embedding: '嵌入中',
  embedded: '已嵌入',
  indexing: '索引中',
  ready: '就绪',
  failed: '失败',
}

// 状态颜色映射
export const STATUS_COLORS: Record<ReportStatus, string> = {
  uploaded: 'bg-gray-100 text-gray-800',
  parsing: 'bg-blue-100 text-blue-800',
  parsed: 'bg-blue-100 text-blue-800',
  chunking: 'bg-yellow-100 text-yellow-800',
  chunked: 'bg-yellow-100 text-yellow-800',
  embedding: 'bg-purple-100 text-purple-800',
  embedded: 'bg-purple-100 text-purple-800',
  indexing: 'bg-orange-100 text-orange-800',
  ready: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
}

// 研报详情
export interface Report {
  id: number
  uuid: string
  title: string
  filename: string
  file_size: number
  page_count: number
  author: string
  source_url: string
  category: string
  tags: string
  status: ReportStatus
  progress: number
  error_message: string
  created_at?: string
  parsed_at?: string
  indexed_at?: string
}

// 研报上传响应
export interface ReportUploadResponse {
  id: number
  uuid: string
  title: string
  filename: string
  status: string
}

// 研报列表参数
export interface ReportListParams {
  page?: number
  page_size?: number
  search?: string
  status?: string
  category?: string
}

// 研报列表响应
export interface ReportListResponse {
  items: Report[]
  total: number
  page: number
  page_size: number
}

// 处理状态响应
export interface ProcessingStatus {
  id: number
  status: string
  progress: number
  error_message?: string
  chunk_count: number
  parsed_at?: string
  indexed_at?: string
}

// 扫描上传请求
export interface ScanUploadRequest {
  directory: string
  pattern?: string
  recursive?: boolean
  auto_process?: boolean
  pipeline?: string
}

// 扫描上传响应
export interface ScanUploadResponse {
  uploaded: number
  reports: ReportUploadResponse[]
}

// 对话
export interface Conversation {
  id: number
  uuid: string
  title: string
  report_id?: number
  created_at?: string
  updated_at?: string
}

// 消息
export interface Message {
  id?: number
  role: 'user' | 'assistant'
  content: string
  sources?: string
  created_at?: string
}

// 创建对话请求
export interface CreateConversationRequest {
  title?: string
  report_id?: number
}

// 聊天请求
export interface ChatRequest {
  message: string
  report_id?: number
  model_key?: string
}

// LLM 模型信息
export interface LLMModel {
  key: string
  name: string
  model: string
  provider: string
  is_default: boolean
}

// LLM 模型列表响应
export interface LLMModelsResponse {
  models: LLMModel[]
  default_model: string
}

// 聊天响应
export interface ChatResponse {
  content: string
  sources: string
  metadata: {
    retrieved_chunks?: number
    reranked_chunks?: number
    total_time?: number
  }
}

// 流式聊天块
export interface StreamChunk {
  type: 'content' | 'done' | 'error'
  content?: string
  metadata?: Record<string, unknown>
  error?: string
}
