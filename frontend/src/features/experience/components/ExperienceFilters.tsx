/**
 * Experience Filters Component
 *
 * 经验列表过滤器组件 - 使用统一的 FilterToolbar 和 FilterSelect
 * 通过 props 接收筛选状态，支持多种状态管理方式（URL params 或 store）
 */

import { useMemo } from 'react'
import { FilterToolbar } from '@/components/ui/filter-toolbar'
import { FilterSelect, type SelectOption } from '@/components/ui/filter-select'
import { useExperienceStats } from '../'
import {
  EXPERIENCE_LEVEL_LABELS,
  EXPERIENCE_STATUS_LABELS,
  SOURCE_TYPE_LABELS,
  MARKET_REGIME_OPTIONS,
  type ExperienceLevel,
  type ExperienceStatus,
  type SourceType,
} from '../types'
import type { ExperienceListParams } from '../types'

// 层级选项
const LEVEL_OPTIONS: SelectOption[] = [
  { value: '', label: '全部层级' },
  { value: 'strategic', label: EXPERIENCE_LEVEL_LABELS.strategic },
  { value: 'tactical', label: EXPERIENCE_LEVEL_LABELS.tactical },
  { value: 'operational', label: EXPERIENCE_LEVEL_LABELS.operational },
]

// 状态选项
const STATUS_OPTIONS: SelectOption[] = [
  { value: '', label: '全部状态' },
  { value: 'draft', label: EXPERIENCE_STATUS_LABELS.draft },
  { value: 'validated', label: EXPERIENCE_STATUS_LABELS.validated },
  { value: 'deprecated', label: EXPERIENCE_STATUS_LABELS.deprecated },
]

// 来源选项
const SOURCE_TYPE_OPTIONS: SelectOption[] = [
  { value: '', label: '全部来源' },
  { value: 'research', label: SOURCE_TYPE_LABELS.research },
  { value: 'backtest', label: SOURCE_TYPE_LABELS.backtest },
  { value: 'live_trade', label: SOURCE_TYPE_LABELS.live_trade },
  { value: 'external', label: SOURCE_TYPE_LABELS.external },
  { value: 'manual', label: SOURCE_TYPE_LABELS.manual },
  { value: 'curated', label: SOURCE_TYPE_LABELS.curated },
]

// 排序选项
const ORDER_BY_OPTIONS: SelectOption[] = [
  { value: 'updated_at', label: '按更新时间' },
  { value: 'created_at', label: '按创建时间' },
  { value: 'confidence', label: '按置信度' },
  { value: 'validation_count', label: '按验证次数' },
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
  const { data: stats } = useExperienceStats()

  // 分类选项（从统计数据获取）
  const categoryOptions: SelectOption[] = useMemo(
    () => [
      { value: '', label: '全部分类' },
      ...(stats?.categories?.map((cat) => ({ value: cat, label: cat })) ?? []),
    ],
    [stats?.categories]
  )

  // 检查是否有活跃筛选（如果外部传入则使用外部值）
  const hasActiveFilters =
    hasActiveFiltersProp ??
    !!(
      searchValue ||
      filters.experience_level ||
      filters.status ||
      filters.category ||
      filters.source_type ||
      filters.market_regime
    )

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
        label="层级"
        options={LEVEL_OPTIONS}
        value={filters.experience_level}
        onChange={(value) =>
          setFilters({
            experience_level: (value as ExperienceLevel) || undefined,
            page: 1,
          })
        }
      />
      <FilterSelect
        label="状态"
        options={STATUS_OPTIONS}
        value={filters.status}
        onChange={(value) =>
          setFilters({
            status: (value as ExperienceStatus) || undefined,
            page: 1,
          })
        }
      />
      <FilterSelect
        label="分类"
        options={categoryOptions}
        value={filters.category}
        onChange={(value) => setFilters({ category: value || undefined, page: 1 })}
      />
      <FilterSelect
        label="来源"
        options={SOURCE_TYPE_OPTIONS}
        value={filters.source_type}
        onChange={(value) =>
          setFilters({
            source_type: (value as SourceType) || undefined,
            page: 1,
          })
        }
      />
      <FilterSelect
        label="市场"
        options={MARKET_REGIME_OPTIONS}
        value={filters.market_regime}
        onChange={(value) => setFilters({ market_regime: value || undefined, page: 1 })}
      />
      <FilterSelect
        label="排序"
        options={ORDER_BY_OPTIONS}
        value={filters.order_by || 'updated_at'}
        onChange={(value) => setFilters({ order_by: value, page: 1 })}
      />
    </FilterToolbar>
  )
}
