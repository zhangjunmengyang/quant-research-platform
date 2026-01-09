/**
 * FilterSelect Component
 * Design System: Unified filter select for dropdown-style filtering
 *
 * Usage:
 * - Use for single-select filter options (status, type, category, tags)
 * - Wraps SearchableSelect with filter-specific defaults
 * - Use size="sm" for compact filter bars
 */

import { SearchableSelect, type SelectOption } from './SearchableSelect'
import { cn } from '@/lib/utils'

export type { SelectOption }

export interface FilterSelectProps {
  /** Filter options */
  options: SelectOption[]
  /** Current selected value */
  value: string | undefined
  /** Change handler */
  onChange: (value: string | undefined) => void
  /** Placeholder text when nothing selected */
  placeholder?: string
  /** Optional label displayed before select */
  label?: string
  /** Size variant */
  size?: 'default' | 'sm'
  /** Additional class name */
  className?: string
  /** Disable the select */
  disabled?: boolean
}

export function FilterSelect({
  options,
  value,
  onChange,
  placeholder = '全部',
  label,
  size = 'sm',
  className,
  disabled,
}: FilterSelectProps) {
  const handleChange = (newValue: string) => {
    onChange(newValue === '' ? undefined : newValue)
  }

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {label && (
        <span className="text-sm text-muted-foreground whitespace-nowrap">{label}</span>
      )}
      <SearchableSelect
        options={options}
        value={value ?? ''}
        onChange={handleChange}
        placeholder={placeholder}
        size={size}
        disabled={disabled}
        className="min-w-[120px]"
      />
    </div>
  )
}
