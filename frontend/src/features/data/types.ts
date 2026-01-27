/**
 * Data Module Type Definitions
 * 数据模块类型定义
 */

/**
 * Symbol (coin) info with availability flags
 *
 * 通过 has_spot/has_swap 可以区分:
 * - 只有现货: has_spot=true, has_swap=false
 * - 只有合约: has_spot=false, has_swap=true
 * - 两者都有: has_spot=true, has_swap=true
 */
export interface Symbol {
  symbol: string
  name?: string
  exchange?: string
  quote_currency: string
  base_currency: string
  is_active: boolean
  has_spot: boolean   // 是否有现货数据
  has_swap: boolean   // 是否有合约数据
  first_candle_time?: string  // K线开始时间
  last_candle_time?: string   // K线结束时间
  kline_count?: number        // K线数量
}

/**
 * OHLCV K-line data with all available fields
 */
export interface KlineData {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number  // 成交量（基础货币）
  quote_volume?: number  // 成交额（计价货币）
  trade_num?: number  // 成交笔数
  taker_buy_base_asset_volume?: number  // 主动买入成交量
  taker_buy_quote_asset_volume?: number  // 主动买入成交额
  funding_fee?: number  // 资金费率（仅合约）
  avg_price_1m?: number  // 1分钟均价
  avg_price_5m?: number  // 5分钟均价
}

/**
 * Statistics for a specific data type (spot/swap)
 */
export interface DataTypeStats {
  total_symbols: number
  active_symbols: number
  total_records: number
  data_start_date?: string
  data_end_date?: string
}

/**
 * Data overview statistics
 */
export interface DataOverview {
  total_symbols: number  // 所有币种总数（去重）
  spot: DataTypeStats    // 现货数据统计
  swap: DataTypeStats    // 合约数据统计
  last_updated?: string
  available_factors?: string[]
}

/**
 * Factor calculation request
 */
export interface FactorCalcRequest {
  symbol: string
  factor_name: string
  params: number[]
  data_type?: 'spot' | 'swap'
  start_date?: string  // 起始日期 (YYYY-MM-DD)
  end_date?: string    // 结束日期 (YYYY-MM-DD)
  limit?: number
}

/**
 * Factor value data point
 */
export interface FactorValueItem {
  time: string
  value: number | null
}

/**
 * Factor calculation result for a single parameter
 */
export interface FactorParamResult {
  param: number
  data: FactorValueItem[]
  stats: {
    count?: number
    mean?: number | null
    std?: number | null
    min?: number | null
    max?: number | null
    latest?: number | null
  }
}

/**
 * Factor calculation result
 */
export interface FactorCalcResult {
  symbol: string
  factor_name: string
  data_type: string
  results: FactorParamResult[]
}

/**
 * Available factor for calculation
 */
export interface AvailableFactor {
  name: string
  description?: string
  default_params: number[]
  param_names?: string[]
}

/**
 * Cross-section data (ranking at a specific time)
 */
export interface CrossSectionData {
  time: string
  data: Array<{
    symbol: string
    value: number
    rank: number
  }>
}

/**
 * Tag info with count
 */
export interface TagInfo {
  tag: string
  count: number
}
