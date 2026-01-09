/**
 * Note module type definitions
 * Mirrors backend Pydantic models for type safety
 */

/**
 * 笔记类型枚举
 */
export enum NoteType {
  OBSERVATION = 'observation', // 观察 - 对数据或现象的客观记录
  HYPOTHESIS = 'hypothesis',   // 假设 - 基于观察提出的假设
  FINDING = 'finding',         // 发现 - 验证后的发现
  TRAIL = 'trail',             // 轨迹 - 研究过程记录（自动生成）
  GENERAL = 'general',         // 通用 - 一般性笔记（向后兼容）
}

/**
 * 笔记类型显示名称
 */
export const NOTE_TYPE_LABELS: Record<NoteType, string> = {
  [NoteType.OBSERVATION]: '观察',
  [NoteType.HYPOTHESIS]: '假设',
  [NoteType.FINDING]: '发现',
  [NoteType.TRAIL]: '轨迹',
  [NoteType.GENERAL]: '通用',
}

/**
 * 笔记类型颜色配置
 */
export const NOTE_TYPE_COLORS: Record<NoteType, { bg: string; text: string; border: string }> = {
  [NoteType.OBSERVATION]: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  [NoteType.HYPOTHESIS]: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  [NoteType.FINDING]: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' },
  [NoteType.TRAIL]: { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200' },
  [NoteType.GENERAL]: { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' },
}

export interface Note {
  id: number
  title: string
  content: string
  tags: string
  source: string
  source_ref: string
  note_type: NoteType
  research_session_id?: string | null
  promoted_to_experience_id?: number | null
  is_archived: boolean
  created_at?: string
  updated_at?: string
}

export interface NoteCreate {
  title: string
  content: string
  tags?: string
  source?: string
  source_ref?: string
  note_type?: NoteType
  research_session_id?: string
}

export interface NoteUpdate {
  title?: string
  content?: string
  tags?: string
  source?: string
  source_ref?: string
  note_type?: NoteType
  research_session_id?: string
}

export interface NoteListParams {
  page?: number
  page_size?: number
  search?: string
  tags?: string
  source?: string
  note_type?: NoteType
  is_archived?: boolean
  order_by?: string
  order_desc?: boolean
}

export interface NoteStats {
  total: number
  tags_count: number
  tags: string[]
  active_count: number
  archived_count: number
  promoted_count: number
  session_count: number
  by_type: Record<string, number>
}

/**
 * 记录观察请求
 */
export interface ObservationCreate {
  title: string
  content: string
  tags?: string
  source?: string
  source_ref?: string
  research_session_id?: string
}

/**
 * 记录假设请求
 */
export interface HypothesisCreate {
  title: string
  content: string
  tags?: string
  source?: string
  source_ref?: string
  research_session_id?: string
}

/**
 * 记录发现请求
 */
export interface FindingCreate {
  title: string
  content: string
  tags?: string
  source?: string
  source_ref?: string
  research_session_id?: string
}

/**
 * 提炼为经验请求
 */
export interface PromoteRequest {
  experience_id: number
}

/**
 * 研究轨迹响应
 */
export interface ResearchTrail {
  session_id: string
  notes: Note[]
  total: number
  by_type: Record<string, number>
}

// Source type labels
export const SOURCE_LABELS: Record<string, string> = {
  factor: '因子',
  strategy: '策略',
  backtest: '回测',
  manual: '手动',
}
