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
  verification_status: number  // 验证状态（0=未验证, 1=通过, 2=废弃）
  verify_note?: string
  excluded?: boolean  // 是否已排除
  exclude_reason?: string  // 排除原因

  // Timestamps
  created_at?: string
  updated_at?: string

  // 参数分析结果 (JSON 字符串)
  param_analysis?: string
}

// ============= 参数分析类型 (新版本 - 复用 run_backtest 结构) =============

/** 因子列表项: [因子名, 排序方向, 参数, 权重] */
export type FactorListItem = [string, boolean, number, number]

/** 过滤因子配置: [因子名, 参数, 过滤条件, 是否正排序] */
export type FilterItem = [string, number, string, boolean]

/** 策略配置（与 run_backtest 相同结构） */
export interface StrategyConfig {
  factor_list: FactorListItem[]
  hold_period?: string
  market?: string
  long_select_coin_num?: number
  short_select_coin_num?: number
  long_cap_weight?: number
  short_cap_weight?: number
  // 前置过滤
  filter_list?: FilterItem[]
  long_filter_list?: FilterItem[]
  short_filter_list?: FilterItem[]
  // 后置过滤
  filter_list_post?: FilterItem[]
  long_filter_list_post?: FilterItem[]
  short_filter_list_post?: FilterItem[]
}

/** 参数分析配置 */
export interface ParamAnalysisConfig {
  /** 策略配置列表 */
  strategy_list: StrategyConfig[]
  /** 参数网格: { 路径表达式: 值列表 } */
  param_grid: Record<string, (string | number)[]>
  /** 回测开始日期 */
  start_date?: string
  /** 回测结束日期 */
  end_date?: string
  /** 杠杆倍数 */
  leverage?: number
}

/** 参数分析结果项（动态字段由 grid_keys 决定） */
export interface ParamAnalysisResult {
  /** 回测指标 */
  annual_return?: number
  max_drawdown?: number
  sharpe_ratio?: number
  win_rate?: number
  cumulative_return?: number
  error?: string
  /** 动态参数字段（由 grid_keys 决定） */
  [key: string]: string | number | undefined
}

/** 参数分析数据 */
export interface ParamAnalysisData {
  updated_at: string
  /** 图表类型: bar=柱状图(1维), heatmap=热力图(2维) */
  chart_type: 'bar' | 'heatmap'
  /** 配置信息 */
  config: ParamAnalysisConfig
  /** 参数网格维度的键名列表 */
  grid_keys: string[]
  /** 所有参数组合的结果 */
  results: ParamAnalysisResult[]
  /** 最优参数组合的结果（包含 grid_keys 对应的参数值和指标） */
  best_result: ParamAnalysisResult
  /** 评价指标 */
  indicator: string
  /** ECharts 图表配置 */
  chart: EChartsOption
}

/** 类型守卫：判断是否为二维分析 */
export function isParamAnalysis2D(data: ParamAnalysisData): boolean {
  return data.chart_type === 'heatmap'
}

/** 从 grid_key 提取显示名称（去掉 $ 前缀） */
export function getGridKeyDisplayName(key: string): string {
  // "$window" -> "window"
  // "$hold" -> "hold"
  return key.startsWith('$') ? key.slice(1) : key
}

// ECharts 配置类型 (简化版)
export interface EChartsOption {
  title?: Record<string, unknown>
  tooltip?: Record<string, unknown>
  xAxis?: Record<string, unknown>
  yAxis?: Record<string, unknown>
  series?: Array<Record<string, unknown>>
  grid?: Record<string, unknown>
  visualMap?: Record<string, unknown>
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
  verification_status?: number  // 验证状态（0=未验证, 1=通过, 2=废弃）
  excluded?: ExcludedFilter
  order_by?: string
  order_desc?: boolean
}

export interface FactorStats {
  total: number
  excluded: number
  scored: number
  passed: number  // 验证通过数量
  failed: number  // 废弃（失败研究）数量
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
  { key: 'verification_status', label: '验证状态', width: 80, sortable: true },
  { key: 'created_at', label: '入库时间', width: 150, sortable: true },
]

export const DEFAULT_VISIBLE_COLUMNS: (keyof Factor)[] = [
  'filename',
  'factor_type',
  'style',
  'tags',
  'formula',
  'llm_score',
  'verification_status',
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
