/**
 * Research React Query Hooks
 */

import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { researchApi } from './api'
import type {
  ReportListParams,
  CreateConversationRequest,
  ChatRequest,
  ScanUploadRequest,
} from './types'

// Query Keys
export const researchKeys = {
  all: ['research'] as const,
  // LLM
  models: () => [...researchKeys.all, 'models'] as const,
  // 研报
  reports: () => [...researchKeys.all, 'reports'] as const,
  reportList: (params: ReportListParams) => [...researchKeys.reports(), 'list', params] as const,
  reportDetail: (id: number) => [...researchKeys.reports(), 'detail', id] as const,
  reportStatus: (id: number) => [...researchKeys.reports(), 'status', id] as const,
  // 对话
  conversations: () => [...researchKeys.all, 'conversations'] as const,
  conversationList: () => [...researchKeys.conversations(), 'list'] as const,
  conversationDetail: (id: number) => [...researchKeys.conversations(), 'detail', id] as const,
  messages: (conversationId: number) =>
    [...researchKeys.conversations(), conversationId, 'messages'] as const,
}

// 默认缓存时间: 5 分钟
const DEFAULT_STALE_TIME = 5 * 60 * 1000

// ==================== LLM Hooks ====================

/**
 * 获取可用的 LLM 模型列表
 */
export function useModels() {
  return useQuery({
    queryKey: researchKeys.models(),
    queryFn: () => researchApi.getModels(),
    staleTime: DEFAULT_STALE_TIME,
  })
}

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

// ==================== 对话 Hooks ====================

/**
 * 获取对话列表
 */
export function useConversations(limit = 50, offset = 0) {
  return useQuery({
    queryKey: researchKeys.conversationList(),
    queryFn: () => researchApi.listConversations(limit, offset),
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * 获取对话详情
 */
export function useConversation(id: number | null) {
  return useQuery({
    queryKey: researchKeys.conversationDetail(id ?? 0),
    queryFn: () => researchApi.getConversation(id!),
    enabled: id !== null && id > 0,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * 获取对话消息
 */
export function useMessages(conversationId: number | null, limit = 100) {
  return useQuery({
    queryKey: researchKeys.messages(conversationId ?? 0),
    queryFn: () => researchApi.getMessages(conversationId!, limit),
    enabled: conversationId !== null && conversationId > 0,
    staleTime: 60 * 1000, // 消息缓存 1 分钟（用户可能正在聊天）
  })
}

/**
 * 对话操作 mutations
 */
export function useConversationMutations() {
  const queryClient = useQueryClient()

  const invalidateConversations = () => {
    queryClient.invalidateQueries({ queryKey: researchKeys.conversations() })
  }

  // 创建对话
  const createMutation = useMutation({
    mutationFn: (request: CreateConversationRequest) => researchApi.createConversation(request),
    onSuccess: () => {
      invalidateConversations()
    },
  })

  // 删除对话
  const deleteMutation = useMutation({
    mutationFn: (id: number) => researchApi.deleteConversation(id),
    onSuccess: () => {
      invalidateConversations()
    },
  })

  // 发送消息 (同步)
  const chatMutation = useMutation({
    mutationFn: ({ conversationId, request }: { conversationId: number; request: ChatRequest }) =>
      researchApi.chat(conversationId, request),
    onSuccess: (_, { conversationId }) => {
      queryClient.invalidateQueries({ queryKey: researchKeys.messages(conversationId) })
    },
  })

  return {
    create: createMutation,
    delete: deleteMutation,
    chat: chatMutation,
  }
}

/**
 * 综合研报管理 hook
 */
export function useResearchManager() {
  const reportMutations = useReportMutations()
  const conversationMutations = useConversationMutations()

  return {
    ...reportMutations,
    createConversation: conversationMutations.create,
    deleteConversation: conversationMutations.delete,
    chat: conversationMutations.chat,
  }
}
