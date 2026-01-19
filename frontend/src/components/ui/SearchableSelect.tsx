/**
 * SearchableSelect Component
 * 可搜索的下拉选择框组件
 */

import { useState, useRef, useEffect, useMemo } from 'react'
import { ChevronDown, Search, X, Check } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SelectOption {
  value: string
  label: string
  description?: string
  group?: string
}

interface SearchableSelectProps {
  options: SelectOption[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
  searchPlaceholder?: string
  disabled?: boolean
  className?: string
  emptyText?: string
  /** 是否允许清空选择 */
  clearable?: boolean
  /** 最大显示高度 */
  maxHeight?: number
  /** 尺寸: 默认 'default', 可选 'sm' 紧凑模式 */
  size?: 'default' | 'sm'
}

export function SearchableSelect({
  options,
  value,
  onChange,
  placeholder = '请选择',
  searchPlaceholder = '搜索...',
  disabled = false,
  className,
  emptyText = '无匹配项',
  clearable = false,
  maxHeight = 300,
  size = 'default',
}: SearchableSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // 当前选中的选项
  const selectedOption = useMemo(
    () => options.find((opt) => opt.value === value),
    [options, value]
  )

  // 过滤后的选项
  const filteredOptions = useMemo(() => {
    if (!searchQuery) return options
    const query = searchQuery.toLowerCase()
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(query) ||
        opt.value.toLowerCase().includes(query) ||
        opt.description?.toLowerCase().includes(query)
    )
  }, [options, searchQuery])

  // 按分组组织选项
  const groupedOptions = useMemo(() => {
    const groups: Record<string, SelectOption[]> = {}
    const ungrouped: SelectOption[] = []

    filteredOptions.forEach((opt) => {
      if (opt.group) {
        if (!groups[opt.group]) groups[opt.group] = []
        groups[opt.group]!.push(opt)
      } else {
        ungrouped.push(opt)
      }
    })

    return { groups, ungrouped }
  }, [filteredOptions])

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSearchQuery('')
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 打开时聚焦搜索框
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const handleSelect = (optionValue: string) => {
    onChange(optionValue)
    setIsOpen(false)
    setSearchQuery('')
  }

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange('')
    setSearchQuery('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false)
      setSearchQuery('')
    } else if (e.key === 'Enter' && filteredOptions.length === 1 && filteredOptions[0]) {
      handleSelect(filteredOptions[0].value)
    }
  }

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={cn(
          'flex w-full items-center justify-between rounded-md border border-input bg-background text-sm',
          size === 'sm' ? 'h-8 px-2.5 py-1.5' : 'px-3 py-2',
          'hover:bg-accent hover:text-accent-foreground',
          'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
          'disabled:cursor-not-allowed disabled:opacity-50',
          isOpen && 'ring-2 ring-ring ring-offset-2'
        )}
      >
        <span className={cn('truncate text-left flex-1', !selectedOption && 'text-muted-foreground')}>
          {selectedOption?.label || placeholder}
        </span>
        <div className="flex items-center gap-1 shrink-0 ml-1">
          {clearable && value && (
            <X
              className="h-4 w-4 text-muted-foreground hover:text-foreground"
              onClick={handleClear}
            />
          )}
          <ChevronDown
            className={cn(
              'h-4 w-4 text-muted-foreground transition-transform',
              isOpen && 'rotate-180'
            )}
          />
        </div>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-lg">
          {/* Search Input - 仅当选项数量 >= 20 时显示 */}
          {options.length >= 20 && (
            <div className="border-b p-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  ref={inputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={searchPlaceholder}
                  className="w-full rounded-md border border-input bg-background py-1.5 pl-8 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                />
                {searchQuery && (
                  <X
                    className="absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 cursor-pointer text-muted-foreground hover:text-foreground"
                    onClick={() => setSearchQuery('')}
                  />
                )}
              </div>
            </div>
          )}

          {/* Options List */}
          <div className="overflow-auto" style={{ maxHeight }}>
            {filteredOptions.length === 0 ? (
              <div className="px-3 py-6 text-center text-sm text-muted-foreground">
                {emptyText}
              </div>
            ) : (
              <>
                {/* Ungrouped options */}
                {groupedOptions.ungrouped.map((opt) => (
                  <OptionItem
                    key={opt.value}
                    option={opt}
                    isSelected={opt.value === value}
                    onSelect={handleSelect}
                  />
                ))}

                {/* Grouped options */}
                {Object.entries(groupedOptions.groups).map(([group, opts]) => (
                  <div key={group}>
                    <div className="sticky top-0 bg-muted px-3 py-1.5 text-xs font-medium text-muted-foreground">
                      {group}
                    </div>
                    {opts.map((opt) => (
                      <OptionItem
                        key={opt.value}
                        option={opt}
                        isSelected={opt.value === value}
                        onSelect={handleSelect}
                      />
                    ))}
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

interface OptionItemProps {
  option: SelectOption
  isSelected: boolean
  onSelect: (value: string) => void
}

function OptionItem({ option, isSelected, onSelect }: OptionItemProps) {
  return (
    <div
      onClick={() => onSelect(option.value)}
      className={cn(
        'flex cursor-pointer items-center gap-2 px-3 py-2 text-sm',
        'hover:bg-accent hover:text-accent-foreground',
        isSelected && 'bg-accent/50'
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="truncate">{option.label}</div>
        {option.description && (
          <div className="truncate text-xs text-muted-foreground">{option.description}</div>
        )}
      </div>
      {isSelected && <Check className="h-4 w-4 shrink-0 text-primary" />}
    </div>
  )
}
