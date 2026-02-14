import React from 'react'
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'

const variants = {
  info: {
    container: 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800',
    icon: 'text-blue-500',
    title: 'text-blue-800 dark:text-blue-200',
    message: 'text-blue-700 dark:text-blue-300',
    Icon: InformationCircleIcon,
  },
  success: {
    container: 'bg-success-50 border-success-200 dark:bg-success-900/20 dark:border-success-800',
    icon: 'text-success-500',
    title: 'text-success-800 dark:text-success-200',
    message: 'text-success-700 dark:text-success-300',
    Icon: CheckCircleIcon,
  },
  warning: {
    container: 'bg-warning-50 border-warning-200 dark:bg-warning-900/20 dark:border-warning-800',
    icon: 'text-warning-500',
    title: 'text-warning-800 dark:text-warning-200',
    message: 'text-warning-700 dark:text-warning-300',
    Icon: ExclamationTriangleIcon,
  },
  danger: {
    container: 'bg-danger-50 border-danger-200 dark:bg-danger-900/20 dark:border-danger-800',
    icon: 'text-danger-500',
    title: 'text-danger-800 dark:text-danger-200',
    message: 'text-danger-700 dark:text-danger-300',
    Icon: XCircleIcon,
  },
}

export function Alert({
  variant = 'info',
  title,
  children,
  dismissible = false,
  onDismiss,
  className,
  icon: CustomIcon,
}) {
  const config = variants[variant]
  const Icon = CustomIcon || config.Icon

  return (
    <div
      className={cn(
        'flex p-4 rounded-lg border',
        config.container,
        className
      )}
      role="alert"
    >
      <div className="flex-shrink-0">
        <Icon className={cn('w-5 h-5', config.icon)} />
      </div>
      
      <div className="ml-3 flex-1">
        {title && (
          <h3 className={cn('text-sm font-medium', config.title)}>
            {title}
          </h3>
        )}
        {children && (
          <div className={cn('text-sm', config.message, title && 'mt-1')}>
            {children}
          </div>
        )}
      </div>
      
      {dismissible && (
        <button
          type="button"
          onClick={onDismiss}
          className={cn(
            'flex-shrink-0 ml-3 -mr-1.5 -mt-1.5 p-1.5 rounded-lg',
            'hover:bg-black/5 dark:hover:bg-white/5',
            'focus:outline-none focus:ring-2 focus:ring-offset-2',
            config.icon
          )}
        >
          <XMarkIcon className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}

export default Alert