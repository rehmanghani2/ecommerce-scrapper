import React from 'react'
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'
import { Button } from './Button'

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  siblingCount = 1,
  className,
}) {
  // Generate page numbers to display
  const getPageNumbers = () => {
    const pages = []
    const totalNumbers = siblingCount * 2 + 3 // siblings + current + first + last
    const totalBlocks = totalNumbers + 2 // + 2 for dots

    if (totalPages <= totalBlocks) {
      // Show all pages
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i)
      }
    } else {
      const leftSiblingIndex = Math.max(currentPage - siblingCount, 1)
      const rightSiblingIndex = Math.min(currentPage + siblingCount, totalPages)

      const showLeftDots = leftSiblingIndex > 2
      const showRightDots = rightSiblingIndex < totalPages - 1

      if (!showLeftDots && showRightDots) {
        // Show more pages at start
        for (let i = 1; i <= 3 + siblingCount * 2; i++) {
          pages.push(i)
        }
        pages.push('...')
        pages.push(totalPages)
      } else if (showLeftDots && !showRightDots) {
        // Show more pages at end
        pages.push(1)
        pages.push('...')
        for (let i = totalPages - (2 + siblingCount * 2); i <= totalPages; i++) {
          pages.push(i)
        }
      } else {
        // Show dots on both sides
        pages.push(1)
        pages.push('...')
        for (let i = leftSiblingIndex; i <= rightSiblingIndex; i++) {
          pages.push(i)
        }
        pages.push('...')
        pages.push(totalPages)
      }
    }

    return pages
  }

  if (totalPages <= 1) return null

  return (
    <nav
      className={cn('flex items-center justify-center gap-1', className)}
      aria-label="Pagination"
    >
      {/* Previous button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="px-2"
      >
        <ChevronLeftIcon className="w-5 h-5" />
      </Button>

      {/* Page numbers */}
      {getPageNumbers().map((page, index) => (
        <React.Fragment key={index}>
          {page === '...' ? (
            <span className="px-3 py-2 text-gray-500">...</span>
          ) : (
            <button
              onClick={() => onPageChange(page)}
              className={cn(
                'min-w-[40px] h-10 px-3 text-sm font-medium rounded-lg transition-colors',
                page === currentPage
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
              )}
            >
              {page}
            </button>
          )}
        </React.Fragment>
      ))}

      {/* Next button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="px-2"
      >
        <ChevronRightIcon className="w-5 h-5" />
      </Button>
    </nav>
  )
}

// Simple pagination with info
export function SimplePagination({
  currentPage,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
  className,
}) {
  const startItem = (currentPage - 1) * pageSize + 1
  const endItem = Math.min(currentPage * pageSize, totalItems)

  return (
    <div className={cn('flex items-center justify-between', className)}>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Showing <span className="font-medium">{startItem}</span> to{' '}
        <span className="font-medium">{endItem}</span> of{' '}
        <span className="font-medium">{totalItems}</span> results
      </p>
      
      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
        >
          Previous
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
        >
          Next
        </Button>
      </div>
    </div>
  )
}

export default Pagination