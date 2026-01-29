/**
 * Note module type definitions
 * Mirrors backend Pydantic models for type safety
 */

/**
 * 笔记类型枚举
 *
 * 研究流程：观察 -> 假设 -> 检验
 */
export enum NoteType {
  OBSERVATION = 'observation',   // 观察 - 对数据或现象的客观记录
  HYPOTHESIS = 'hypothesis',     // 假设 - 基于观察提出的待验证假说
  VERIFICATION = 'verification', // 检验 - 对假设的验证过程和结论
}

/**
 * 笔记类型显示名称
 */
export const NOTE_TYPE_LABELS: Record<NoteType, string> = {
  [NoteType.OBSERVATION]: '观察',
  [NoteType.HYPOTHESIS]: '假设',
  [NoteType.VERIFICATION]: '检验',
}

/**
 * 笔记类型颜色配置
 */
export const NOTE_TYPE_COLORS: Record<NoteType, { bg: string; text: string; border: string }> = {
  [NoteType.OBSERVATION]: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  [NoteType.HYPOTHESIS]: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  [NoteType.VERIFICATION]: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' },
}

export interface Note {
  id: number
  title: string
  content: string
  tags: string
  note_type: NoteType
  promoted_to_experience_id?: number | null
  is_archived: boolean
  created_at?: string
  updated_at?: string
}

export interface NoteCreate {
  title: string
  content: string
  tags?: string
  note_type?: NoteType
}

export interface NoteUpdate {
  title?: string
  content?: string
  tags?: string
  note_type?: NoteType
}

export interface NoteListParams {
  page?: number
  page_size?: number
  search?: string
  tags?: string
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
  by_type: Record<string, number>
}

/**
 * 记录观察请求
 */
export interface ObservationCreate {
  title: string
  content: string
  tags?: string
}

/**
 * 记录假设请求
 */
export interface HypothesisCreate {
  title: string
  content: string
  tags?: string
}

/**
 * 记录检验请求
 */
export interface VerificationCreate {
  title: string
  content: string
  tags?: string
  hypothesis_id?: number  // 通过 Edge 系统关联假设
}

/**
 * 提炼为经验请求
 */
export interface PromoteRequest {
  experience_id: number
}

/**
 * 研究轨迹
 */
export interface ResearchTrail {
  session_id: string
  notes: Note[]
  created_at: string
}
