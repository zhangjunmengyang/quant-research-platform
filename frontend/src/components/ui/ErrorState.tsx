/**
 * Error State Component
 * 统一的错误状态展示组件
 *
 * @example
 * ```tsx
 * <ErrorState message="加载失败" />
 * <ErrorState message="网络错误" onRetry={() => refetch()} />
 * ```
 */

import { AlertCircle, RefreshCw, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ErrorStateProps {
  /** 错误消息 */
  message?: string
  /** 详细错误信息 */
  detail?: string
  /** 错误类型 */
  variant?: 'default' | 'network' | 'notFound' | 'permission'
  /** 重试回调 */
  onRetry?: () => void
  /** 重试按钮文字 */
  retryText?: string
  /** 自定义类名 */
  className?: string
  /** 全屏高度 */
  fullScreen?: boolean
  /** 图标 */
  icon?: React.ReactNode
}

export function ErrorState({
  message = '加载失败',
  detail,
  variant = 'default',
  onRetry,
  retryText = '重试',
  className,
  fullScreen = false,
  icon,
}: ErrorStateProps) {
  const variantConfig = {
    default: {
      icon: icon || <AlertCircle className="h-12 w-12 text-destructive" />,
      title: message,
    },
    network: {
      icon: icon || <XCircle className="h-12 w-12 text-orange-500" />,
      title: message || '网络连接失败',
    },
    notFound: {
      icon: icon || <AlertCircle className="h-12 w-12 text-muted-foreground" />,
      title: message || '未找到数据',
    },
    permission: {
      icon: icon || <XCircle className="h-12 w-12 text-yellow-500" />,
      title: message || '没有权限访问',
    },
  }

  const config = variantConfig[variant]

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4 text-center',
        fullScreen ? 'h-screen' : 'min-h-[200px]',
        className
      )}
    >
      {config.icon}
      <div>
        <p className="font-medium">{config.title}</p>
        {detail && <p className="mt-1 text-sm text-muted-foreground">{detail}</p>}
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
        >
          <RefreshCw className="h-4 w-4" />
          {retryText}
        </button>
      )}
    </div>
  )
}
