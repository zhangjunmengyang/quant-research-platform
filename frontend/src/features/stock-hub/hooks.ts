/**
 * Stock Hub React Query Hooks
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
} from '@tanstack/react-query'
import { stockHubApi } from './api'
import type {
  StockFactorListParams,
  StockBacktestRequest,
  StockICAnalysisRequest,
  EvaluationRequest,
  EnhancedAnalysisRequest,
  DualAnalysisRequest,
} from './types'

// Query Keys
export const stockHubKeys = {
  all: ['stock-hub'] as const,
  factors: () => [...stockHubKeys.all, 'factors'] as const,
  factorList: (params: StockFactorListParams) =>
    [...stockHubKeys.factors(), 'list', params] as const,
  factorDetail: (name: string) => [...stockHubKeys.factors(), 'detail', name] as const,
  categories: () => [...stockHubKeys.factors(), 'categories'] as const,
  backtests: () => [...stockHubKeys.all, 'backtests'] as const,
  backtestDetail: (taskId: string) => [...stockHubKeys.backtests(), taskId] as const,
}

const STALE_5MIN = 5 * 60 * 1000

/**
 * Stock Hub 可用性状态
 */
export function useStockHubStatus() {
  return useQuery({
    queryKey: [...stockHubKeys.all, 'status'] as const,
    queryFn: stockHubApi.getStatus,
    staleTime: 60 * 1000,
  })
}

/**
 * A股因子列表（分页+搜索+分类）
 */
export function useStockFactors(params: StockFactorListParams = {}) {
  return useQuery({
    queryKey: stockHubKeys.factorList(params),
    queryFn: () => stockHubApi.listFactors(params),
    placeholderData: keepPreviousData,
    staleTime: STALE_5MIN,
  })
}

/**
 * 单个因子详情
 */
export function useStockFactor(name: string, includeCode = false) {
  return useQuery({
    queryKey: [...stockHubKeys.factorDetail(name), includeCode],
    queryFn: () => stockHubApi.getFactor(name, includeCode),
    enabled: !!name,
    staleTime: STALE_5MIN,
  })
}

/**
 * 因子分类统计
 */
export function useStockCategories() {
  return useQuery({
    queryKey: stockHubKeys.categories(),
    queryFn: stockHubApi.getCategories,
    staleTime: 10 * 60 * 1000,
  })
}

/**
 * 刷新因子库缓存
 */
export function useRefreshStockFactors() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: stockHubApi.refreshFactors,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: stockHubKeys.factors() })
    },
  })
}

/**
 * 提交回测
 */
export function useSubmitBacktest() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: StockBacktestRequest) => stockHubApi.submitBacktest(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: stockHubKeys.backtests() })
    },
  })
}

/**
 * 回测任务列表
 */
export function useStockBacktests() {
  return useQuery({
    queryKey: stockHubKeys.backtests(),
    queryFn: stockHubApi.listBacktests,
    staleTime: 30 * 1000,
  })
}

/**
 * 单个回测结果
 */
export function useStockBacktestResult(taskId: string) {
  return useQuery({
    queryKey: stockHubKeys.backtestDetail(taskId),
    queryFn: () => stockHubApi.getBacktestResult(taskId),
    enabled: !!taskId,
    staleTime: 10 * 1000,
  })
}

/**
 * IC/ICIR 因子分析
 */
export function useStockICAnalysis() {
  return useMutation({
    mutationFn: (req: StockICAnalysisRequest) => stockHubApi.analyzeIC(req),
  })
}

/**
 * 因子评估列表
 */
export function useStockEvaluations() {
  return useQuery({
    queryKey: [...stockHubKeys.all, 'evaluations'] as const,
    queryFn: stockHubApi.listEvaluations,
    staleTime: STALE_5MIN,
  })
}

/**
 * 单因子评估详情
 */
export function useStockEvaluation(factorName: string, enabled = true) {
  return useQuery({
    queryKey: [...stockHubKeys.all, 'evaluation', factorName] as const,
    queryFn: () => stockHubApi.getEvaluation(factorName),
    enabled: !!factorName && enabled,
    staleTime: STALE_5MIN,
    retry: false,
  })
}

/**
 * 触发因子评估
 */
export function useEvaluateFactor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: EvaluationRequest) => stockHubApi.evaluateFactor(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...stockHubKeys.all, 'evaluations'] })
    },
  })
}

// ===== 增强因子分析 =====

/**
 * 增强单因子分析（早盘换仓 + 全offset）
 */
export function useEnhancedAnalysis() {
  return useMutation({
    mutationFn: (req: EnhancedAnalysisRequest) => stockHubApi.enhancedAnalyze(req),
  })
}

/**
 * 双因子分析
 */
export function useDualAnalysis() {
  return useMutation({
    mutationFn: (req: DualAnalysisRequest) => stockHubApi.dualAnalyze(req),
  })
}

/**
 * 可用回测数据源列表
 */
export function useAvailableBacktests() {
  return useQuery({
    queryKey: [...stockHubKeys.all, 'available-backtests'] as const,
    queryFn: stockHubApi.listAvailableBacktests,
    staleTime: 30 * 1000,
  })
}

/**
 * 运行缓存中的可用因子列表
 */
export function useCachedFactors(backtestName?: string) {
  return useQuery({
    queryKey: [...stockHubKeys.all, 'cached-factors', backtestName] as const,
    queryFn: () => stockHubApi.listCachedFactors(backtestName),
    staleTime: 30 * 1000,
  })
}

/**
 * 已有分析结果列表
 */
export function useAnalysisResults(cfgStr?: string) {
  return useQuery({
    queryKey: [...stockHubKeys.all, 'analysis-results', cfgStr] as const,
    queryFn: () => stockHubApi.listAnalysisResults(cfgStr),
    staleTime: 30 * 1000,
  })
}
