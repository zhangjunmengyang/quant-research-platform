/**
 * Experience Filters Component
 *
 * 经验列表过滤器组件
 */

import { useMemo } from 'react'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'
import { Search, RotateCcw } from 'lucide-react'
import { useExperienceStore, useExperienceStats } from '../'
import {
  EXPERIENCE_LEVEL_LABELS,
  EXPERIENCE_STATUS_LABELS,
  SOURCE_TYPE_LABELS,
  MARKET_REGIME_OPTIONS,
  type ExperienceLevel,
  type ExperienceStatus,
  type SourceType,
} from '../types'

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
  onSearch?: (query: string) => void
  searchValue?: string
}

export function ExperienceFilters({ onSearch, searchValue = '' }: ExperienceFiltersProps) {
  const { data: stats } = useExperienceStats()
  const { filters, setFilters, resetFilters } = useExperienceStore()

  // 分类选项（从统计数据获取）
  const categoryOptions: SelectOption[] = useMemo(
    () => [
      { value: '', label: '全部分类' },
      ...(stats?.categories?.map((cat) => ({ value: cat, label: cat })) ?? []),
    ],
    [stats?.categories]
  )

  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border bg-card p-4">
      {/* 搜索框 */}
      <div className="flex-1 min-w-[200px] max-w-md">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="搜索经验..."
            defaultValue={searchValue}
            className="w-full rounded-md border border-input bg-background px-3 py-2 pl-10 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onChange={(e) => onSearch?.(e.target.value)}
          />
        </div>
      </div>

      {/* 层级筛选 */}
      <div className="min-w-[120px]">
        <SearchableSelect
          options={LEVEL_OPTIONS}
          value={filters.experience_level || ''}
          onChange={(value) =>
            setFilters({
              experience_level: (value as ExperienceLevel) || undefined,
              page: 1,
            })
          }
        />
      </div>

      {/* 状态筛选 */}
      <div className="min-w-[120px]">
        <SearchableSelect
          options={STATUS_OPTIONS}
          value={filters.status || ''}
          onChange={(value) =>
            setFilters({
              status: (value as ExperienceStatus) || undefined,
              page: 1,
            })
          }
        />
      </div>

      {/* 分类筛选 */}
      <div className="min-w-[150px]">
        <SearchableSelect
          options={categoryOptions}
          value={filters.category || ''}
          onChange={(value) => setFilters({ category: value || undefined, page: 1 })}
          searchPlaceholder="搜索分类..."
        />
      </div>

      {/* 来源筛选 */}
      <div className="min-w-[120px]">
        <SearchableSelect
          options={SOURCE_TYPE_OPTIONS}
          value={filters.source_type || ''}
          onChange={(value) =>
            setFilters({
              source_type: (value as SourceType) || undefined,
              page: 1,
            })
          }
        />
      </div>

      {/* 市场环境筛选 */}
      <div className="min-w-[100px]">
        <SearchableSelect
          options={MARKET_REGIME_OPTIONS}
          value={filters.market_regime || ''}
          onChange={(value) => setFilters({ market_regime: value || undefined, page: 1 })}
        />
      </div>

      {/* 排序 */}
      <div className="min-w-[140px]">
        <SearchableSelect
          options={ORDER_BY_OPTIONS}
          value={filters.order_by || 'updated_at'}
          onChange={(value) => setFilters({ order_by: value, page: 1 })}
        />
      </div>

      {/* 重置按钮 */}
      <button
        onClick={resetFilters}
        className="flex items-center gap-1 rounded-md border border-input bg-background px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
      >
        <RotateCcw className="h-4 w-4" />
        重置
      </button>
    </div>
  )
}
