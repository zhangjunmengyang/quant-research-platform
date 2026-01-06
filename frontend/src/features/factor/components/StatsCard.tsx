/**
 * Factor Statistics Card Component
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
  valueSize?: 'sm' | 'md' | 'lg'
}

const valueSizeClasses = {
  sm: 'text-lg font-semibold',
  md: 'text-2xl font-bold',
  lg: 'text-3xl font-bold',
}

export function StatsCard({
  title,
  value,
  description,
  icon,
  trend,
  className,
  valueSize = 'lg',
}: StatsCardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border bg-card p-6 text-card-foreground shadow-sm',
        className
      )}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        {icon && <div className="text-muted-foreground">{icon}</div>}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <p className={valueSizeClasses[valueSize]}>{value}</p>
        {trend && (
          <span
            className={cn(
              'text-sm font-medium',
              trend.isPositive ? 'text-green-600' : 'text-red-600'
            )}
          >
            {trend.isPositive ? '+' : ''}
            {trend.value}%
          </span>
        )}
      </div>
      {description && (
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      )}
    </div>
  )
}
