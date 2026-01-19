/**
 * Experience Filters Component
 *
 * 经验列表过滤器组件 - 简化版本
 * 只保留搜索和排序功能
 */

import { FilterToolbar } from '@/components/ui/filter-toolbar'
import { FilterSelect, type SelectOption } from '@/components/ui/filter-select'
import type { ExperienceListParams } from '../types'

// 排序选项
const ORDER_BY_OPTIONS: SelectOption[] = [
  { value: 'updated_at', label: '按更新时间' },
  { value: 'created_at', label: '按创建时间' },
  { value: 'title', label: '按标题' },
]

interface ExperienceFiltersProps {
  filters: Partial<ExperienceListParams>
  setFilters: (filters: Partial<ExperienceListParams>) => void
  resetFilters: () => void
  onSearch?: (query: string) => void
  searchValue?: string
  onSearchInputChange?: (value: string) => void
  searchInputValue?: string
  hasActiveFilters?: boolean
}

export function ExperienceFilters({
  filters,
  setFilters,
  resetFilters,
  onSearch,
  searchValue = '',
  onSearchInputChange,
  searchInputValue,
  hasActiveFilters: hasActiveFiltersProp,
}: ExperienceFiltersProps) {
  // 检查是否有活跃筛选
  const hasActiveFilters = hasActiveFiltersProp ?? !!searchValue

  // 同步搜索框输入和搜索值
  const handleSearchChange = onSearchInputChange
    ? (value: string) => {
        onSearchInputChange(value)
        if (value === '') {
          onSearch?.('')
        }
      }
    : undefined

  const handleSearchSubmit = onSearch ? () => onSearch(searchInputValue ?? searchValue) : undefined

  return (
    <FilterToolbar
      searchValue={searchInputValue ?? searchValue}
      onSearchChange={handleSearchChange}
      onSearch={handleSearchSubmit}
      searchPlaceholder="搜索经验..."
      hasActiveFilters={hasActiveFilters}
      onReset={resetFilters}
    >
      <FilterSelect
        label="排序"
        options={ORDER_BY_OPTIONS}
        value={filters.order_by || 'updated_at'}
        onChange={(value) => setFilters({ order_by: value, page: 1 })}
      />
    </FilterToolbar>
  )
}
