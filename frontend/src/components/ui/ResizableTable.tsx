/**
 * ResizableTable - 支持列宽拖拽调整和表头排序的表格组件
 */

import { useState, useRef, useCallback, useEffect, type ReactNode } from 'react'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { cn } from '@/lib/utils'

export type SortOrder = 'asc' | 'desc'

export interface TableColumn<T> {
  key: string
  label: string
  width: number
  minWidth?: number
  maxWidth?: number
  render?: (value: unknown, row: T, index: number) => ReactNode
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
  fixed?: 'left' | 'right'
}

export interface SortState {
  field: string
  order: SortOrder
}

interface ResizableTableProps<T> {
  columns: TableColumn<T>[]
  data: T[]
  rowKey: keyof T | ((row: T) => string)
  onColumnWidthChange?: (columnKey: string, width: number) => void
  onRowClick?: (row: T) => void
  emptyText?: string
  className?: string
  headerClassName?: string
  rowClassName?: string | ((row: T, index: number) => string)
  stickyHeader?: boolean
  maxHeight?: number | string
  // 排序相关
  sortState?: SortState
  onSortChange?: (sort: SortState) => void
}

export function ResizableTable<T>({
  columns,
  data,
  rowKey,
  onColumnWidthChange,
  onRowClick,
  emptyText = '暂无数据',
  className,
  headerClassName,
  rowClassName,
  stickyHeader = false,
  maxHeight,
  sortState,
  onSortChange,
}: ResizableTableProps<T>) {
  // 列宽状态
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>(() => {
    const widths: Record<string, number> = {}
    columns.forEach((col) => {
      widths[col.key] = col.width
    })
    return widths
  })

  // 拖拽状态
  const [resizing, setResizing] = useState<string | null>(null)
  const resizeStartX = useRef(0)
  const resizeStartWidth = useRef(0)
  const tableRef = useRef<HTMLDivElement>(null)

  // 当 columns 变化时更新宽度
  useEffect(() => {
    setColumnWidths((prev) => {
      const newWidths: Record<string, number> = {}
      columns.forEach((col) => {
        // 保留已有的宽度，否则使用默认值
        newWidths[col.key] = prev[col.key] ?? col.width
      })
      return newWidths
    })
  }, [columns])

  // 获取行的 key
  const getRowKey = useCallback(
    (row: T): string => {
      if (typeof rowKey === 'function') {
        return rowKey(row)
      }
      return String(row[rowKey])
    },
    [rowKey]
  )

  // 开始拖拽
  const handleResizeStart = useCallback(
    (e: React.MouseEvent, columnKey: string) => {
      e.preventDefault()
      e.stopPropagation()
      setResizing(columnKey)
      resizeStartX.current = e.clientX
      resizeStartWidth.current = columnWidths[columnKey] ?? 100
    },
    [columnWidths]
  )

  // 拖拽中
  const handleResizeMove = useCallback(
    (e: MouseEvent) => {
      if (!resizing) return

      const column = columns.find((c) => c.key === resizing)
      if (!column) return

      const diff = e.clientX - resizeStartX.current
      const minW = column.minWidth ?? 50
      const maxW = column.maxWidth ?? 800
      const newWidth = Math.max(minW, Math.min(maxW, resizeStartWidth.current + diff))

      setColumnWidths((prev) => ({
        ...prev,
        [resizing]: newWidth,
      }))
    },
    [resizing, columns]
  )

  // 结束拖拽
  const handleResizeEnd = useCallback(() => {
    if (resizing && onColumnWidthChange) {
      const width = columnWidths[resizing] ?? 100
      onColumnWidthChange(resizing, width)
    }
    setResizing(null)
  }, [resizing, columnWidths, onColumnWidthChange])

  // 添加/移除全局事件监听
  useEffect(() => {
    if (resizing) {
      document.addEventListener('mousemove', handleResizeMove)
      document.addEventListener('mouseup', handleResizeEnd)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'

      return () => {
        document.removeEventListener('mousemove', handleResizeMove)
        document.removeEventListener('mouseup', handleResizeEnd)
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
      }
    }
  }, [resizing, handleResizeMove, handleResizeEnd])

  // 处理排序点击
  const handleSortClick = useCallback(
    (columnKey: string) => {
      if (!onSortChange) return
      if (sortState?.field === columnKey) {
        // 切换排序方向
        onSortChange({
          field: columnKey,
          order: sortState.order === 'asc' ? 'desc' : 'asc',
        })
      } else {
        // 新字段，默认降序
        onSortChange({ field: columnKey, order: 'desc' })
      }
    },
    [sortState, onSortChange]
  )

  // 渲染排序图标
  const renderSortIcon = (columnKey: string, isSortable: boolean) => {
    if (!isSortable || !onSortChange) return null

    if (sortState?.field !== columnKey) {
      return <ArrowUpDown className="h-3.5 w-3.5 text-muted-foreground/50" />
    }
    return sortState.order === 'asc' ? (
      <ArrowUp className="h-3.5 w-3.5" />
    ) : (
      <ArrowDown className="h-3.5 w-3.5" />
    )
  }

  // 计算总宽度
  const totalWidth = columns.reduce((sum, col) => {
    const w = columnWidths[col.key] ?? col.width
    return sum + w
  }, 0)

  // 渲染单元格内容
  const renderCell = (column: TableColumn<T>, row: T, index: number) => {
    const value = (row as Record<string, unknown>)[column.key]
    if (column.render) {
      return column.render(value, row, index)
    }
    if (value === null || value === undefined) {
      return <span className="text-muted-foreground">-</span>
    }
    return String(value)
  }

  // 获取行的 className
  const getRowClassName = (row: T, index: number): string => {
    if (typeof rowClassName === 'function') {
      return rowClassName(row, index)
    }
    return rowClassName || ''
  }

  return (
    <div
      ref={tableRef}
      className={cn('rounded-lg border overflow-hidden bg-background', className)}
      style={{ maxHeight }}
    >
      <div className="overflow-auto" style={{ maxHeight: maxHeight ? '100%' : undefined }}>
        <table
          className="w-full border-collapse"
          style={{ minWidth: totalWidth, tableLayout: 'fixed' }}
        >
          {/* colgroup 定义列宽 */}
          <colgroup>
            {columns.map((col) => (
              <col key={col.key} style={{ width: columnWidths[col.key] ?? col.width }} />
            ))}
          </colgroup>

          {/* 表头 - 白色背景 */}
          <thead className={cn(stickyHeader && 'sticky top-0 z-10')}>
            <tr className={cn('border-b bg-background', headerClassName)}>
              {columns.map((col) => {
                const isSortable = col.sortable && onSortChange
                return (
                  <th
                    key={col.key}
                    className={cn(
                      'relative px-3 py-3 text-sm font-medium text-muted-foreground select-none',
                      col.align === 'center' && 'text-center',
                      col.align === 'right' && 'text-right',
                      !col.align && 'text-left',
                      isSortable && 'cursor-pointer hover:bg-muted/50'
                    )}
                    style={{ width: columnWidths[col.key] ?? col.width }}
                    onClick={() => isSortable && handleSortClick(col.key)}
                  >
                    <div
                      className={cn(
                        'flex items-center gap-1.5',
                        col.align === 'center' && 'justify-center',
                        col.align === 'right' && 'justify-end'
                      )}
                    >
                      <span className="truncate">{col.label}</span>
                      {renderSortIcon(col.key, !!col.sortable)}
                    </div>

                    {/* 拖拽手柄 */}
                    <div
                      className={cn(
                        'absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/50 transition-colors',
                        resizing === col.key && 'bg-primary'
                      )}
                      onMouseDown={(e) => handleResizeStart(e, col.key)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </th>
                )
              })}
            </tr>
          </thead>

          {/* 表体 */}
          <tbody className="divide-y">
            {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center text-muted-foreground">
                  {emptyText}
                </td>
              </tr>
            ) : (
              data.map((row, index) => (
                <tr
                  key={getRowKey(row)}
                  className={cn(
                    'hover:bg-muted/30 transition-colors border-b last:border-b-0',
                    onRowClick && 'cursor-pointer',
                    getRowClassName(row, index)
                  )}
                  onClick={() => onRowClick?.(row)}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        'px-3 py-3 text-sm bg-background',
                        col.align === 'center' && 'text-center',
                        col.align === 'right' && 'text-right'
                      )}
                    >
                      <div className="truncate">{renderCell(col, row, index)}</div>
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
