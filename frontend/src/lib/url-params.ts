/**
 * URL Params 相关工具函数
 * 用于处理 search params 与 filters 之间的转换
 */

import type { FactorListParams, ExcludedFilter, FactorType } from '@/features/factor'
import type { StrategyListParams } from '@/features/strategy'
import type { ExperienceListParams } from '@/features/experience'
import { NoteType, type NoteListParams } from '@/features/note'

// =============================================================================
// 类型验证辅助函数
// =============================================================================

/**
 * 验证值是否在允许的选项中
 */
function validateEnum<T extends string>(value: string | null, validValues: readonly T[], defaultValue: T): T {
  if (!value || !validValues.includes(value as T)) {
    return defaultValue
  }
  return value as T
}

// 各业务域的有效枚举值 (必须与 types.ts 中的定义保持一致)
const FACTOR_ORDER_BY_VALUES = ['filename', 'verified', 'created_at'] as const
const FACTOR_EXCLUDED_VALUES: readonly ExcludedFilter[] = ['all', 'active', 'excluded']
const FACTOR_TYPE_VALUES: readonly FactorType[] = ['time_series', 'cross_section']
const STRATEGY_ORDER_BY_VALUES = ['created_at', 'updated_at', 'name'] as const
const NOTE_TYPE_VALUES: readonly NoteType[] = [NoteType.OBSERVATION, NoteType.HYPOTHESIS, NoteType.FINDING, NoteType.TRAIL, NoteType.GENERAL]

// =============================================================================
// Factor 相关
// =============================================================================

// 将 URLSearchParams 转换为 FactorListParams
export function paramsToFactorFilters(searchParams: URLSearchParams): FactorListParams {
  const factorType = searchParams.get('factor_type')
  return {
    page: Number(searchParams.get('page')) || 1,
    page_size: Number(searchParams.get('page_size')) || 50,
    search: searchParams.get('search') || undefined,
    style: searchParams.get('style') || undefined,
    factor_type: factorType ? validateEnum(factorType, FACTOR_TYPE_VALUES, 'time_series') : undefined,
    verified: searchParams.get('verified') === 'true' ? true : searchParams.get('verified') === 'false' ? false : undefined,
    order_by: validateEnum(searchParams.get('order_by'), FACTOR_ORDER_BY_VALUES, 'filename'),
    excluded: searchParams.get('excluded')
      ? validateEnum(searchParams.get('excluded'), FACTOR_EXCLUDED_VALUES, 'active')
      : undefined,
  }
}

// 将 FactorListParams 转换为 URLSearchParams
export function factorFiltersToParams(filters: Partial<FactorListParams>): Record<string, string> {
  const params: Record<string, string> = {}
  if (filters.page) params.page = String(filters.page)
  if (filters.page_size) params.page_size = String(filters.page_size)
  if (filters.search) params.search = filters.search
  if (filters.style) params.style = filters.style
  if (filters.factor_type) params.factor_type = filters.factor_type
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
    order_by: validateEnum(searchParams.get('order_by'), STRATEGY_ORDER_BY_VALUES, 'created_at'),
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
    tags: searchParams.get('tags') || undefined,
    order_by: searchParams.get('order_by') || 'updated_at',
    order_desc: searchParams.get('order_desc') !== 'false',
  }
}

// 将 ExperienceListParams 转换为 URLSearchParams
export function experienceFiltersToParams(filters: Partial<ExperienceListParams>): Record<string, string> {
  const params: Record<string, string> = {}
  if (filters.page) params.page = String(filters.page)
  if (filters.page_size) params.page_size = String(filters.page_size)
  if (filters.tags) params.tags = filters.tags
  if (filters.order_by) params.order_by = filters.order_by
  if (filters.order_desc !== undefined) params.order_desc = String(filters.order_desc)
  return params
}

// =============================================================================
// Note 相关
// =============================================================================

// 将 URLSearchParams 转换为 NoteListParams
export function paramsToNoteFilters(searchParams: URLSearchParams): NoteListParams {
  const noteType = searchParams.get('note_type')

  return {
    page: Number(searchParams.get('page')) || 1,
    page_size: Number(searchParams.get('page_size')) || 20,
    search: searchParams.get('search') || undefined,
    tags: searchParams.get('tags') || undefined,
    source: searchParams.get('source') || undefined,
    note_type: noteType
      ? validateEnum(noteType, NOTE_TYPE_VALUES, NoteType.GENERAL)
      : undefined,
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
