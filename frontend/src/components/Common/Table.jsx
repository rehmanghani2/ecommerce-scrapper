import React from 'react'
import { cn } from '@/utils/helpers'
import { Spinner } from './Spinner'
import EmptyState from './EmptyState'

export function Table({ children, className }) {
  return (
    <div className={cn('overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700', className)}>
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        {children}
      </table>
    </div>
  )
}

export function TableHead({ children, className }) {
  return (
    <thead className={cn('bg-gray-50 dark:bg-gray-800', className)}>
      {children}
    </thead>
  )
}

export function TableBody({ children, className }) {
  return (
    <tbody className={cn('divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-900', className)}>
      {children}
    </tbody>
  )
}

export function TableRow({ children, className, onClick, clickable = false }) {
  return (
    <tr
      className={cn(
        'transition-colors',
        clickable && 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800',
        !clickable && 'hover:bg-gray-50/50 dark:hover:bg-gray-800/50',
        className
      )}
      onClick={onClick}
    >
      {children}
    </tr>
  )
}

export function TableHeader({ children, className, sortable, sorted, sortDirection, onSort }) {
  return (
    <th
      className={cn(
        'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider',
        'dark:text-gray-400',
        sortable && 'cursor-pointer select-none hover:text-gray-700 dark:hover:text-gray-200',
        className
      )}
      onClick={sortable ? onSort : undefined}
    >
      <div className="flex items-center gap-1">
        {children}
        {sortable && sorted && (
          <svg
            className={cn('w-4 h-4 transition-transform', sortDirection === 'desc' && 'rotate-180')}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          </svg>
        )}
      </div>
    </th>
  )
}

export function TableCell({ children, className }) {
  return (
    <td className={cn('px-6 py-4 text-sm text-gray-900 dark:text-gray-100', className)}>
      {children}
    </td>
  )
}

// Loading state for table
export function TableSkeleton({ rows = 5, columns = 4 }) {
  return (
    <Table>
      <TableHead>
        <TableRow>
          {Array.from({ length: columns }).map((_, i) => (
            <TableHeader key={i}>
              <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
            </TableHeader>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <TableRow key={rowIndex}>
            {Array.from({ length: columns }).map((_, colIndex) => (
              <TableCell key={colIndex}>
                <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

// Data Table with built-in loading and empty states
export function DataTable({
  columns,
  data,
  loading = false,
  emptyTitle = 'No data',
  emptyDescription = 'No records found',
  emptyAction,
  onRowClick,
  className,
}) {
  if (loading) {
    return <TableSkeleton rows={5} columns={columns.length} />
  }

  if (!data || data.length === 0) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        action={emptyAction}
      />
    )
  }

  return (
    <Table className={className}>
      <TableHead>
        <TableRow>
          {columns.map((column) => (
            <TableHeader key={column.key} className={column.headerClassName}>
              {column.title}
            </TableHeader>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {data.map((row, rowIndex) => (
          <TableRow
            key={row.id || rowIndex}
            clickable={!!onRowClick}
            onClick={() => onRowClick?.(row)}
          >
            {columns.map((column) => (
              <TableCell key={column.key} className={column.cellClassName}>
                {column.render ? column.render(row[column.key], row) : row[column.key]}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export default Table