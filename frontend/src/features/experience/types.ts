/**
 * Experience module type definitions
 * Mirrors backend Pydantic models for type safety
 */

// ==================== 枚举定义 ====================

/**
 * 经验层级枚举
 */
export type ExperienceLevel = 'strategic' | 'tactical' | 'operational'

export const EXPERIENCE_LEVEL_LABELS: Record<ExperienceLevel, string> = {
  strategic: '战略级',
  tactical: '战术级',
  operational: '操作级',
}

export const EXPERIENCE_LEVEL_DESCRIPTIONS: Record<ExperienceLevel, string> = {
  strategic: '长期有效的研究原则',
  tactical: '特定场景下的研究结论',
  operational: '具体的研究记录',
}

/**
 * 经验状态枚举
 */
export type ExperienceStatus = 'draft' | 'validated' | 'deprecated'

export const EXPERIENCE_STATUS_LABELS: Record<ExperienceStatus, string> = {
  draft: '草稿',
  validated: '已验证',
  deprecated: '已废弃',
}

export const EXPERIENCE_STATUS_COLORS: Record<ExperienceStatus, string> = {
  draft: 'bg-yellow-100 text-yellow-800',
  validated: 'bg-green-100 text-green-800',
  deprecated: 'bg-gray-100 text-gray-500',
}

/**
 * 经验分类枚举
 */
export type ExperienceCategory =
  // 战略级分类
  | 'market_regime_principle'
  | 'factor_design_principle'
  | 'risk_management_principle'
  // 战术级分类
  | 'factor_performance'
  | 'strategy_optimization'
  | 'param_sensitivity'
  // 操作级分类
  | 'successful_experiment'
  | 'failed_experiment'
  | 'research_observation'

export const EXPERIENCE_CATEGORY_LABELS: Record<ExperienceCategory, string> = {
  // 战略级
  market_regime_principle: '市场环境原则',
  factor_design_principle: '因子设计原则',
  risk_management_principle: '风险管理原则',
  // 战术级
  factor_performance: '因子表现结论',
  strategy_optimization: '策略优化结论',
  param_sensitivity: '参数敏感性结论',
  // 操作级
  successful_experiment: '成功实验',
  failed_experiment: '失败实验',
  research_observation: '研究观察',
}

// 按层级分组的分类
export const CATEGORIES_BY_LEVEL: Record<ExperienceLevel, ExperienceCategory[]> = {
  strategic: ['market_regime_principle', 'factor_design_principle', 'risk_management_principle'],
  tactical: ['factor_performance', 'strategy_optimization', 'param_sensitivity'],
  operational: ['successful_experiment', 'failed_experiment', 'research_observation'],
}

/**
 * 来源类型枚举
 */
export type SourceType = 'research' | 'backtest' | 'live_trade' | 'external' | 'manual' | 'curated'

export const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  research: '研究会话',
  backtest: '回测结果',
  live_trade: '实盘交易',
  external: '外部输入',
  manual: '手动录入',
  curated: '提炼生成',
}

/**
 * 关联实体类型枚举
 */
export type EntityType = 'factor' | 'strategy' | 'note' | 'research' | 'experience'

export const ENTITY_TYPE_LABELS: Record<EntityType, string> = {
  factor: '因子',
  strategy: '策略',
  note: '笔记',
  research: '研报',
  experience: '经验',
}

// ==================== 内容接口 ====================

/**
 * 经验核心内容（PARL 框架）
 */
export interface ExperienceContent {
  problem: string   // 面临的问题或挑战
  approach: string  // 采用的方法或策略
  result: string    // 得到的结果
  lesson: string    // 总结的教训或规律
}

/**
 * 经验上下文信息
 */
export interface ExperienceContext {
  market_regime: string    // 市场状态（牛市/熊市/震荡）
  factor_styles: string[]  // 相关的因子风格
  time_horizon: string     // 适用的时间范围（短期/中期/长期）
  asset_class: string      // 资产类别（BTC/ETH/山寨币/全市场）
  tags: string[]           // 自定义标签
}

// ==================== 主接口 ====================

/**
 * 经验完整响应
 */
export interface Experience {
  id: number
  uuid: string
  title: string
  experience_level: ExperienceLevel
  category: string
  content: ExperienceContent
  context: ExperienceContext
  source_type: SourceType
  source_ref: string
  confidence: number
  validation_count: number
  last_validated?: string
  status: ExperienceStatus
  deprecated_reason: string
  created_at?: string
  updated_at?: string
}

