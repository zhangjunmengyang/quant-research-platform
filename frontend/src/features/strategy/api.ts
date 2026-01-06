/**
 * Strategy API client
 */

import { apiClient, type ApiResponse, type PaginatedResponse } from '@/lib/api/client'
import type {
  Strategy,
  StrategyCreate,
  StrategyUpdate,
  StrategyListParams,
  StrategyStats,
  BacktestRequest,
  SimpleBacktestRequest,
  BacktestStatus,
  BacktestResult,
  BacktestTemplate,
  BacktestConfigResponse,
  BatchBacktestRequest,
  BatchBacktestStatus,
  BacktestTask,
  TaskExecution,
  CreateTaskRequest,
  UpdateTaskRequest,
  DuplicateTaskRequest,
  ExecuteTaskRequest,
  ExecutionSubmitResponse,
  TaskStats,
  ExportToStrategyRequest,
  ExportToStrategyResponse,
  TaskListParams,
  ExecutionListParams,
  // 策略分析类型
  ParamSearchRequest,
  ParamSearchResponse,
  ParamAnalysisRequest,
  ParamAnalysisResponse,
  BacktestComparisonRequest,
  BacktestComparisonResponse,
  FactorComparisonRequest,
  FactorComparisonResponse,
  StrategyComparisonRequest,
  CoinSimilarityResponse,
  EquityCorrelationResponse,
} from './types'

const STRATEGY_URL = '/strategies'
const BACKTEST_URL = '/backtest'
const TASKS_URL = '/tasks'
const ANALYSIS_URL = '/analysis'

export const strategyApi = {
  /**
   * Get paginated strategy list
   */
  list: async (params: StrategyListParams = {}): Promise<PaginatedResponse<Strategy>> => {
    const { data } = await apiClient.get<ApiResponse<PaginatedResponse<Strategy>>>(
      `${STRATEGY_URL}/`,
      { params }
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch strategies')
    }
    return data.data
  },

  /**
   * Get strategy by ID
   */
  get: async (id: string): Promise<Strategy> => {
    const { data } = await apiClient.get<ApiResponse<Strategy>>(`${STRATEGY_URL}/${id}`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Strategy not found')
    }
    return data.data
  },

  /**
   * Create new strategy
   */
  create: async (request: StrategyCreate): Promise<Strategy> => {
    const { data } = await apiClient.post<ApiResponse<Strategy>>(`${STRATEGY_URL}/`, request)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to create strategy')
    }
    return data.data
  },

  /**
   * Update strategy
   */
  update: async (id: string, update: StrategyUpdate): Promise<Strategy> => {
    const { data } = await apiClient.patch<ApiResponse<Strategy>>(`${STRATEGY_URL}/${id}`, update)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to update strategy')
    }
    return data.data
  },

  /**
   * Delete strategy
   */
  delete: async (id: string): Promise<void> => {
    const { data } = await apiClient.delete<ApiResponse<null>>(`${STRATEGY_URL}/${id}`)
    if (!data.success) {
      throw new Error(data.error || 'Failed to delete strategy')
    }
  },

  /**
   * Get strategy statistics
   */
  getStats: async (): Promise<StrategyStats> => {
    const { data } = await apiClient.get<ApiResponse<StrategyStats>>(`${STRATEGY_URL}/stats`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch stats')
    }
    return data.data
  },
}

