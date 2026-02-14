import React, { forwardRef } from 'react'
import { cn } from '@/utils/helpers'

const Input = forwardRef(({
  label,
  error,
  hint,
  icon: Icon,
  iconPosition = 'left',
  size = 'md',
  fullWidth = true,
  className,
  containerClassName,
  ...props
}, ref) => {
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-4 py-3 text-base',
  }

  const iconPadding = {
    left: {
      sm: 'pl-9',
      md: 'pl-10',
      lg: 'pl-11',
    },
    right: {
      sm: 'pr-9',
      md: 'pr-10',
      lg: 'pr-11',
    },
  }

  return (
    <div className={cn(fullWidth && 'w-full', containerClassName)}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {label}
        </label>
      )}
      
      <div className="relative">
        {Icon && iconPosition === 'left' && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Icon className="h-5 w-5 text-gray-400" />
          </div>
        )}
        
        <input
          ref={ref}
          className={cn(
            'w-full rounded-lg border bg-white text-gray-900',
            'placeholder-gray-400',
            'focus:outline-none focus:ring-2 focus:border-transparent',
            'disabled:bg-gray-100 disabled:cursor-not-allowed',
            'dark:bg-gray-800 dark:text-gray-100 dark:border-gray-600',
            'transition-colors duration-200',
            sizes[size],
            error
              ? 'border-danger-500 focus:ring-danger-500'
              : 'border-gray-300 focus:ring-primary-500 dark:border-gray-600',
            Icon && iconPosition === 'left' && iconPadding.left[size],
            Icon && iconPosition === 'right' && iconPadding.right[size],
            className
          )}
          {...props}
        />
        
        {Icon && iconPosition === 'right' && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <Icon className="h-5 w-5 text-gray-400" />
          </div>
        )}
      </div>
      
      {error && (
        <p className="mt-1 text-sm text-danger-600 dark:text-danger-400">{error}</p>
      )}
      
      {hint && !error && (
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{hint}</p>
      )}
    </div>
  )
})

Input.displayName = 'Input'

// Textarea component
export const Textarea = forwardRef(({
  label,
  error,
  hint,
  rows = 4,
  className,
  containerClassName,
  ...props
}, ref) => {
  return (
    <div className={cn('w-full', containerClassName)}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {label}
        </label>
      )}
      
      <textarea
        ref={ref}
        rows={rows}
        className={cn(
          'w-full px-4 py-2 text-sm rounded-lg border bg-white text-gray-900',
          'placeholder-gray-400',
          'focus:outline-none focus:ring-2 focus:border-transparent',
          'disabled:bg-gray-100 disabled:cursor-not-allowed',
          'dark:bg-gray-800 dark:text-gray-100 dark:border-gray-600',
          'transition-colors duration-200 resize-none',
          error
            ? 'border-danger-500 focus:ring-danger-500'
            : 'border-gray-300 focus:ring-primary-500',
          className
        )}
        {...props}
      />
      
      {error && (
        <p className="mt-1 text-sm text-danger-600">{error}</p>
      )}
      
      {hint && !error && (
        <p className="mt-1 text-sm text-gray-500">{hint}</p>
      )}
    </div>
  )
})

Textarea.displayName = 'Textarea'

export default Input