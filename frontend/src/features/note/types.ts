/**
 * Note module type definitions
 * Mirrors backend Pydantic models for type safety
 */

export interface Note {
  id: number
  title: string
  content: string
  tags: string
  source: string
  source_ref: string
  created_at?: string
  updated_at?: string
}

export interface NoteCreate {
  title: string
  content: string
  tags?: string
  source?: string
  source_ref?: string
}

export interface NoteUpdate {
  title?: string
  content?: string
  tags?: string
  source?: string
  source_ref?: string
}

export interface NoteListParams {
  page?: number
  page_size?: number
  search?: string
  tags?: string
  source?: string
  order_by?: string
  order_desc?: boolean
}

export interface NoteStats {
  total: number
  tags_count: number
  tags: string[]
}

// Source type labels
export const SOURCE_LABELS: Record<string, string> = {
  factor: '因子',
  strategy: '策略',
  backtest: '回测',
  manual: '手动',
}