export const backtestApi = {
  /**
   * Submit full backtest task
   */
  submit: async (request: BacktestRequest): Promise<BacktestStatus> => {
    const { data } = await apiClient.post<ApiResponse<BacktestStatus>>(
      `${BACKTEST_URL}/submit`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to submit backtest')
    }
    return data.data
  },

  /**
   * Submit batch backtest tasks
   * 批量提交回测任务，后端并行执行
   */
  submitBatch: async (request: BatchBacktestRequest): Promise<BatchBacktestStatus> => {
    const { data } = await apiClient.post<ApiResponse<BatchBacktestStatus>>(
      `${BACKTEST_URL}/submit/batch`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to submit batch backtest')
    }
    return data.data
  },

  /**
   * Submit simple backtest task (for quick testing)
   */
  submitSimple: async (request: SimpleBacktestRequest): Promise<BacktestStatus> => {
    const { data } = await apiClient.post<ApiResponse<BacktestStatus>>(
      `${BACKTEST_URL}/submit/simple`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to submit backtest')
    }
    return data.data
  },

  /**
   * Get backtest status
   */
  getStatus: async (taskId: string): Promise<BacktestStatus> => {
    const { data } = await apiClient.get<ApiResponse<BacktestStatus>>(
      `${BACKTEST_URL}/${taskId}/status`
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to get backtest status')
    }
    return data.data
  },

  /**
   * Get batch backtest status
   * 批量获取回测任务状态
   */
  getBatchStatus: async (taskIds: string[]): Promise<BatchBacktestStatus> => {
    const { data } = await apiClient.post<ApiResponse<BatchBacktestStatus>>(
      `${BACKTEST_URL}/status/batch`,
      taskIds
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to get batch backtest status')
    }
    return data.data
  },

  /**
   * Get backtest result
   */
  getResult: async (taskId: string): Promise<BacktestResult> => {
    const { data } = await apiClient.get<ApiResponse<BacktestResult>>(
      `${BACKTEST_URL}/${taskId}/result`
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to get backtest result')
    }
    return data.data
  },

  /**
   * Cancel backtest
   */
  cancel: async (taskId: string): Promise<void> => {
    const { data } = await apiClient.delete<ApiResponse<null>>(`${BACKTEST_URL}/${taskId}`)
    if (!data.success) {
      throw new Error(data.error || 'Failed to cancel backtest')
    }
  },

  /**
   * Get current backtest config (defaults and available factors)
   */
  getConfig: async (): Promise<BacktestConfigResponse> => {
    const { data } = await apiClient.get<ApiResponse<BacktestConfigResponse>>(
      `${BACKTEST_URL}/config`
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch config')
    }
    return data.data
  },

  /**
   * Get backtest templates
   */
  getTemplates: async (): Promise<BacktestTemplate[]> => {
    const { data } = await apiClient.get<ApiResponse<BacktestTemplate[]>>(
      `${BACKTEST_URL}/templates`
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch templates')
    }
    return data.data
  },
}

// =============================================================================
// 任务管理 API
// =============================================================================

export const taskApi = {
  // -------------------------------------------------------------------------
  // 任务单 CRUD
  // -------------------------------------------------------------------------

  /**
   * 创建任务单
   */
  create: async (request: CreateTaskRequest): Promise<BacktestTask> => {
    const { data } = await apiClient.post<ApiResponse<BacktestTask>>(`${TASKS_URL}/`, request)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to create task')
    }
    return data.data
  },

  /**
   * 获取任务单列表
   */
  list: async (params: TaskListParams = {}): Promise<PaginatedResponse<BacktestTask>> => {
    const { data } = await apiClient.get<ApiResponse<PaginatedResponse<BacktestTask>>>(
      `${TASKS_URL}/`,
      { params }
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch tasks')
    }
    return data.data
  },

  /**
   * 获取任务单详情
   */
  get: async (taskId: string): Promise<BacktestTask> => {
    const { data } = await apiClient.get<ApiResponse<BacktestTask>>(`${TASKS_URL}/${taskId}`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Task not found')
    }
    return data.data
  },

  /**
   * 更新任务单
   */
  update: async (taskId: string, request: UpdateTaskRequest): Promise<BacktestTask> => {
    const { data } = await apiClient.put<ApiResponse<BacktestTask>>(
      `${TASKS_URL}/${taskId}`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to update task')
    }
    return data.data
  },

  /**
   * 删除任务单
   */
  delete: async (taskId: string): Promise<void> => {
    const { data } = await apiClient.delete<ApiResponse<null>>(`${TASKS_URL}/${taskId}`)
    if (!data.success) {
      throw new Error(data.error || 'Failed to delete task')
    }
  },

  /**
   * 复制任务单
   */
  duplicate: async (taskId: string, request: DuplicateTaskRequest): Promise<BacktestTask> => {
    const { data } = await apiClient.post<ApiResponse<BacktestTask>>(
      `${TASKS_URL}/${taskId}/duplicate`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to duplicate task')
    }
    return data.data
  },

  // -------------------------------------------------------------------------
  // 任务执行
  // -------------------------------------------------------------------------

  /**
   * 执行任务单
   */
  execute: async (
    taskId: string,
    request?: ExecuteTaskRequest
  ): Promise<ExecutionSubmitResponse> => {
    const { data } = await apiClient.post<ApiResponse<ExecutionSubmitResponse>>(
      `${TASKS_URL}/${taskId}/execute`,
      request || {}
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to execute task')
    }
    return data.data
  },

  /**
   * 获取任务的执行记录列表
   */
  listExecutions: async (
    taskId: string,
    params: ExecutionListParams = {}
  ): Promise<PaginatedResponse<TaskExecution>> => {
    const { data } = await apiClient.get<ApiResponse<PaginatedResponse<TaskExecution>>>(
      `${TASKS_URL}/${taskId}/executions`,
      { params }
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch executions')
    }
    return data.data
  },

  /**
   * 获取任务统计信息
   */
  getStats: async (taskId: string): Promise<TaskStats> => {
    const { data } = await apiClient.get<ApiResponse<TaskStats>>(`${TASKS_URL}/${taskId}/stats`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch task stats')
    }
    return data.data
  },

  // -------------------------------------------------------------------------
  // 执行记录操作
  // -------------------------------------------------------------------------

  /**
   * 获取执行记录详情
   */
  getExecution: async (executionId: string): Promise<TaskExecution> => {
    const { data } = await apiClient.get<ApiResponse<TaskExecution>>(
      `${TASKS_URL}/executions/${executionId}`
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Execution not found')
    }
    return data.data
  },

  /**
   * 删除执行记录
   */
  deleteExecution: async (executionId: string): Promise<void> => {
    const { data } = await apiClient.delete<ApiResponse<null>>(
      `${TASKS_URL}/executions/${executionId}`
    )
    if (!data.success) {
      throw new Error(data.error || 'Failed to delete execution')
    }
  },

  /**
   * 导出执行结果到策略库
   */
  exportToStrategy: async (
    executionId: string,
    request: ExportToStrategyRequest
  ): Promise<ExportToStrategyResponse> => {
    const { data } = await apiClient.post<ApiResponse<ExportToStrategyResponse>>(
      `${TASKS_URL}/executions/${executionId}/export`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to export to strategy')
    }
    return data.data
  },
}

