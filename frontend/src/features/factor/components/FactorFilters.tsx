/**
 * Factor List Filters Component
 *
 * 因子列表过滤器组件 - 使用统一的 FilterToolbar 和 FilterSelect
 */

import { useMemo } from 'react'
import { useFactorStyles } from '../'
import type { FactorListParams } from '../types'
import { FilterToolbar } from '@/components/ui/filter-toolbar'
import { FilterSelect, type SelectOption } from '@/components/ui/filter-select'
import { FACTOR_TYPE_LABELS, type FactorType, type ExcludedFilter } from '../types'

// 因子类型选项
const FACTOR_TYPE_OPTIONS: SelectOption[] = [
  { value: '', label: '全部类型' },
  { value: 'time_series', label: FACTOR_TYPE_LABELS.time_series },
  { value: 'cross_section', label: FACTOR_TYPE_LABELS.cross_section },
]

// 验证状态选项
const VERIFIED_OPTIONS: SelectOption[] = [
  { value: '', label: '全部状态' },
  { value: 'true', label: '已校验' },
  { value: 'false', label: '未审查' },
]

// 排除状态选项
const EXCLUDED_OPTIONS: SelectOption[] = [
  { value: 'active', label: '有效因子' },
  { value: 'excluded', label: '已排除' },
  { value: 'all', label: '全部' },
]

// 排序选项
const ORDER_BY_OPTIONS: SelectOption[] = [
  { value: 'filename', label: '按名称' },
  { value: 'factor_type', label: '按类型' },
  { value: 'style', label: '按风格' },
  { value: 'llm_score', label: '按评分' },
  { value: 'created_at', label: '按创建时间' },
  { value: 'updated_at', label: '按更新时间' },
]

interface FactorFiltersProps {
  filters: Partial<FactorListParams>
  setFilters: (filters: Partial<FactorListParams>) => void
  resetFilters: () => void
  onSearch?: (query: string) => void
  searchValue?: string
}

export function FactorFilters({ filters, setFilters, resetFilters, onSearch, searchValue = '' }: FactorFiltersProps) {
  const { data: styles = [] } = useFactorStyles()

  // 风格选项
  const styleOptions: SelectOption[] = useMemo(
    () => [
      { value: '', label: '全部风格' },
      ...styles.map((style) => ({ value: style, label: style })),
    ],
    [styles]
  )

  // 检查是否有活跃筛选
  const hasActiveFilters = !!(
    searchValue ||
    filters.factor_type ||
    filters.style ||
    filters.verified !== undefined ||
    (filters.excluded && filters.excluded !== 'active')
  )

  return (
    <FilterToolbar
      searchValue={searchValue}
      onSearchChange={onSearch}
      searchPlaceholder="搜索名称、标签、公式..."
      hasActiveFilters={hasActiveFilters}
      onReset={resetFilters}
    >
      <FilterSelect
        label="类型"
        options={FACTOR_TYPE_OPTIONS}
        value={filters.factor_type}
        onChange={(value) =>
          setFilters({
            factor_type: (value as FactorType) || undefined,
            page: 1,
          })
        }
      />
      <FilterSelect
        label="风格"
        options={styleOptions}
        value={filters.style}
        onChange={(value) => setFilters({ style: value || undefined, page: 1 })}
      />
      <FilterSelect
        label="校验"
        options={VERIFIED_OPTIONS}
        value={filters.verified === undefined ? undefined : String(filters.verified)}
        onChange={(value) =>
          setFilters({
            verified: value === undefined ? undefined : value === 'true',
            page: 1,
          })
        }
      />
      <FilterSelect
        label="状态"
        options={EXCLUDED_OPTIONS}
        value={filters.excluded || 'active'}
        onChange={(value) =>
          setFilters({
            excluded: (value as ExcludedFilter) || 'active',
            page: 1,
          })
        }
      />
      <FilterSelect
        label="排序"
        options={ORDER_BY_OPTIONS}
        value={filters.order_by || 'filename'}
        onChange={(value) => setFilters({ order_by: value, page: 1 })}
      />
    </FilterToolbar>
  )
}
