/**
 * Stock Hub (A股千因子) 类型定义
 * 镜像后端 domains/stock_hub/models/ 的 Pydantic 模型
 */

export interface StockHubStatus {
  available: boolean
  stock_framework_path: string
  stock_framework_exists: boolean
  fuel_python_exists: boolean
  factor_lib_exists: boolean
  section_factor_lib_exists: boolean
}

export type StockFactorCategory = 'H财务' | '技术' | '截面'

export const CATEGORY_LABELS: Record<StockFactorCategory, string> = {
  H财务: 'H财务因子',
  技术: '技术因子',
  截面: '截面因子',
}

export interface StockFactorMeta {
  name: string
  category: StockFactorCategory
  library: '因子库' | '截面因子库'
  has_add_factor: boolean
  fin_cols: string[]
  ov_cols: string[]
  extra_data: string[]
  description: string
  example_select: string
  example_filter: string
  file_path: string
  code?: string
}

export interface StockFactorListParams {
  category?: string
  search?: string
  page?: number
  page_size?: number
}

export interface StockFactorListResponse {
  factors: StockFactorMeta[]
  total: number
  page: number
  page_size: number
}

export interface StockCategoryStats {
  [category: string]: number
}

// ===== 回测配置 =====

export interface StockFactorConfig {
  name: string
  ascending: boolean
  param: string
  weight: number
}

export interface StockFilterConfig {
  name: string
  param: string
  condition: string
  keep: boolean
}

export interface StockStrategyConfig {
  name: string
  hold_period: string
  offset_list: number[]
  select_num: number
  cap_weight: number
  rebalance_time: string
  factor_list: StockFactorConfig[]
  filter_list: StockFilterConfig[]
}

export interface StockBacktestRequest {
  backtest_name: string
  start_date: string
  end_date?: string
  strategies: StockStrategyConfig[]
  performance_mode?: string
  stay_real?: boolean
  excluded_boards?: string[]
  days_listed?: number
  total_cap_usage?: number
  initial_cash?: number
  c_rate?: number
  t_rate?: number
  stock_timing_order_price?: string
}

export interface StockBacktestResult {
  status: 'ok' | 'error' | 'running'
  message: string
  result_path?: string
  log_output?: string
  summary?: Record<string, unknown>
}

export interface StockBacktestTask {
  task_id: string
  status: string
  submitted_at: number
  backtest_name?: string
  result?: StockBacktestResult
}

// ===== IC 分析 =====

export interface StockICAnalysisRequest {
  result_path: string
  factor_name: string
  hold_period?: string
  group_num?: number
}

export interface StockICAnalysisData {
  ic_mean: number
  icir: number
  t_stat: number
  group_returns: Record<string, number>
}

export interface StockICAnalysisResult {
  status: string
  data?: StockICAnalysisData
  message?: string
}

// ===== 表格列 =====

export interface StockFactorColumn {
  key: string
  label: string
  width?: number
  sortable?: boolean
}

export const STOCK_FACTOR_COLUMNS: StockFactorColumn[] = [
  { key: 'name', label: '因子名称', width: 200, sortable: true },
  { key: 'category', label: '分类', width: 80, sortable: true },
  { key: 'library', label: '因子库', width: 100 },
  { key: 'has_add_factor', label: 'add_factor', width: 90 },
  { key: 'description', label: '描述', width: 300 },
  { key: 'fin_cols', label: '财务列', width: 150 },
  { key: 'ov_cols', label: 'OV列', width: 150 },
]

export const DEFAULT_STOCK_FACTOR_VISIBLE_COLUMNS = [
  'name',
  'category',
  'has_add_factor',
  'description',
]

// ===== 因子评估 =====

export interface ModuleScore {
  score: number
  analysis: string
}

export interface FactorEvaluation {
  factor_name: string
  factor_category: string
  evaluated_at: number
  logic: ModuleScore | null
  backtest: ModuleScore | null
  effectiveness: ModuleScore | null
  overall_score: number | null
  overall_summary: string | null
  tags: string[]
  verdict: string // "推荐" | "观望" | "弃用"
  backtest_snapshot: Record<string, unknown> | null
  ic_snapshot: Record<string, unknown> | null
}

export interface EvaluationRequest {
  factor_name: string
  factor_code?: string
  factor_category?: string
  factor_description?: string
  backtest_result?: Record<string, unknown>
  ic_data?: Record<string, unknown>
}

export interface EvaluationListItem {
  factor_name: string
  factor_category: string
  evaluated_at: number
  overall_score: number | null
  verdict: string
  tags: string[]
}

// ===== 回测数据源 =====

export interface BacktestInfo {
  name: string
  factor_count: number
  modified_time: string
}

// ===== 增强因子分析 =====

export interface EnhancedAnalysisRequest {
  factor_name: string
  period_offset_list: string[]
  rebalance_time: string
  bins: number
  backtest_name?: string
}

export interface EnhancedAnalysisData {
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
  html_path: string
  pkl_path: string
  elapsed_seconds: number
}

export interface CachedFactorsData {
  factors: string[]
  total: number
}

export interface AnalysisResultItem {
  factor_name: string
  score: number
  ic_mean: number
  icir: number
  ic_ratio: string
  config: string
}

// ===== 双因子分析 =====

export interface DualAnalysisRequest {
  main_factor: string
  sub_factor: string
  period_offset_list?: string[]
  rebalance_time?: string
  bins?: number
  backtest_name?: string
}

export interface HeatmapData {
  columns: string[]
  index: string[]
  values: number[][]
}

export interface DualStyleExposure {
  main: number
  sub: number
  dual: number
}

export interface DualAnalysisData {
  main_factor: string
  sub_factor: string
  start_date: string
  end_date: string
  period_offset_list: string[]
  rebalance_time: string
  mix_nv: HeatmapData
  mix_prop: HeatmapData
  filter_nv_ms: HeatmapData
  filter_nv_sm: HeatmapData
  style_exposure: Record<string, DualStyleExposure>
  correlation_text: string
  html_path: string
  elapsed_seconds: number
}
