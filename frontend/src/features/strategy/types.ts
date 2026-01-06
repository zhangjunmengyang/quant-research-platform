/**
 * Strategy Type Definitions
 * 策略模块类型定义
 *
 * 完整暴露 strategy_hub/core 回测引擎的配置能力
 */

// =============================================================================
// Strategy 基础类型
// =============================================================================

/**
 * Strategy model
 *
 * 包含完整的回测配置和指标，与后端 API Schema 一致。
 */
export interface Strategy {
  // 基础信息
  id: string
  name: string
  description?: string

  // 因子配置 (JSON 字符串)
  factor_list?: string
  factor_params?: string
  strategy_config?: string  // 完整策略配置

  // 回测配置
  start_date?: string
  end_date?: string
  leverage: number
  select_coin_num: number
  trade_type: string

  // 多空配置
  long_select_coin_num?: number
  short_select_coin_num?: number
  long_cap_weight?: number
  short_cap_weight?: number

  // 持仓配置
  hold_period?: string
  offset?: number
  market?: string

  // 排序方向 (JSON 字符串)
  sort_directions?: string

  // 账户配置
  account_type?: string
  initial_usdt?: number
  margin_rate?: number

  // 手续费配置
  swap_c_rate?: number
  spot_c_rate?: number

  // 最小下单量
  swap_min_order_limit?: number
  spot_min_order_limit?: number

  // 价格计算
  avg_price_col?: string

  // 币种过滤
  min_kline_num?: number
  black_list?: string
  white_list?: string

  // 核心绩效指标
  cumulative_return?: number
  annual_return?: number
  max_drawdown?: number
  max_drawdown_start?: string
  max_drawdown_end?: string
  sharpe_ratio?: number
  recovery_rate?: number
  recovery_time?: string

  // 交易统计
  win_periods?: number
  loss_periods?: number
  win_rate?: number
  avg_return_per_period?: number
  profit_loss_ratio?: number
  max_single_profit?: number
  max_single_loss?: number
  max_consecutive_wins?: number
  max_consecutive_losses?: number
  return_std?: number

  // 周期收益 (JSON 字符串)
  year_return?: string
  quarter_return?: string
  month_return?: string

  // 资金曲线 (JSON 字符串)
  equity_curve?: string

  // 元数据
  verified: boolean
  tags?: string
  notes?: string
  task_status?: string
  error_message?: string
  created_at?: string
  updated_at?: string
}

/**
 * Strategy creation request
 */
export interface StrategyCreate {
  name: string
  description?: string
  factor_list: string
  factor_params: string
  start_date: string
  end_date: string
  leverage?: number
  select_coin_num?: number
  trade_type?: string
}

/**
 * Strategy update request
 */
export interface StrategyUpdate {
  name?: string
  description?: string
  factor_list?: string
  factor_params?: string
}

/**
 * Strategy list parameters
 */
export interface StrategyListParams {
  page?: number
  page_size?: number
  verified?: boolean
  order_by?: string
  task_status?: string
}

/**
 * Strategy statistics
 */
export interface StrategyStats {
  total: number
  verified: number
  avg_sharpe?: number
  avg_return?: number
}

// =============================================================================
// 因子配置类型
// =============================================================================

/**
 * 单个选币因子配置
 */
export interface FactorItem {
  /** 因子名称，需与 factors 目录中的因子文件名一致 */
  name: string
  /** 排序方向，true=升序(选小的)，false=降序(选大的) */
  is_sort_asc: boolean
  /** 因子参数 */
  param: number | number[]
  /** 因子权重，多因子时用于加权排序 */
  weight: number
}

/**
 * 单个过滤因子配置
 */
export interface FilterItem {
  /** 过滤因子名称 */
  name: string
  /** 因子参数 */
  param: number | number[]
  /** 过滤方式，格式为 'how:range'，如 'rank:<=10', 'pct:<0.1', 'val:>0' */
  method?: string
  /** 排序方向 */
  is_sort_asc: boolean
}

// =============================================================================
// 策略配置类型
// =============================================================================

/**
 * 单个子策略配置
 * 对应回测引擎 strategy_list 中的一个策略项
 */
export interface StrategyItem {
  /** 策略名称/标识 */
  strategy: string

  // 持仓周期
  /** 持仓周期，如 1H, 6H, 1D, 7D */
  hold_period: string

  // 偏移配置
  /** 策略偏移量 */
  offset: number
  /** 多偏移列表，如 [0, 1, 2] */
  offset_list?: number[]

  // 选币市场范围
  /** 选币范围_优先下单: swap_swap, spot_spot, spot_swap, mix_spot, mix_swap */
  market: string

