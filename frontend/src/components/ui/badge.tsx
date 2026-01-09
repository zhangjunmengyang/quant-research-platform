/**
 * Badge Component
 * Design System: Unified badge styles with semantic color variants
 */

import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground',
        secondary: 'border-transparent bg-secondary text-secondary-foreground',
        destructive: 'bg-destructive-muted text-destructive border-destructive/20',
        outline: 'text-foreground border-border',
        success: 'bg-success-muted text-success border-success/20',
        warning: 'bg-warning-muted text-warning border-warning/20',
        info: 'bg-info-muted text-info border-info/20',
        muted: 'bg-muted text-muted-foreground border-transparent',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

// Status badge with dot indicator
interface StatusBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  status: 'online' | 'offline' | 'pending' | 'error' | 'success' | 'warning'
  label?: string
}

const statusConfig = {
  online: { dot: 'bg-success', text: 'text-success', bg: 'bg-success-muted' },
  offline: { dot: 'bg-muted-foreground', text: 'text-muted-foreground', bg: 'bg-muted' },
  pending: { dot: 'bg-warning animate-pulse', text: 'text-warning', bg: 'bg-warning-muted' },
  error: { dot: 'bg-destructive', text: 'text-destructive', bg: 'bg-destructive-muted' },
  success: { dot: 'bg-success', text: 'text-success', bg: 'bg-success-muted' },
  warning: { dot: 'bg-warning', text: 'text-warning', bg: 'bg-warning-muted' },
}

function StatusBadge({ status, label, className, children, ...props }: StatusBadgeProps) {
  const config = statusConfig[status]
  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        config.bg,
        config.text,
        className
      )}
      {...props}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', config.dot)} />
      {label || children || status}
    </div>
  )
}

export { Badge, badgeVariants, StatusBadge }
