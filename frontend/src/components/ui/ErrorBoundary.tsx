/**
 * Error Boundary Component
 * 捕获子组件中的 JavaScript 错误，显示备用 UI
 *
 * @example
 * ```tsx
 * <ErrorBoundary fallback={<ErrorState message="加载失败" />}>
 *   <YourComponent />
 * </ErrorBoundary>
 * ```
 */

import { Component, ReactNode, ComponentType } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface ErrorBoundaryProps {
  children: ReactNode
  /** 错误时显示的备用 UI */
  fallback?: ReactNode
  /** 错误回调 */
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
}

/**
 * Error Boundary 类组件
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.props.onError?.(error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || <DefaultErrorFallback error={this.state.error} />
    }
    return this.props.children
  }
}

/**
 * 默认错误回退 UI
 */
interface DefaultErrorFallbackProps {
  error?: Error
}

function DefaultErrorFallback({ error }: DefaultErrorFallbackProps) {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-4 text-destructive">
      <AlertCircle className="h-12 w-12" />
      <div className="text-center">
        <p className="font-medium">出现错误</p>
        <p className="text-sm text-muted-foreground">
          {error?.message || '未知错误'}
        </p>
      </div>
      <button
        onClick={() => window.location.reload()}
        className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
      >
        <RefreshCw className="h-4 w-4" />
        重新加载
      </button>
    </div>
  )
}

/**
 * 高阶组件版本
 */
export function withErrorBoundary<P extends object>(
  Component: ComponentType<P>,
  fallback?: ReactNode
): ComponentType<P & { onError?: (error: Error, errorInfo: React.ErrorInfo) => void }> {
  return function WrappedComponent(props) {
    return (
      <ErrorBoundary fallback={fallback}>
        <Component {...props} />
      </ErrorBoundary>
    )
  }
}