  // 多头配置
  /** 多头选币数量，整数=固定数量，小数=百分比 */
  long_select_coin_num: number
  /** 多头资金权重 */
  long_cap_weight: number

  // 空头配置
  /** 空头选币数量，'long_nums'=与多头相同 */
  short_select_coin_num: number | string
  /** 空头资金权重 */
  short_cap_weight: number

  // 策略整体权重
  /** 策略在组合中的资金权重 */
  cap_weight: number

  // 选币因子
  /** 选币因子列表（多空共用） */
  factor_list: FactorItem[]
  /** 多头专用选币因子（多空分离时使用） */
  long_factor_list?: FactorItem[]
  /** 空头专用选币因子（多空分离时使用） */
  short_factor_list?: FactorItem[]

  // 前置过滤因子
  /** 前置过滤因子列表（多空共用） */
  filter_list: FilterItem[]
  /** 多头专用前置过滤因子 */
  long_filter_list?: FilterItem[]
  /** 空头专用前置过滤因子 */
  short_filter_list?: FilterItem[]

  // 后置过滤因子
  /** 后置过滤因子列表 */
  filter_list_post: FilterItem[]

  /** 是否使用策略文件中的自定义计算函数 */
  use_custom_func: boolean
}

// =============================================================================
// 回测请求类型
// =============================================================================

/**
 * 完整回测请求配置
 * 对应 config/backtest_config.py 的全部可配置项
 */
export interface BacktestRequest {
  /** 回测名称 */
  name: string

  // 时间配置
  /** 回测开始日期，格式 YYYY-MM-DD */
  start_date: string
  /** 回测结束日期，格式 YYYY-MM-DD */
  end_date: string

  // 账户配置
  /** 账户类型: '统一账户' | '普通账户' */
  account_type: '统一账户' | '普通账户'
  /** 初始资金(USDT) */
  initial_usdt: number
  /** 杠杆倍数 */
  leverage: number
  /** 维持保证金率 */
  margin_rate: number

  // 手续费配置
  /** 合约手续费率(含滑点) */
  swap_c_rate: number
  /** 现货手续费率(含滑点) */
  spot_c_rate: number

  // 最小下单量
  /** 合约最小下单量(USDT) */
  swap_min_order_limit: number
  /** 现货最小下单量(USDT) */
  spot_min_order_limit: number

  // 价格计算
  /** 均价计算列 */
  avg_price_col: 'avg_price_1m' | 'avg_price_5m'

  // 币种过滤
  /** 最少上市K线数 */
  min_kline_num: number
  /** 黑名单币种 */
  black_list: string[]
  /** 白名单币种 */
  white_list: string[]

  // 策略列表
  /** 策略配置列表 */
  strategy_list: StrategyItem[]

  // 再择时配置
  /** 再择时配置（可选） */
  re_timing?: Record<string, unknown>
}

/**
 * 简化版回测请求（兼容旧API）
 */
export interface SimpleBacktestRequest {
  strategy_name: string
  factor_list: string[]
  factor_params: Record<string, number[]>
  start_date: string
  end_date: string
  leverage?: number
  select_coin_num?: number
  trade_type?: 'swap' | 'spot'
  hold_period?: string
  initial_usdt?: number
}

// =============================================================================
// 回测状态和结果类型
// =============================================================================

/**
 * Backtest status
 */
export interface BacktestStatus {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  message?: string
  started_at?: string
  completed_at?: string
}

/**
 * 批量回测请求
 * 支持一次提交多个回测任务，后端并行执行
 */
export interface BatchBacktestRequest {
  tasks: BacktestRequest[]
}

/**
 * 批量回测状态
 */
export interface BatchBacktestStatus {
  total: number
  submitted: number
  tasks: BacktestStatus[]
}

/**
 * 回测指标
 */
export interface BacktestMetrics {
  // 收益指标
  cumulative_return?: number
  annual_return?: number
  avg_return_per_period?: number

  // 风险指标
  max_drawdown?: number
  max_drawdown_start?: string
  max_drawdown_end?: string
  return_std?: number

  // 风险调整收益
  sharpe_ratio?: number
  recovery_rate?: number
  recovery_time?: string

  // 胜率统计
  win_periods?: number
  loss_periods?: number
  win_rate?: number
  profit_loss_ratio?: number

  // 极值统计
  max_single_profit?: number
  max_single_loss?: number
  max_consecutive_wins?: number
  max_consecutive_losses?: number
}

/**
 * Backtest result
 */
