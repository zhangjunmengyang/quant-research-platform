/**
 * FilterToolbar Component
 * Design System: Unified filter toolbar for list pages
 *
 * Usage:
 * - Use for page-level filter controls
 * - Includes search input, filter selects, and action buttons
 * - Responsive layout with wrap support
 */

import { RotateCcw, RefreshCw } from 'lucide-react'
import { SearchInput } from './search-input'
import { cn } from '@/lib/utils'

interface FilterToolbarProps {
  /** Search input value */
  searchValue?: string
  /** Search input change handler */
  onSearchChange?: (value: string) => void
  /** Search submit handler (Enter key or button click) */
  onSearch?: () => void
  /** Search placeholder text */
  searchPlaceholder?: string
  /** Show refresh button */
  showRefresh?: boolean
  /** Refresh handler */
  onRefresh?: () => void
  /** Show reset button when hasActiveFilters is true */
  hasActiveFilters?: boolean
  /** Reset handler */
  onReset?: () => void
  /** Filter controls (FilterSelect components) */
  children?: React.ReactNode
  /** Additional class name */
  className?: string
}

export function FilterToolbar({
  searchValue,
  onSearchChange,
  onSearch,
  searchPlaceholder = '搜索...',
  showRefresh = false,
  onRefresh,
  hasActiveFilters = false,
  onReset,
  children,
  className,
}: FilterToolbarProps) {
  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-3 rounded-lg border bg-card p-4',
        className
      )}
    >
      {/* Search Input */}
      {onSearchChange && (
        <div className="flex items-center gap-2">
          <SearchInput
            value={searchValue ?? ''}
            onChange={onSearchChange}
            onSearch={onSearch}
            placeholder={searchPlaceholder}
          />
          {onSearch && (
            <button
              onClick={onSearch}
              className="rounded-md bg-secondary px-3 py-2 text-sm hover:bg-secondary/80"
            >
              搜索
            </button>
          )}
        </div>
      )}

      {/* Filter Controls */}
      {children}

      {/* Action Buttons */}
      <div className="flex items-center gap-2 ml-auto">
        {showRefresh && onRefresh && (
          <button
            onClick={onRefresh}
            className="rounded-md border border-input bg-background p-2 hover:bg-accent"
            title="刷新"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        )}
        {hasActiveFilters && onReset && (
          <button
            onClick={onReset}
            className="flex items-center gap-1 rounded-md border border-input bg-background px-3 py-2 text-sm font-medium hover:bg-accent"
          >
            <RotateCcw className="h-4 w-4" />
            重置
          </button>
        )}
      </div>
    </div>
  )
}
