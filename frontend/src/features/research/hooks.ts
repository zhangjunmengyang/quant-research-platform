/**
 * Research React Query Hooks
 */

import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { researchApi } from './api'
import type {
  ReportListParams,
  ScanUploadRequest,
  SearchRequest,
  AskRequest,
  SimilarChunksRequest,
} from './types'

// Query Keys
export const researchKeys = {
  all: ['research'] as const,
  // 研报
  reports: () => [...researchKeys.all, 'reports'] as const,
  reportList: (params: ReportListParams) => [...researchKeys.reports(), 'list', params] as const,
  reportDetail: (id: number) => [...researchKeys.reports(), 'detail', id] as const,
  reportStatus: (id: number) => [...researchKeys.reports(), 'status', id] as const,
  // 切块
  chunks: () => [...researchKeys.all, 'chunks'] as const,
  reportChunks: (reportId: number, params: { page?: number; page_size?: number }) =>
    [...researchKeys.chunks(), 'report', reportId, params] as const,
  similarChunks: (chunkId: string) => [...researchKeys.chunks(), 'similar', chunkId] as const,
  // 搜索
  search: () => [...researchKeys.all, 'search'] as const,
  searchResults: (query: string) => [...researchKeys.search(), query] as const,
  // 问答
  ask: () => [...researchKeys.all, 'ask'] as const,
}

// 默认缓存时间: 5 分钟
const DEFAULT_STALE_TIME = 5 * 60 * 1000

// ==================== 研报 Hooks ====================

/**
 * 获取研报列表
 */
export function useReports(params: ReportListParams = {}) {
  return useQuery({
    queryKey: researchKeys.reportList(params),
    queryFn: () => researchApi.listReports(params),
    placeholderData: keepPreviousData,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * 获取研报详情
 */
export function useReport(id: number | null) {
  return useQuery({
    queryKey: researchKeys.reportDetail(id ?? 0),
    queryFn: () => researchApi.getReport(id!),
    enabled: id !== null && id > 0,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * 获取处理状态 (可轮询)
 */
export function useProcessingStatus(id: number | null, enabled = true, refetchInterval?: number) {
  return useQuery({
    queryKey: researchKeys.reportStatus(id ?? 0),
    queryFn: () => researchApi.getProcessingStatus(id!),
    enabled: enabled && id !== null && id > 0,
    refetchInterval,
  })
}

/**
 * 研报操作 mutations
 */
export function useReportMutations() {
  const queryClient = useQueryClient()

  const invalidateReports = () => {
    queryClient.invalidateQueries({ queryKey: researchKeys.reports() })
  }

  // 上传研报
  const uploadMutation = useMutation({
    mutationFn: ({
      file,
      options,
    }: {
      file: File
      options?: { title?: string; author?: string; source_url?: string }
    }) => researchApi.uploadReport(file, options),
    onSuccess: () => {
      invalidateReports()
    },
  })

  // 处理研报
  const processMutation = useMutation({
    mutationFn: ({ id, pipeline }: { id: number; pipeline?: string }) =>
      researchApi.processReport(id, pipeline),
    onSuccess: () => {
      invalidateReports()
    },
  })

  // 删除研报
  const deleteMutation = useMutation({
    mutationFn: (id: number) => researchApi.deleteReport(id),
    onSuccess: () => {
      invalidateReports()
    },
  })

  // 扫描上传
  const scanUploadMutation = useMutation({
    mutationFn: (request: ScanUploadRequest) => researchApi.scanAndUpload(request),
    onSuccess: () => {
      invalidateReports()
    },
  })

  return {
    upload: uploadMutation,
    process: processMutation,
    delete: deleteMutation,
    scanUpload: scanUploadMutation,
  }
}

// ==================== 切块 Hooks ====================

/**
 * 获取研报切块列表
 */
export function useReportChunks(
  reportId: number | null,
  params: { page?: number; page_size?: number } = {}
) {
  return useQuery({
    queryKey: researchKeys.reportChunks(reportId ?? 0, params),
    queryFn: () => researchApi.getReportChunks(reportId!, params),
    enabled: reportId !== null && reportId > 0,
    placeholderData: keepPreviousData,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * 获取相似切块 (mutation，按需调用)
 */
export function useSimilarChunks() {
  return useMutation({
    mutationFn: (request: SimilarChunksRequest) => researchApi.getSimilarChunks(request),
  })
}

// ==================== 语义搜索 Hooks ====================

/**
 * 语义搜索 (mutation，按需调用)
 */
export function useSearch() {
  return useMutation({
    mutationFn: (request: SearchRequest) => researchApi.search(request),
  })
}

// ==================== RAG 问答 Hooks ====================

/**
 * RAG 问答 (mutation，按需调用)
 */
export function useAsk() {
  return useMutation({
    mutationFn: (request: AskRequest) => researchApi.ask(request),
  })
}