export interface BacktestResult {
  task_id: string
  strategy_id?: string
  status: string
  metrics?: BacktestMetrics
  equity_curve?: Array<{ time: string; value: number }>
  trades?: Array<{
    time: string
    symbol: string
    side: 'buy' | 'sell'
    price: number
    quantity: number
  }>
  error?: string
}

// =============================================================================
// 回测配置和模板类型
// =============================================================================

/**
 * 回测模板
 */
export interface BacktestTemplate {
  name: string
  description?: string
  strategy_list: StrategyItem[]
  default_config?: {
    leverage?: number
    initial_usdt?: number
    [key: string]: unknown
  }
}

/**
 * 当前回测配置响应
 */
export interface BacktestConfigResponse {
  // 数据路径
  pre_data_path: string
  data_source_dict: Record<string, unknown>

  // 默认时间范围
  start_date: string
  end_date: string

  // 默认交易配置
  account_type: string
  initial_usdt: number
  leverage: number
  margin_rate: number
  swap_c_rate: number
  spot_c_rate: number
  swap_min_order_limit: number
  spot_min_order_limit: number
  avg_price_col: string

  // 币种过滤
  min_kline_num: number
  black_list: string[]
  white_list: string[]
  stable_symbol: string[]

  // 可用因子列表
  available_factors: string[]
}

// =============================================================================
// 辅助函数 - 创建默认值
// =============================================================================

/**
 * 创建默认因子配置
 */
export function createDefaultFactorItem(name: string): FactorItem {
  return {
    name,
    is_sort_asc: true,
    param: 24,
    weight: 1.0,
  }
}

/**
 * 创建默认策略配置
 */
export function createDefaultStrategyItem(): StrategyItem {
  return {
    strategy: 'Strategy',
    hold_period: '1H',
    offset: 0,
    market: 'swap_swap',
    long_select_coin_num: 5,
    long_cap_weight: 1.0,
    short_select_coin_num: 0,
    short_cap_weight: 0,
    cap_weight: 1.0,
    factor_list: [],
    filter_list: [],
    filter_list_post: [],
    use_custom_func: false,
  }
}

/**
 * 创建默认回测请求
 */
export function createDefaultBacktestRequest(): BacktestRequest {
  return {
    name: '',
    start_date: '2024-01-01',
    end_date: '2024-12-31',
    account_type: '统一账户',
    initial_usdt: 10000,
    leverage: 1.0,
    margin_rate: 0.05,
    swap_c_rate: 0.0006,
    spot_c_rate: 0.001,
    swap_min_order_limit: 5,
    spot_min_order_limit: 10,
    avg_price_col: 'avg_price_1m',
    min_kline_num: 0,
    black_list: [],
    white_list: [],
    strategy_list: [],
  }
}

// =============================================================================
// 任务管理类型
// =============================================================================

/**
 * 任务配置（与 BacktestRequest 一致）
 */
export type TaskConfig = BacktestRequest

/**
 * 回测任务单
 * 存储回测配置模板，可被多次执行
 */
export interface BacktestTask {
  id: string
  name: string
  description?: string
  /** 配置 JSON 字符串 */
  config: string
  created_at: string
  updated_at: string
  tags?: string
  notes?: string
  /** 执行次数 */
  execution_count: number
  /** 最后执行时间 */
  last_execution_at?: string
}

/**
 * 任务执行状态
 */
export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

/**
 * 任务执行记录
 * 每次执行的状态和结果
 */
export interface TaskExecution {
  id: string
  task_id: string
  status: ExecutionStatus
  created_at: string
  started_at?: string
  completed_at?: string
  progress: number
  message?: string

  // 因子配置快照
  factor_list?: string
  factor_params?: string

  // 回测配置快照
  start_date?: string
  end_date?: string
  leverage?: number
  account_type?: string
  initial_usdt?: number
  hold_period?: string
  long_select_coin_num?: number
  short_select_coin_num?: number

  // 绩效指标
  cumulative_return?: number
  annual_return?: number
  max_drawdown?: number
  max_drawdown_start?: string
  max_drawdown_end?: string
  sharpe_ratio?: number
  recovery_rate?: number
  recovery_time?: string

  // 交易统计
  win_periods?: number
  loss_periods?: number
  win_rate?: number
  avg_return_per_period?: number
  profit_loss_ratio?: number
  max_single_profit?: number
  max_single_loss?: number
  max_consecutive_wins?: number
  max_consecutive_losses?: number
  return_std?: number

  // 周期收益 (JSON 字符串)
  year_return?: string
  quarter_return?: string
  month_return?: string
  equity_curve?: string

  // 错误信息
  error_message?: string

  // 导出到策略库后的ID
  strategy_id?: string
}

/**
 * 创建任务请求
 */
