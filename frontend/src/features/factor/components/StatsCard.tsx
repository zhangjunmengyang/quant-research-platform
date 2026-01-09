/**
 * Stats Card Component
 * Design System: Unified stats card for displaying metrics
 *
 * Visual Hierarchy:
 * - Default variant: Standard display for all metrics (recommended)
 * - Compact variant: Dense display for secondary information
 */

import { cn } from '@/lib/utils'

interface StatsCardProps {
  title: string
  value: string | number
  description?: string
  icon?: React.ReactNode
  trend?: {
    value: number
    isPositive: boolean
  }
  className?: string
  /** Visual hierarchy: default (standard), compact (small) */
  variant?: 'default' | 'compact'
  /** Optional accent color for the value */
  valueColor?: 'default' | 'success' | 'warning' | 'destructive' | 'info'
  /** Icon background color class (e.g., 'bg-purple-500') */
  iconColorClass?: string
}

const variantStyles = {
  default: {
    container: 'p-4',
    title: 'text-sm text-muted-foreground',
    value: 'text-2xl font-bold tabular-nums',
    iconWrapper: 'h-10 w-10 rounded-lg [&>svg]:h-5 [&>svg]:w-5',
    trend: 'text-sm font-medium',
    description: 'text-xs text-muted-foreground',
    gap: 'mt-2',
  },
  compact: {
    container: 'p-4',
    title: 'text-xs font-medium text-muted-foreground',
    value: 'text-xl font-semibold tabular-nums',
    iconWrapper: 'h-8 w-8 rounded-md [&>svg]:h-4 [&>svg]:w-4',
    trend: 'text-xs font-medium',
    description: 'text-2xs text-muted-foreground',
    gap: 'mt-2',
  },
}

const valueColorStyles = {
  default: '',
  success: 'text-success',
  warning: 'text-warning',
  destructive: 'text-destructive',
  info: 'text-info',
}

export function StatsCard({
  title,
  value,
  description,
  icon,
  trend,
  className,
  variant = 'default',
  valueColor = 'default',
  iconColorClass,
}: StatsCardProps) {
  const styles = variantStyles[variant]

  return (
    <div
      className={cn(
        'rounded-lg border bg-card text-card-foreground shadow-depth-1',
        'transition-shadow duration-200 hover:shadow-depth-2',
        styles.container,
        className
      )}
    >
      <div className="flex items-center justify-between">
        <p className={styles.title}>{title}</p>
        {icon && (
          <div
            className={cn(
              'flex items-center justify-center',
              iconColorClass ? iconColorClass : 'bg-primary/10',
              iconColorClass ? 'text-white' : 'text-primary',
              styles.iconWrapper
            )}
          >
            {icon}
          </div>
        )}
      </div>
      <div className={cn('flex items-baseline gap-2', styles.gap)}>
        <p className={cn(styles.value, valueColorStyles[valueColor])}>{value}</p>
        {trend && (
          <span
            className={cn(
              styles.trend,
              trend.isPositive ? 'text-success' : 'text-destructive'
            )}
          >
            {trend.isPositive ? '+' : ''}
            {trend.value}%
          </span>
        )}
      </div>
      {description && <p className={cn('mt-1.5', styles.description)}>{description}</p>}
    </div>
  )
}
