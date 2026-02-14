import React from 'react'
import { cn } from '@/utils/helpers'

export function Card({
  children,
  className,
  padding = 'md',
  hover = false,
  ...props
}) {
  const paddings = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  }

  return (
    <div
      className={cn(
        'bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700',
        hover && 'transition-shadow duration-200 hover:shadow-md',
        paddings[padding],
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className, action }) {
  return (
    <div className={cn('flex items-center justify-between mb-4', className)}>
      <div>{children}</div>
      {action && <div>{action}</div>}
    </div>
  )
}

export function CardTitle({ children, className }) {
  return (
    <h3 className={cn('text-lg font-semibold text-gray-900 dark:text-gray-100', className)}>
      {children}
    </h3>
  )
}

export function CardDescription({ children, className }) {
  return (
    <p className={cn('text-sm text-gray-500 dark:text-gray-400 mt-1', className)}>
      {children}
    </p>
  )
}

export function CardContent({ children, className }) {
  return <div className={cn('', className)}>{children}</div>
}

export function CardFooter({ children, className }) {
  return (
    <div className={cn('flex items-center justify-end gap-3 mt-4 pt-4 border-t dark:border-gray-700', className)}>
      {children}
    </div>
  )
}

// Stat Card for dashboard
export function StatCard({
  title,
  value,
  change,
  changeType = 'neutral',
  icon: Icon,
  iconColor = 'primary',
  loading = false,
  className,
}) {
  const iconColors = {
    primary: 'bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400',
    success: 'bg-success-100 text-success-600 dark:bg-success-900/30 dark:text-success-400',
    warning: 'bg-warning-100 text-warning-600 dark:bg-warning-900/30 dark:text-warning-400',
    danger: 'bg-danger-100 text-danger-600 dark:bg-danger-900/30 dark:text-danger-400',
  }

  const changeColors = {
    positive: 'text-success-600 dark:text-success-400',
    negative: 'text-danger-600 dark:text-danger-400',
    neutral: 'text-gray-500 dark:text-gray-400',
  }

  return (
    <Card className={className}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            {title}
          </p>
          {loading ? (
            <div className="h-8 w-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mt-1" />
          ) : (
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">
              {value}
            </p>
          )}
          {change && (
            <p className={cn('text-sm mt-1', changeColors[changeType])}>
              {change}
            </p>
          )}
        </div>
        
        {Icon && (
          <div className={cn('p-3 rounded-xl', iconColors[iconColor])}>
            <Icon className="w-6 h-6" />
          </div>
        )}
      </div>
    </Card>
  )
}

export default Card