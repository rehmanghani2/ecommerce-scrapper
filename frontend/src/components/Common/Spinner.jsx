import React from 'react'
import { cn } from '@/utils/helpers'

const sizes = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
  xl: 'w-12 h-12',
}

export function Spinner({
  size = 'md',
  className,
  color = 'currentColor',
}) {
  return (
    <svg
      className={cn('animate-spin', sizes[size], className)}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke={color}
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill={color}
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

// Full page loader
export function PageLoader({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px]">
      <Spinner size="xl" className="text-primary-600" />
      {message && (
        <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">{message}</p>
      )}
    </div>
  )
}

// Overlay loader
export function OverlayLoader({ message }) {
  return (
    <div className="absolute inset-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm flex items-center justify-center z-50 rounded-lg">
      <div className="text-center">
        <Spinner size="lg" className="text-primary-600" />
        {message && (
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{message}</p>
        )}
      </div>
    </div>
  )
}

export default Spinner