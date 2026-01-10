/**
 * Loading State Component
 * 统一的加载状态展示组件
 *
 * @example
 * ```tsx
 * <LoadingState />
 * <LoadingState message="加载数据中..." />
 * <LoadingState size="large" />
 * ```
 */

import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface LoadingStateProps {
  /** 加载提示文字 */
  message?: string
  /** 尺寸 */
  size?: 'small' | 'medium' | 'large'
  /** 自定义类名 */
  className?: string
  /** 全屏高度 */
  fullScreen?: boolean
}

export function LoadingState({
  message = '加载中...',
  size = 'medium',
  className,
  fullScreen = false,
}: LoadingStateProps) {
  const sizeClasses = {
    small: 'h-4 w-4',
    medium: 'h-8 w-8',
    large: 'h-12 w-12',
  }

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 text-muted-foreground',
        fullScreen && 'h-screen',
        className
      )}
    >
      <Loader2 className={cn('animate-spin', sizeClasses[size])} />
      {message && <p className="text-sm">{message}</p>}
    </div>
  )
}