/**
 * 创建经验请求
 */
export interface ExperienceCreate {
  title: string
  experience_level?: ExperienceLevel
  category?: string
  content?: ExperienceContent
  context?: ExperienceContext
  source_type?: SourceType
  source_ref?: string
  confidence?: number
}

/**
 * 更新经验请求
 */
export interface ExperienceUpdate {
  title?: string
  experience_level?: ExperienceLevel
  category?: string
  content?: ExperienceContent
  context?: ExperienceContext
  confidence?: number
}

// ==================== 查询参数接口 ====================

/**
 * 经验列表查询参数
 */
export interface ExperienceListParams {
  page?: number
  page_size?: number
  experience_level?: ExperienceLevel
  category?: string
  status?: ExperienceStatus
  source_type?: SourceType
  market_regime?: string
  factor_styles?: string
  min_confidence?: number
  include_deprecated?: boolean
  order_by?: string
  order_desc?: boolean
}

/**
 * 语义查询参数
 */
export interface ExperienceQueryParams {
  query: string
  experience_level?: ExperienceLevel
  category?: string
  market_regime?: string
  factor_styles?: string[]
  min_confidence?: number
  include_deprecated?: boolean
  top_k?: number
}

// ==================== 操作响应接口 ====================

/**
 * 验证经验请求
 */
export interface ExperienceValidateRequest {
  validation_note?: string
  confidence_delta?: number
}

/**
 * 验证经验响应
 */
export interface ExperienceValidateResponse {
  experience_id: number
  new_confidence: number
  validation_count: number
}

/**
 * 废弃经验请求
 */
export interface ExperienceDeprecateRequest {
  reason: string
}

/**
 * 废弃经验响应
 */
export interface ExperienceDeprecateResponse {
  experience_id: number
  status: string
}

/**
 * 关联经验请求
 */
export interface ExperienceLinkRequest {
  entity_type: EntityType
  entity_id: string
  relation?: string
}

/**
 * 关联经验响应
 */
export interface ExperienceLinkResponse {
  link_id: number
  experience_id: number
  entity_type: string
  entity_id: string
}

/**
 * 经验关联记录
 */
export interface ExperienceLink {
  id: number
  experience_id: number
  experience_uuid: string
  entity_type: string
  entity_id: string
  relation: string
  created_at?: string
}

/**
 * 提炼经验请求
 */
export interface ExperienceCurateRequest {
  source_experience_ids: number[]
  target_level: ExperienceLevel
  title: string
  content: ExperienceContent
  context?: ExperienceContext
}

/**
 * 提炼经验响应
 */
export interface ExperienceCurateResponse {
  experience_id: number
  message: string
}

// ==================== 统计接口 ====================

/**
 * 经验统计信息
 */
export interface ExperienceStats {
  total: number
  by_status: Record<string, number>
  by_level: Record<string, number>
  categories: string[]
  categories_count: number
}

// ==================== 常量配置 ====================

/**
 * 默认创建内容
 */
export const DEFAULT_EXPERIENCE_CONTENT: ExperienceContent = {
  problem: '',
  approach: '',
  result: '',
  lesson: '',
}

/**
 * 默认创建上下文
 */
export const DEFAULT_EXPERIENCE_CONTEXT: ExperienceContext = {
  market_regime: '',
  factor_styles: [],
  time_horizon: '',
  asset_class: '',
  tags: [],
}

/**
 * 市场状态选项
 */
export const MARKET_REGIME_OPTIONS = [
  { value: '', label: '全部' },
  { value: '牛市', label: '牛市' },
  { value: '熊市', label: '熊市' },
  { value: '震荡', label: '震荡' },
]

/**
 * 时间范围选项
 */
export const TIME_HORIZON_OPTIONS = [
  { value: '', label: '全部' },
  { value: '短期', label: '短期' },
  { value: '中期', label: '中期' },
  { value: '长期', label: '长期' },
]

/**
 * 资产类别选项
 */
export const ASSET_CLASS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'BTC', label: 'BTC' },
  { value: 'ETH', label: 'ETH' },
  { value: '山寨币', label: '山寨币' },
  { value: '全市场', label: '全市场' },
]