export interface CreateTaskRequest {
  name: string
  description?: string
  config: TaskConfig
  tags?: string[]
  notes?: string
}

/**
 * 更新任务请求
 */
export interface UpdateTaskRequest {
  name?: string
  description?: string
  config?: TaskConfig
  tags?: string[]
  notes?: string
}

/**
 * 复制任务请求
 */
export interface DuplicateTaskRequest {
  new_name: string
}

/**
 * 执行任务请求
 */
export interface ExecuteTaskRequest {
  config_override?: Record<string, unknown>
}

/**
 * 执行提交响应
 */
export interface ExecutionSubmitResponse {
  execution_id: string
  status: ExecutionStatus
  message: string
}

/**
 * 任务统计信息
 */
export interface TaskStats {
  total: number
  completed: number
  failed: number
  running: number
  pending: number
  avg_annual_return?: number
  avg_sharpe_ratio?: number
  best_annual_return?: number
  worst_annual_return?: number
}

/**
 * 导出到策略库请求
 */
export interface ExportToStrategyRequest {
  strategy_name: string
  description?: string
}

/**
 * 导出到策略库响应
 */
export interface ExportToStrategyResponse {
  strategy_id: string
  message: string
}

/**
 * 任务列表查询参数
 */
export interface TaskListParams {
  page?: number
  page_size?: number
  search?: string
  order_by?: string
  order_desc?: boolean
}

/**
 * 执行记录列表查询参数
 */
export interface ExecutionListParams {
  page?: number
  page_size?: number
  status?: ExecutionStatus
}

// =============================================================================
// 策略分析类型
// =============================================================================

/**
 * 参数搜索请求
 */
export interface ParamSearchRequest {
  /** 搜索任务名称 */
  name: string
  /** 参数搜索范围 {参数名: [参数值列表]} */
  batch_params: Record<string, unknown[]>
  /** 策略模板配置 */
  strategy_template: Record<string, unknown>
  /** 最大并行数 */
  max_workers?: number
}

/**
 * 参数搜索响应
 */
export interface ParamSearchResponse {
  name: string
  total_combinations: number
  status: string
  output_path?: string
  error?: string
}

/**
 * 参数分析请求
 */
export interface ParamAnalysisRequest {
  /** 遍历结果名称 */
  trav_name: string
  /** 参数范围 (可选) */
  batch_params?: Record<string, unknown[]>
  /** X轴参数 */
  param_x: string
  /** Y轴参数，为空则单参数分析 */
  param_y?: string
  /** 固定参数条件 */
  limit_dict?: Record<string, unknown[]>
  /** 评价指标 */
  indicator?: string
}

/**
 * 参数分析响应
 */
export interface ParamAnalysisResponse {
  name: string
  analysis_type: string
  indicator: string
  html_path?: string
  error?: string
}

/**
 * 回测实盘对比请求
 */
export interface BacktestComparisonRequest {
  /** 回测策略名称 */
  backtest_name: string
  /** 对比开始时间 */
  start_time?: string
  /** 对比结束时间 */
  end_time?: string
}

/**
 * 指标对比值
 */
export interface MetricsComparisonValue {
  backtest: number | string
  live: number | string
  diff: number | string
}

/**
 * 回测实盘对比响应
 */
export interface BacktestComparisonResponse {
  backtest_name: string
  start_time?: string
  end_time?: string
  coin_selection_similarity?: number
  metrics_comparison?: Record<string, MetricsComparisonValue>
  html_path?: string
  error?: string
}

/**
 * 因子值对比请求
 */
export interface FactorComparisonRequest {
  /** 回测策略名称 */
  backtest_name: string
  /** 币种名称 */
  coin: string
  /** 因子名称列表，为空则自动检测 */
  factor_names?: string[]
}

/**
 * 因子值对比响应
 */
export interface FactorComparisonResponse {
  backtest_name: string
  coin: string
  factors: string[]
  html_path?: string
  error?: string
}

/**
 * 策略对比类型
 */
export type StrategyComparisonType = 'coin_similarity' | 'equity_correlation'

/**
 * 策略对比请求
 */
export interface StrategyComparisonRequest {
  /** 策略名称列表 (至少2个) */
  strategy_list: string[]
  /** 对比类型 (可选，由具体 API 决定) */
  comparison_type?: StrategyComparisonType
}

/**
 * 选币相似度响应
 */
export interface CoinSimilarityResponse {
  strategies: string[]
  similarity_matrix?: number[][]
  html_path?: string
  error?: string
}

/**
 * 资金曲线相关性响应
 */
export interface EquityCorrelationResponse {
  strategies: string[]
  correlation_matrix?: number[][]
  html_path?: string
  error?: string
}
