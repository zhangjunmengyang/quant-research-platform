/**
 * Factor module type definitions
 * Mirrors backend Pydantic models for type safety
 */

// 因子类型枚举
export type FactorType = 'time_series' | 'cross_section'

export const FACTOR_TYPE_LABELS: Record<FactorType, string> = {
  time_series: '时序',
  cross_section: '截面',
}

export interface Factor {
  filename: string
  factor_type: FactorType
  uuid?: string
  style?: string
  formula?: string
  input_data?: string
  value_range?: string
  description?: string
  analysis?: string
  code_path?: string
  code_content?: string

  // Scores
  llm_score?: number
  code_complexity?: number

  // Performance metrics
  ic?: number
  rank_ic?: number
  backtest_sharpe?: number
  backtest_ic?: number
  backtest_ir?: number
  turnover?: number
  decay?: number
  last_backtest_date?: string

  // Classification
  market_regime?: string
  best_holding_period?: number
  tags?: string  // 标签（英文逗号分隔）

  // Status
  verified: boolean  // 人工校验状态（通过/未审查）
  verify_note?: string
  excluded?: boolean  // 是否已排除
  exclude_reason?: string  // 排除原因

  // Timestamps
  created_at?: string
  updated_at?: string
}

export interface FactorUpdate {
  style?: string
  formula?: string
  input_data?: string
  value_range?: string
  description?: string
  analysis?: string
  llm_score?: number
  verify_note?: string
  market_regime?: string
  best_holding_period?: number
  tags?: string
}

export type ExcludedFilter = 'all' | 'active' | 'excluded'

export interface FactorListParams {
  page?: number
  page_size?: number
  search?: string
  style?: string
  factor_type?: FactorType
  score_min?: number
  score_max?: number
  verified?: boolean
  excluded?: ExcludedFilter
  order_by?: string
  order_desc?: boolean
}

export interface FactorStats {
  total: number
  excluded: number
  scored: number
  verified: number
  avg_score?: number
  style_distribution: Record<string, number>
  score_distribution: Record<string, number>
  factor_type_distribution: Record<string, number>
}

export interface FactorVerifyRequest {
  note?: string
}

// Table column configuration
export interface FactorColumn {
  key: keyof Factor
  label: string
  width?: number
  editable?: boolean
  sortable?: boolean
}

export const FACTOR_COLUMNS: FactorColumn[] = [
  { key: 'filename', label: '文件名', width: 180, sortable: true },
  { key: 'factor_type', label: '类型', width: 70, sortable: true },
  { key: 'style', label: '风格', width: 100, editable: true, sortable: true },
  { key: 'tags', label: '标签', width: 150, editable: true },
  { key: 'formula', label: '核心公式', width: 250, editable: true },
  { key: 'input_data', label: '输入数据', width: 120, editable: true },
  { key: 'value_range', label: '值域', width: 100, editable: true },
  { key: 'description', label: '刻画特征', width: 200, editable: true },
  { key: 'llm_score', label: '评分', width: 70, sortable: true },
  { key: 'ic', label: 'IC', width: 70, sortable: true },
  { key: 'rank_ic', label: 'RankIC', width: 80, sortable: true },
  { key: 'verified', label: '人工校验', width: 80, sortable: true },
  { key: 'created_at', label: '入库时间', width: 150, sortable: true },
]

export const DEFAULT_VISIBLE_COLUMNS: (keyof Factor)[] = [
  'filename',
  'factor_type',
  'style',
  'tags',
  'formula',
  'llm_score',
  'verified',
  'created_at',
]

// ============= 因子分组分析 =============

export type DataType = 'spot' | 'swap' | 'all'
export type BinMethod = 'pct' | 'val'

export interface FactorGroupAnalysisRequest {
  /** 因子字典 {因子名: [参数列表]} */
  factor_dict: Record<string, unknown[]>
  /** 过滤条件列表 */
  filter_list?: Array<[string, string, unknown]>
  /** 数据类型 */
  data_type?: DataType
  /** 分组数量 (2-20) */
  bins?: number
  /** 分箱方法: pct(分位数) 或 val(等宽) */
  method?: BinMethod
}

export interface GroupCurvePoint {
  date: string
  values: Record<string, number>  // {group_name: nav_value}
}

export interface GroupBarData {
  group: string
  nav: number
  label: string  // Min Value / Max Value / ''
}

export interface FactorGroupAnalysisResponse {
  factor_name: string
  bins: number
  method: string
  data_type: string
  labels: string[]  // 分组标签列表
  curve_data: GroupCurvePoint[]  // 净值曲线数据
  bar_data: GroupBarData[]  // 柱状图数据
  error?: string
}

// ============= 因子创建 =============

export interface FactorCreateRequest {
  /** 因子代码内容 */
  code_content: string
  /** 因子文件名（可选，不填则自动命名） */
  filename?: string
  /** 风格分类 */
  style?: string
  /** 核心公式 */
  formula?: string
  /** 刻画特征 */
  description?: string
}

export interface FactorCreateResponse {
  filename: string
  message: string
  auto_named: boolean
}
