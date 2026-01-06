/**
 * ColumnSelector - 列选择器组件，支持多选显示/隐藏列
 */

import { useState, useRef, useEffect } from 'react'
import { Check, ChevronDown, Columns3 } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ColumnOption {
  key: string
  label: string
  required?: boolean // 是否必选（不能隐藏）
}

interface ColumnSelectorProps {
  columns: ColumnOption[]
  visibleColumns: string[]
  onChange: (visibleColumns: string[]) => void
  className?: string
}

export function ColumnSelector({
  columns,
  visibleColumns,
  onChange,
  className,
}: ColumnSelectorProps) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }

    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open])

  const handleToggle = (key: string) => {
    const column = columns.find((c) => c.key === key)
    if (column?.required) return // 必选列不能取消

    if (visibleColumns.includes(key)) {
      onChange(visibleColumns.filter((k) => k !== key))
    } else {
      // 保持原有顺序插入
      const columnIndex = columns.findIndex((c) => c.key === key)
      const newVisible = [...visibleColumns]
      let insertIndex = newVisible.length
      for (let i = 0; i < newVisible.length; i++) {
        const currentIndex = columns.findIndex((c) => c.key === newVisible[i])
        if (currentIndex > columnIndex) {
          insertIndex = i
          break
        }
      }
      newVisible.splice(insertIndex, 0, key)
      onChange(newVisible)
    }
  }

  const handleSelectAll = () => {
    onChange(columns.map((c) => c.key))
  }

  const handleSelectDefault = () => {
    // 选择必选列 + 前几个非必选列
    const requiredKeys = columns.filter((c) => c.required).map((c) => c.key)
    const optionalKeys = columns.filter((c) => !c.required).slice(0, 5).map((c) => c.key)
    onChange([...requiredKeys, ...optionalKeys])
  }

  const visibleCount = visibleColumns.length
  const totalCount = columns.length

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          'flex items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm',
          'hover:bg-accent hover:text-accent-foreground transition-colors',
          open && 'ring-2 ring-ring'
        )}
      >
        <Columns3 className="h-4 w-4" />
        <span>显示列</span>
        <span className="text-muted-foreground">({visibleCount}/{totalCount})</span>
        <ChevronDown className={cn('h-4 w-4 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-64 rounded-md border bg-popover shadow-lg">
          {/* 快捷操作 */}
          <div className="flex items-center justify-between border-b px-3 py-2">
            <span className="text-sm text-muted-foreground">选择显示的列</span>
            <div className="flex gap-2">
              <button
                onClick={handleSelectAll}
                className="text-xs text-primary hover:underline"
              >
                全选
              </button>
              <button
                onClick={handleSelectDefault}
                className="text-xs text-primary hover:underline"
              >
                默认
              </button>
            </div>
          </div>

          {/* 列列表 */}
          <div className="max-h-64 overflow-auto py-1">
            {columns.map((column) => {
              const isVisible = visibleColumns.includes(column.key)
              const isRequired = column.required
              return (
                <button
                  key={column.key}
                  onClick={() => handleToggle(column.key)}
                  disabled={isRequired}
                  className={cn(
                    'flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors',
                    'hover:bg-accent',
                    isRequired && 'opacity-60 cursor-not-allowed'
                  )}
                >
                  <div
                    className={cn(
                      'flex h-4 w-4 items-center justify-center rounded border',
                      isVisible
                        ? 'border-primary bg-primary text-primary-foreground'
                        : 'border-input'
                    )}
                  >
                    {isVisible && <Check className="h-3 w-3" />}
                  </div>
                  <span className="flex-1 text-left">{column.label}</span>
                  {isRequired && (
                    <span className="text-xs text-muted-foreground">必选</span>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
