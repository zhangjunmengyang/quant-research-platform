/**
 * Pagination Component
 * 统一的分页组件，支持多种显示模式
 */

import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface PaginationProps {
  /** 当前页码 (从 1 开始) */
  page: number
  /** 每页条数 */
  pageSize: number
  /** 总条数 */
  total: number
  /** 总页数 (可选，会自动计算) */
  totalPages?: number
  /** 页码变化回调 */
  onPageChange: (page: number) => void
  /** 每页条数变化回调 (可选) */
  onPageSizeChange?: (size: number) => void
  /** 可选的每页条数 */
  pageSizeOptions?: number[]
  /** 显示模式 */
  variant?: 'default' | 'simple' | 'range'
  /** 位置 */
  position?: 'start' | 'center' | 'end' | 'between'
  /** 自定义类名 */
  className?: string
}

/** 内部组件: 上一页按钮 */
interface PrevButtonProps {
  disabled: boolean
  onClick: () => void
  variant: 'default' | 'simple'
}

function PrevButton({ disabled, onClick, variant }: PrevButtonProps) {
  if (variant === 'simple') {
    return (
      <button
        onClick={onClick}
        disabled={disabled}
        className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted"
      >
        上一页
      </button>
    )
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="p-1.5 rounded hover:bg-accent disabled:opacity-30 disabled:cursor-not-allowed"
    >
      <ChevronLeft className="h-4 w-4" />
    </button>
  )
}

/** 内部组件: 下一页按钮 */
interface NextButtonProps {
  disabled: boolean
  onClick: () => void
  variant: 'default' | 'simple'
}

function NextButton({ disabled, onClick, variant }: NextButtonProps) {
  if (variant === 'simple') {
    return (
      <button
        onClick={onClick}
        disabled={disabled}
        className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted"
      >
        下一页
      </button>
    )
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="p-1.5 rounded hover:bg-accent disabled:opacity-30 disabled:cursor-not-allowed"
    >
      <ChevronRight className="h-4 w-4" />
    </button>
  )
}

/** 内部组件: 页码显示 */
interface PageInfoProps {
  page: number
  totalPages: number
}

function PageInfo({ page, totalPages }: PageInfoProps) {
  return (
    <span className="text-sm text-muted-foreground">
      {page} / {totalPages}
    </span>
  )
}

/** 内部组件: 范围显示 */
interface RangeInfoProps {
  page: number
  pageSize: number
  total: number
}

function RangeInfo({ page, pageSize, total }: RangeInfoProps) {
  const start = (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)
  return (
    <p className="text-sm text-muted-foreground">
      显示 {start}-{end} / 共 {total} 条
    </p>
  )
}

/** 内部组件: 总数显示 */
interface TotalInfoProps {
  total: number
}

function TotalInfo({ total }: TotalInfoProps) {
  return (
    <span className="text-sm text-muted-foreground">共 {total} 条</span>
  )
}

/** 内部组件: 每页条数选择器 */
interface PageSizeSelectProps {
  value: number
  options: number[]
  onChange: (size: number) => void
}

function PageSizeSelect({ value, options, onChange }: PageSizeSelectProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="h-8 px-2 rounded border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
    >
      {options.map((size) => (
        <option key={size} value={size}>
          {size}条/页
        </option>
      ))}
    </select>
  )
}

/** 主组件 */
export function Pagination({
  page,
  pageSize,
  total,
  totalPages: propsTotalPages,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [20, 50, 100, 200],
  variant = 'default',
  position = 'end',
  className,
}: PaginationProps) {
  const totalPages = (propsTotalPages ?? Math.ceil(total / pageSize)) || 1
  const hasPrev = page > 1
  const hasNext = page < totalPages

  // 如果没有数据或只有一页，不显示分页
  if (total === 0 || totalPages <= 1) {
    return null
  }

  const content = (
    <div
      className={cn(
        'flex items-center gap-2 text-sm',
        {
          'justify-start': position === 'start',
          'justify-center': position === 'center',
          'justify-end': position === 'end',
          'justify-between': position === 'between',
        },
        className
      )}
    >
      {/* 左侧范围信息 (仅 range 模式) */}
      {variant === 'range' && position === 'between' && (
        <RangeInfo page={page} pageSize={pageSize} total={total} />
      )}

      {/* 中间控制区 */}
      <div className="flex items-center gap-2">
        {variant === 'simple' ? (
          <>
            <PrevButton disabled={!hasPrev} onClick={() => onPageChange(page - 1)} variant="simple" />
            <span className="px-3 text-sm text-muted-foreground">
              第 {page} / {totalPages} 页
            </span>
            <NextButton disabled={!hasNext} onClick={() => onPageChange(page + 1)} variant="simple" />
          </>
        ) : (
          <>
            <PrevButton disabled={!hasPrev} onClick={() => onPageChange(page - 1)} variant="default" />
            <PageInfo page={page} totalPages={totalPages} />
            <NextButton disabled={!hasNext} onClick={() => onPageChange(page + 1)} variant="default" />
          </>
        )}
      </div>

      {/* 右侧每页条数选择器 (仅 default 模式且有 onPageSizeChange) */}
      {variant === 'default' && onPageSizeChange && (
        <PageSizeSelect value={pageSize} options={pageSizeOptions} onChange={onPageSizeChange} />
      )}

      {/* 右侧总数信息 (仅 default 模式且非 between 位置) */}
      {variant === 'default' && position !== 'between' && (
        <TotalInfo total={total} />
      )}
    </div>
  )

  return content
}
