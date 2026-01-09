/**
 * SearchInput Component
 * Design System: Unified search input with icon
 *
 * Usage:
 * - Standalone search input with search icon
 * - Consistent styling across all pages
 */

import { Search } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SearchInputProps {
  /** Current value */
  value: string
  /** Change handler */
  onChange: (value: string) => void
  /** Enter key handler */
  onSearch?: () => void
  /** Placeholder text */
  placeholder?: string
  /** Additional class name for wrapper */
  className?: string
}

export function SearchInput({
  value,
  onChange,
  onSearch,
  placeholder = '搜索...',
  className,
}: SearchInputProps) {
  return (
    <div className={cn('relative flex-1 min-w-[200px] max-w-md', className)}>
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && onSearch?.()}
        className="w-full rounded-md border border-input bg-background py-2 pl-10 pr-4 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />
    </div>
  )
}
