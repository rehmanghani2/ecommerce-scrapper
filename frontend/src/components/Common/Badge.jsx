import React from 'react'
import { cn } from '@/utils/helpers'

const variants = {
  primary: 'bg-primary-100 text-primary-800 dark:bg-primary-900/30 dark:text-primary-400',
  secondary: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
  success: 'bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-400',
  warning: 'bg-warning-100 text-warning-800 dark:bg-warning-900/30 dark:text-warning-400',
  danger: 'bg-danger-100 text-danger-800 dark:bg-danger-900/30 dark:text-danger-400',
  info: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
}

const sizes = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-0.5 text-xs',
  lg: 'px-3 py-1 text-sm',
}

export function Badge({
  children,
  variant = 'primary',
  size = 'md',
  dot = false,
  removable = false,
  onRemove,
  className,
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded-full',
        variants[variant],
        sizes[size],
        className
      )}
    >
      {dot && (
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full mr-1.5',
            variant === 'success' && 'bg-success-500',
            variant === 'warning' && 'bg-warning-500',
            variant === 'danger' && 'bg-danger-500',
            variant === 'primary' && 'bg-primary-500',
            variant === 'secondary' && 'bg-gray-500',
            variant === 'info' && 'bg-blue-500'
          )}
        />
      )}
      {children}
      {removable && (
        <button
          type="button"
          onClick={onRemove}
          className="ml-1.5 -mr-1 hover:opacity-75"
        >
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      )}
    </span>
  )
}

// Status Badge specifically for job statuses
export function StatusBadge({ status, size = 'md' }) {
  const statusConfig = {
    pending: { variant: 'secondary', label: 'Pending' },
    queued: { variant: 'info', label: 'Queued' },
    running: { variant: 'primary', label: 'Running', dot: true },
    paused: { variant: 'warning', label: 'Paused' },
    completed: { variant: 'success', label: 'Completed' },
    failed: { variant: 'danger', label: 'Failed' },
    cancelled: { variant: 'secondary', label: 'Cancelled' },
  }

  const config = statusConfig[status] || statusConfig.pending

  return (
    <Badge variant={config.variant} size={size} dot={config.dot}>
      {config.label}
    </Badge>
  )
}

export default Badge