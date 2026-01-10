/**
 * URL Params 相关工具函数
 * 用于处理 search params 与 filters 之间的转换
 */

import type { FactorListParams } from '@/features/factor'
import type { StrategyListParams } from '@/features/strategy'
import type { ExperienceListParams } from '@/features/experience'
import type { NoteListParams } from '@/features/note'

// =============================================================================
// Factor 相关
// =============================================================================

// 将 URLSearchParams 转换为 FactorListParams
export function paramsToFactorFilters(searchParams: URLSearchParams): FactorListParams {
  return {
    page: Number(searchParams.get('page')) || 1,
    page_size: Number(searchParams.get('page_size')) || 50,
    search: searchParams.get('search') || undefined,
    style: searchParams.get('style') || undefined,
    verified: searchParams.get('verified') === 'true' ? true : searchParams.get('verified') === 'false' ? false : undefined,
    order_by: (searchParams.get('order_by') as FactorListParams['order_by']) || 'filename',
    excluded: (searchParams.get('excluded') as FactorListParams['excluded']) || undefined,
  }
}

// 将 FactorListParams 转换为 URLSearchParams
export function factorFiltersToParams(filters: Partial<FactorListParams>): Record<string, string> {
  const params: Record<string, string> = {}
  if (filters.page) params.page = String(filters.page)
  if (filters.page_size) params.page_size = String(filters.page_size)
  if (filters.search) params.search = filters.search
  if (filters.style) params.style = filters.style
  if (filters.verified !== undefined) params.verified = String(filters.verified)
  if (filters.order_by) params.order_by = filters.order_by
  if (filters.excluded) params.excluded = filters.excluded
  return params
}

// 将 URLSearchParams 转换为 StrategyListParams
export function paramsToStrategyFilters(searchParams: URLSearchParams): StrategyListParams {
  return {
    page: Number(searchParams.get('page')) || 1,
    page_size: Number(searchParams.get('page_size')) || 50,
    order_by: (searchParams.get('order_by') as StrategyListParams['order_by']) || 'created_at',
    verified: searchParams.get('verified') === 'true' ? true : searchParams.get('verified') === 'false' ? false : undefined,
  }
}

// 将 StrategyListParams 转换为 URLSearchParams
export function strategyFiltersToParams(filters: Partial<StrategyListParams>): Record<string, string> {
  const params: Record<string, string> = {}
  if (filters.page) params.page = String(filters.page)
  if (filters.page_size) params.page_size = String(filters.page_size)
  if (filters.order_by) params.order_by = filters.order_by
  if (filters.verified !== undefined) params.verified = String(filters.verified)
  return params
}

// =============================================================================
// Experience 相关
// =============================================================================

// 将 URLSearchParams 转换为 ExperienceListParams
export function paramsToExperienceFilters(searchParams: URLSearchParams): ExperienceListParams {
  return {
    page: Number(searchParams.get('page')) || 1,
    page_size: Number(searchParams.get('page_size')) || 20,
    experience_level: (searchParams.get('experience_level') as ExperienceListParams['experience_level']) || undefined,
    category: searchParams.get('category') || undefined,
    status: (searchParams.get('status') as ExperienceListParams['status']) || undefined,
    source_type: (searchParams.get('source_type') as ExperienceListParams['source_type']) || undefined,
    market_regime: searchParams.get('market_regime') || undefined,
    min_confidence: searchParams.get('min_confidence') ? Number(searchParams.get('min_confidence')) : undefined,
    include_deprecated: searchParams.get('include_deprecated') === 'true' ? true : undefined,
    order_by: searchParams.get('order_by') || 'updated_at',
    order_desc: searchParams.get('order_desc') !== 'false',
  }
}

// 将 ExperienceListParams 转换为 URLSearchParams
export function experienceFiltersToParams(filters: Partial<ExperienceListParams>): Record<string, string> {
  const params: Record<string, string> = {}
  if (filters.page) params.page = String(filters.page)
  if (filters.page_size) params.page_size = String(filters.page_size)
  if (filters.experience_level) params.experience_level = filters.experience_level
  if (filters.category) params.category = filters.category
  if (filters.status) params.status = filters.status
  if (filters.source_type) params.source_type = filters.source_type
  if (filters.market_regime) params.market_regime = filters.market_regime
  if (filters.min_confidence) params.min_confidence = String(filters.min_confidence)
  if (filters.include_deprecated) params.include_deprecated = String(filters.include_deprecated)
  if (filters.order_by) params.order_by = filters.order_by
  if (filters.order_desc !== undefined) params.order_desc = String(filters.order_desc)
  return params
}

// =============================================================================
// Note 相关
// =============================================================================

// 将 URLSearchParams 转换为 NoteListParams
export function paramsToNoteFilters(searchParams: URLSearchParams): NoteListParams {
  return {
    page: Number(searchParams.get('page')) || 1,
    page_size: Number(searchParams.get('page_size')) || 20,
    search: searchParams.get('search') || undefined,
    tags: searchParams.get('tags') || undefined,
    source: searchParams.get('source') || undefined,
    note_type: (searchParams.get('note_type') as NoteListParams['note_type']) || undefined,
    is_archived: searchParams.get('is_archived') === 'true' ? true : searchParams.get('is_archived') === 'false' ? false : false,
    order_by: searchParams.get('order_by') || 'updated_at',
    order_desc: searchParams.get('order_desc') !== 'false',
  }
}

// 将 NoteListParams 转换为 URLSearchParams
export function noteFiltersToParams(filters: Partial<NoteListParams>): Record<string, string> {
  const params: Record<string, string> = {}
  if (filters.page) params.page = String(filters.page)
  if (filters.page_size) params.page_size = String(filters.page_size)
  if (filters.search) params.search = filters.search
  if (filters.tags) params.tags = filters.tags
  if (filters.source) params.source = filters.source
  if (filters.note_type) params.note_type = filters.note_type
  if (filters.is_archived !== undefined) params.is_archived = String(filters.is_archived)
  if (filters.order_by) params.order_by = filters.order_by
  if (filters.order_desc !== undefined) params.order_desc = String(filters.order_desc)
  return params
}
