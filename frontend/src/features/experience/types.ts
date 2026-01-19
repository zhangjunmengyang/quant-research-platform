/**
 * Experience module type definitions
 * Mirrors backend Pydantic models for type safety
 *
 * 简化版本: 以标签为核心管理
 */

// ==================== 枚举定义 ====================

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
 * 经验上下文信息（简化为只有标签）
 */
export interface ExperienceContext {
  tags: string[]    // 自定义标签
}

// ==================== 主接口 ====================

/**
 * 经验完整响应
 */
export interface Experience {
  id: number
  uuid: string
  title: string
  content: ExperienceContent
  context: ExperienceContext
  created_at?: string
  updated_at?: string
}

/**
 * 创建经验请求
 */
export interface ExperienceCreate {
  title: string
  content?: ExperienceContent
  context?: ExperienceContext
}

/**
 * 更新经验请求
 */
export interface ExperienceUpdate {
  title?: string
  content?: ExperienceContent
  context?: ExperienceContext
}

// ==================== 查询参数接口 ====================

/**
 * 经验列表查询参数
 */
export interface ExperienceListParams {
  page?: number
  page_size?: number
  tags?: string
  created_after?: string
  created_before?: string
  updated_after?: string
  updated_before?: string
  order_by?: string
  order_desc?: boolean
}

/**
 * 语义查询参数
 */
export interface ExperienceQueryParams {
  query: string
  tags?: string[]
  top_k?: number
}

// ==================== 操作响应接口 ====================

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

// ==================== 统计接口 ====================

/**
 * 经验统计信息
 */
export interface ExperienceStats {
  total: number
  tags: string[]
  tags_count: number
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
