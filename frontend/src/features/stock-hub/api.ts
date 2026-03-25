/**
 * Stock Hub API client
 * 后端返回 {"data": T}，不走框架标准 ApiResponse 格式
 */

import { apiClient } from '@/lib/api/client'
import type {
  StockFactorMeta,
  StockFactorListParams,
  StockFactorListResponse,
  StockCategoryStats,
  StockBacktestRequest,
  StockBacktestTask,
  StockICAnalysisRequest,
  StockICAnalysisResult,
  StockHubStatus,
  EvaluationRequest,
  FactorEvaluation,
  EvaluationListItem,
  EnhancedAnalysisRequest,
  EnhancedAnalysisData,
  CachedFactorsData,
  AnalysisResultItem,
  DualAnalysisRequest,
  DualAnalysisData,
  BacktestInfo,
} from './types'

const BASE = '/stock'

function unwrap<T>(resp: { data: { data: T } }): T {
  return resp.data.data
}

export const stockHubApi = {
  // ===== 状态检查 =====

  getStatus: async (): Promise<StockHubStatus> => {
    const resp = await apiClient.get(`${BASE}/status`)
    return unwrap(resp)
  },

  // ===== 因子查询 =====

  listFactors: async (params: StockFactorListParams = {}): Promise<StockFactorListResponse> => {
    const resp = await apiClient.get(`${BASE}/factors`, { params })
    return unwrap(resp)
  },

  getCategories: async (): Promise<StockCategoryStats> => {
    const resp = await apiClient.get(`${BASE}/factors/categories`)
    return unwrap(resp)
  },

  getFactor: async (name: string, includeCode = false): Promise<StockFactorMeta> => {
    const resp = await apiClient.get(`${BASE}/factors/${encodeURIComponent(name)}`, {
      params: includeCode ? { include_code: true } : {},
    })
    return unwrap(resp)
  },

  refreshFactors: async (): Promise<{ message: string; categories: StockCategoryStats }> => {
    const resp = await apiClient.post(`${BASE}/factors/refresh`)
    return unwrap(resp)
  },

  // ===== 回测 =====

  submitBacktest: async (
    request: StockBacktestRequest
  ): Promise<{ task_id: string; result: StockBacktestTask['result'] }> => {
    const resp = await apiClient.post(`${BASE}/backtest`, request, {
      timeout: 1200000, // 20分钟
    })
    return unwrap(resp)
  },

  getBacktestResult: async (taskId: string): Promise<StockBacktestTask> => {
    const resp = await apiClient.get(`${BASE}/backtest/${taskId}`)
    return unwrap(resp)
  },

  listBacktests: async (): Promise<{ tasks: StockBacktestTask[] }> => {
    const resp = await apiClient.get(`${BASE}/backtest`)
    return unwrap(resp)
  },

  // ===== IC 分析 =====

  analyzeIC: async (request: StockICAnalysisRequest): Promise<StockICAnalysisResult> => {
    const resp = await apiClient.post(`${BASE}/analysis/ic`, request, {
      timeout: 600000, // 10分钟
    })
    return unwrap(resp)
  },

  // ===== 因子评估 =====

  evaluateFactor: async (request: EvaluationRequest): Promise<FactorEvaluation> => {
    const resp = await apiClient.post(`${BASE}/evaluation`, request, {
      timeout: 120000, // 2 minutes for AI evaluation
    })
    return unwrap(resp)
  },

  listEvaluations: async (): Promise<{ evaluations: EvaluationListItem[] }> => {
    const resp = await apiClient.get(`${BASE}/evaluations`)
    return unwrap(resp)
  },

  getEvaluation: async (factorName: string): Promise<FactorEvaluation> => {
    const resp = await apiClient.get(`${BASE}/evaluation/${encodeURIComponent(factorName)}`)
    return unwrap(resp)
  },

  // ===== 增强因子分析 =====

  enhancedAnalyze: async (request: EnhancedAnalysisRequest): Promise<EnhancedAnalysisData> => {
    const resp = await apiClient.post(`${BASE}/analysis/enhanced`, request, {
      timeout: 600000, // 10 minutes
    })
    return unwrap(resp)
  },

  listAvailableBacktests: async (): Promise<{ backtests: BacktestInfo[]; total: number }> => {
    const resp = await apiClient.get(`${BASE}/analysis/available-backtests`)
    return unwrap(resp)
  },

  listCachedFactors: async (backtestName?: string): Promise<CachedFactorsData> => {
    const resp = await apiClient.get(`${BASE}/analysis/cached-factors`, {
      params: backtestName ? { backtest_name: backtestName } : {},
      timeout: 60000,
    })
    return unwrap(resp)
  },

  listAnalysisResults: async (cfgStr?: string): Promise<{ results: AnalysisResultItem[]; total: number }> => {
    const resp = await apiClient.get(`${BASE}/analysis/results`, {
      params: cfgStr ? { cfg_str: cfgStr } : {},
    })
    return unwrap(resp)
  },

  dualAnalyze: async (request: DualAnalysisRequest): Promise<DualAnalysisData> => {
    const resp = await apiClient.post(`${BASE}/analysis/dual`, request, {
      timeout: 600000,
    })
    return unwrap(resp)
  },

  getAnalysisReportUrl: (factorName: string, cfgStr?: string): string => {
    const params = cfgStr ? `?cfg_str=${encodeURIComponent(cfgStr)}` : ''
    return `/api${BASE}/analysis/report/${encodeURIComponent(factorName)}${params}`
  },
}
