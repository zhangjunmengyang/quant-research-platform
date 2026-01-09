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

// ==================== 切块相关 ====================

// 切块项
export interface Chunk {
  chunk_id: string
  chunk_index: number
  chunk_type: string
  content: string
  token_count: number
  page_start?: number
  page_end?: number
  section_title: string
}

// 切块列表响应
export interface ChunkListResponse {
  report_id: number
  total: number
  page: number
  page_size: number
  chunks: Chunk[]
}

// ==================== 语义搜索 ====================

// 搜索请求
export interface SearchRequest {
  query: string
  top_k?: number
  report_id?: number
  min_score?: number
}

// 搜索结果项
export interface SearchResultItem {
  chunk_id: string
  content: string
  score: number
  report_id?: number
  report_uuid: string
  report_title: string
  page_start?: number
  section_title: string
}

// 搜索响应
export interface SearchResponse {
  query: string
  count: number
  results: SearchResultItem[]
}

// ==================== RAG 问答 ====================

// 问答请求
export interface AskRequest {
  question: string
  top_k?: number
  report_id?: number
}

// 来源项
export interface SourceItem {
  chunk_id: string
  content: string
  page_number?: number
  relevance: number
  report_uuid: string
  report_title: string
}

// 问答响应
export interface AskResponse {
  question: string
  answer: string
  sources: SourceItem[]
  retrieved_chunks: number
}

// ==================== 相似切块 ====================

// 相似切块请求
export interface SimilarChunksRequest {
  chunk_id: string
  top_k?: number
  exclude_same_report?: boolean
}

// 相似切块项
export interface SimilarChunkItem {
  chunk_id: string
  content: string
  score: number
  report_id?: number
  report_uuid: string
  report_title: string
  section_title: string
}

// 相似切块响应
export interface SimilarChunksResponse {
  reference_chunk_id: string
  count: number
  similar_chunks: SimilarChunkItem[]
}
