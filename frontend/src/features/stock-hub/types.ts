/**
 * Stock Hub 类型定义
 */

export interface StockStatus {
  available: boolean
  analysis_ready: boolean
  framework_configured: boolean
  fuel_python_configured: boolean
  factor_lib_exists: boolean
  section_factor_lib_exists: boolean
  cache_root_exists: boolean
  enhanced_script_exists: boolean
  dual_script_exists: boolean
  available_backtests_count: number
}

export interface StockFactorSummary {
  name: string
  category: string
  description: string
  has_add_factor: boolean
}

export interface StockFactorDetail extends StockFactorSummary {
  fin_cols: string[]
  ov_cols: string[]
  example_select: string
  example_filter: string
}

export interface BacktestSourceInfo {
  name: string
  factor_count: number
  modified_time: string
}

export interface AvailableBacktestsResponse {
  backtests: BacktestSourceInfo[]
  total: number
}

export interface CachedFactorInfo {
  name: string
  display_name: string
  file_size: number
}

export interface EnhancedAnalysisRequest {
  factor_name: string
  period_offset_list: string[]
  rebalance_time: string
  bins: number
  backtest_name?: string
}

export interface ICSeriesPoint {
  date: string
  rank_ic: number
  cum_rank_ic: number
}

export interface ICHeatmap {
  years: string[]
  months: string[]
  values: (number | null)[][]
}

export interface IndustryICEntry {
  name: string
  rank_ic: number
  top_pct: number
  bottom_pct: number
}

export interface MarketCapICEntry {
  group: number
  rank_ic: number
  top_pct: number
  bottom_pct: number
}

export interface AnalysisResult {
  factor_name: string
  score: number
  ic_mean: number
  ic_std: number
  icir: number
  abs_icir: number
  ic_ratio: string
  start_date: string
  end_date: string
  period_offset_list: string[]
  rebalance_time: string
  group_values: Record<string, number>
  style_exposure: Record<string, number>
  elapsed_seconds: number
  // 扩展图表数据（可选，兼容旧版脚本）
  ic_summary?: string | null
  ic_series?: ICSeriesPoint[] | null
  ic_heatmap?: ICHeatmap | null
  group_nav?: Record<string, unknown>[] | null
  group_holding?: Record<string, unknown>[] | null
  industry_ic?: IndustryICEntry[] | null
  market_cap_ic?: MarketCapICEntry[] | null
  // 多周期分析时，各周期明细
  periods?: AnalysisResult[] | null
}

export interface AnalysisTaskSubmit {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  task_type: 'enhanced' | 'dual'
  message: string
}

export interface AnalysisTaskStatus {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  task_type: 'enhanced' | 'dual'
  message: string
  created_at: string
  started_at?: string | null
  completed_at?: string | null
  error_message?: string | null
}

export interface AnalysisTaskResult<T> {
  task_id: string
  status: 'completed' | 'failed'
  task_type: 'enhanced' | 'dual'
  result?: T | null
  error_message?: string | null
}

export interface DualAnalysisRequest {
  main_factor: string
  sub_factor: string
  period_offset_list: string[]
  rebalance_time: string
  bins: number
  backtest_name?: string
}

export interface DualAnalysisResult {
  main_factor: string
  sub_factor: string
  heatmaps: Record<string, unknown>
  style_exposure: Record<string, unknown>
  corr_summary?: string | null
  elapsed_seconds: number
}

export interface StockFactorListParams {
  page?: number
  page_size?: number
  search?: string
  category?: string
}

/** 单条评估条目 */
export interface EvaluationEntry {
  text: string
  isStreaming: boolean
  isEdited: boolean
}

/** AI 评估类型 */
export type EvaluationType =
  | 'comprehensive'
  | 'ic_performance'
  | 'grouping_ability'
  | 'style_profile'
  | 'market_cap'

/** 分析周期预设 */
export const PERIOD_PRESETS = {
  '5日单offset': ['5_0'],
  '5日全offset': ['5_0', '5_1', '5_2', '5_3', '5_4'],
  '周度单offset': ['W_0'],
  '周度全offset': ['W_0', 'W_1', 'W_2', 'W_3', 'W_4'],
} as const

/** 换仓时间选项 */
export const REBALANCE_TIMES = [
  { value: '0930', label: '0930 开盘' },
  { value: '0955', label: '0955 默认' },
  { value: '1000', label: '1000' },
  { value: '1030', label: '1030' },
  { value: '1100', label: '1100' },
  { value: '1300', label: '1300' },
  { value: '1400', label: '1400' },
  { value: '1455', label: '1455' },
  { value: 'close', label: '收盘价' },
] as const
