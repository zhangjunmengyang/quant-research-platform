/**
 * Factor List Filters Component
 */

import { useMemo } from 'react'
import { useFactorStyles, useFactorStore } from '../'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'
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
  onSearch?: (query: string) => void
}

export function FactorFilters({ onSearch }: FactorFiltersProps) {
  const { data: styles = [] } = useFactorStyles()
  const { filters, setFilters, resetFilters } = useFactorStore()

  // 风格选项
  const styleOptions: SelectOption[] = useMemo(
    () => [
      { value: '', label: '全部风格' },
      ...styles.map((style) => ({ value: style, label: style })),
    ],
    [styles]
  )

  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border bg-card p-4">
      {/* Search */}
      <div className="flex-1 min-w-[200px]">
        <input
          type="text"
          placeholder="搜索因子名称..."
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onChange={(e) => onSearch?.(e.target.value)}
        />
      </div>

      {/* Factor Type Filter */}
      <div className="min-w-[100px]">
        <SearchableSelect
          options={FACTOR_TYPE_OPTIONS}
          value={filters.factor_type || ''}
          onChange={(value) =>
            setFilters({
              factor_type: (value as FactorType) || undefined,
              page: 1,
            })
          }
        />
      </div>

      {/* Style Filter */}
      <div className="min-w-[150px]">
        <SearchableSelect
          options={styleOptions}
          value={filters.style || ''}
          onChange={(value) => setFilters({ style: value || undefined, page: 1 })}
          searchPlaceholder="搜索风格..."
        />
      </div>

      {/* Verified Filter */}
      <div className="min-w-[120px]">
        <SearchableSelect
          options={VERIFIED_OPTIONS}
          value={filters.verified === undefined ? '' : String(filters.verified)}
          onChange={(value) =>
            setFilters({
              verified: value === '' ? undefined : value === 'true',
              page: 1,
            })
          }
        />
      </div>

      {/* Excluded Filter */}
      <div className="min-w-[100px]">
        <SearchableSelect
          options={EXCLUDED_OPTIONS}
          value={filters.excluded || 'active'}
          onChange={(value) =>
            setFilters({
              excluded: (value as ExcludedFilter) || 'active',
              page: 1,
            })
          }
        />
      </div>

      {/* Order By */}
      <div className="min-w-[140px]">
        <SearchableSelect
          options={ORDER_BY_OPTIONS}
          value={filters.order_by || 'filename'}
          onChange={(value) => setFilters({ order_by: value, page: 1 })}
        />
      </div>

      {/* Reset Button */}
      <button
        onClick={resetFilters}
        className="rounded-md border border-input bg-background px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
      >
        重置
      </button>
    </div>
  )
}