// =============================================================================
// 策略分析 API
// =============================================================================

export const analysisApi = {
  /**
   * 运行参数搜索
   */
  runParamSearch: async (request: ParamSearchRequest): Promise<ParamSearchResponse> => {
    const { data } = await apiClient.post<ApiResponse<ParamSearchResponse>>(
      `${ANALYSIS_URL}/param-search`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to run param search')
    }
    return data.data
  },

  /**
   * 参数分析（热力图/平原图）
   */
  analyzeParams: async (request: ParamAnalysisRequest): Promise<ParamAnalysisResponse> => {
    const { data } = await apiClient.post<ApiResponse<ParamAnalysisResponse>>(
      `${ANALYSIS_URL}/param-analysis`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to analyze params')
    }
    return data.data
  },

  /**
   * 回测实盘对比
   */
  compareBacktest: async (
    request: BacktestComparisonRequest
  ): Promise<BacktestComparisonResponse> => {
    const { data } = await apiClient.post<ApiResponse<BacktestComparisonResponse>>(
      `${ANALYSIS_URL}/backtest-comparison`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to compare backtest')
    }
    return data.data
  },

  /**
   * 因子值对比
   */
  compareFactorValues: async (
    request: FactorComparisonRequest
  ): Promise<FactorComparisonResponse> => {
    const { data } = await apiClient.post<ApiResponse<FactorComparisonResponse>>(
      `${ANALYSIS_URL}/factor-comparison`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to compare factor values')
    }
    return data.data
  },

  /**
   * 选币相似度分析
   */
  analyzeCoinSimilarity: async (
    request: StrategyComparisonRequest
  ): Promise<CoinSimilarityResponse> => {
    const { data } = await apiClient.post<ApiResponse<CoinSimilarityResponse>>(
      `${ANALYSIS_URL}/coin-similarity`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to analyze coin similarity')
    }
    return data.data
  },

  /**
   * 资金曲线相关性分析
   */
  analyzeEquityCorrelation: async (
    request: StrategyComparisonRequest
  ): Promise<EquityCorrelationResponse> => {
    const { data } = await apiClient.post<ApiResponse<EquityCorrelationResponse>>(
      `${ANALYSIS_URL}/equity-correlation`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to analyze equity correlation')
    }
    return data.data
  },

  /**
   * 获取分析报告
   */
  getReport: (reportPath: string): string => {
    return `${ANALYSIS_URL}/reports/${reportPath}`
  },
}
