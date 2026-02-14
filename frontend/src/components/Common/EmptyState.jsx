import React from 'react'
import { FolderOpenIcon } from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'
import { Button } from './Button'

export function EmptyState({
  icon: Icon = FolderOpenIcon,
  title = 'No data',
  description,
  action,
  actionLabel,
  onAction,
  className,
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 px-4', className)}>
      <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
        <Icon className="w-8 h-8 text-gray-400 dark:text-gray-500" />
      </div>
      
      <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-1">
        {title}
      </h3>
      
      {description && (
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center max-w-sm mb-4">
          {description}
        </p>
      )}
      
      {(action || (actionLabel && onAction)) && (
        <div className="mt-2">
          {action || (
            <Button onClick={onAction}>{actionLabel}</Button>
          )}
        </div>
      )}
    </div>
  )
}

// Specific empty states
export function NoResultsState({ searchTerm, onClear }) {
  return (
    <EmptyState
      title="No results found"
      description={
        searchTerm
          ? `No results found for "${searchTerm}". Try adjusting your search.`
          : 'No results match your current filters.'
      }
      actionLabel={searchTerm ? 'Clear search' : 'Clear filters'}
      onAction={onClear}
    />
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <EmptyState
      icon={({ className }) => (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      )}
      title="Something went wrong"
      description={message || 'An error occurred while loading data.'}
      actionLabel="Try again"
      onAction={onRetry}
    />
  )
}

export default EmptyState