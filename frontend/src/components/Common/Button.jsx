import React from 'react'
import { cn } from '@/utils/helpers'
import Spinner from './Spinner'

const variants = {
  primary: 'bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500',
  secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-500 dark:bg-gray-700 dark:text-gray-100 dark:hover:bg-gray-600',
  success: 'bg-success-600 text-white hover:bg-success-700 focus:ring-success-500',
  danger: 'bg-danger-600 text-white hover:bg-danger-700 focus:ring-danger-500',
  warning: 'bg-warning-500 text-white hover:bg-warning-600 focus:ring-warning-500',
  ghost: 'bg-transparent text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800',
  outline: 'bg-transparent border-2 border-primary-600 text-primary-600 hover:bg-primary-50 dark:border-primary-400 dark:text-primary-400 dark:hover:bg-primary-900/20',
  link: 'bg-transparent text-primary-600 hover:text-primary-700 hover:underline dark:text-primary-400',
}

const sizes = {
  xs: 'px-2 py-1 text-xs',
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-base',
  xl: 'px-6 py-3 text-lg',
}

const iconSizes = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
  xl: 'w-6 h-6',
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon: Icon,
  iconPosition = 'left',
  loading = false,
  disabled = false,
  fullWidth = false,
  rounded = false,
  className,
  ...props
}) {
  const isDisabled = disabled || loading

  return (
    <button
      className={cn(
        'inline-flex items-center justify-center font-medium transition-all duration-200',
        'focus:outline-none focus:ring-2 focus:ring-offset-2',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        rounded ? 'rounded-full' : 'rounded-lg',
        variants[variant],
        sizes[size],
        fullWidth && 'w-full',
        className
      )}
      disabled={isDisabled}
      {...props}
    >
      {loading && (
        <Spinner size="sm" className={cn('mr-2', iconSizes[size])} />
      )}
      
      {!loading && Icon && iconPosition === 'left' && (
        <Icon className={cn('mr-2', iconSizes[size])} />
      )}
      
      {children}
      
      {!loading && Icon && iconPosition === 'right' && (
        <Icon className={cn('ml-2', iconSizes[size])} />
      )}
    </button>
  )
}

// Icon-only button variant
export function IconButton({
  icon: Icon,
  variant = 'ghost',
  size = 'md',
  loading = false,
  disabled = false,
  rounded = true,
  className,
  ...props
}) {
  const iconOnlySizes = {
    xs: 'p-1',
    sm: 'p-1.5',
    md: 'p-2',
    lg: 'p-2.5',
    xl: 'p-3',
  }

  return (
    <button
      className={cn(
        'inline-flex items-center justify-center transition-all duration-200',
        'focus:outline-none focus:ring-2 focus:ring-offset-2',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        rounded ? 'rounded-full' : 'rounded-lg',
        variants[variant],
        iconOnlySizes[size],
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <Spinner size="sm" className={iconSizes[size]} />
      ) : (
        <Icon className={iconSizes[size]} />
      )}
    </button>
  )
}

export default Button