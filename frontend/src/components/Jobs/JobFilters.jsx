import React from 'react'
import { MagnifyingGlassIcon, FunnelIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'
import { Input, Select, Button, Badge } from '@/components/Common'
import { JOB_STATUS } from '@/utils/constants'

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'running', label: 'Running' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' },
]

export function JobFilters({
  filters,
  onChange,
  onClear,
  className,
}) {
  const hasFilters = filters.search || filters.status || filters.domain

  const handleChange = (key, value) => {
    onChange({ ...filters, [key]: value })
  }

  const activeFilterCount = [
    filters.search,
    filters.status,
    filters.domain,
  ].filter(Boolean).length

  return (
    <div className={cn('space-y-4', className)}>
      {/* Search and main filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <Input
            icon={MagnifyingGlassIcon}
            placeholder="Search jobs..."
            value={filters.search || ''}
            onChange={(e) => handleChange('search', e.target.value)}
          />
        </div>
        
        <div className="flex gap-3">
          <Select
            options={STATUS_OPTIONS}
            value={filters.status || ''}
            onChange={(value) => handleChange('status', value)}
            className="w-40"
          />
          
          <Input
            placeholder="Domain"
            value={filters.domain || ''}
            onChange={(e) => handleChange('domain', e.target.value)}
            className="w-40"
          />
          
          {hasFilters && (
            <Button
              variant="ghost"
              icon={XMarkIcon}
              onClick={onClear}
            >
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* Active filters */}
      {activeFilterCount > 0 && (
        <div className="flex items-center gap-2">
          <FunnelIcon className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-500">Active filters:</span>
          
          {filters.search && (
            <Badge
              variant="primary"
              removable
              onRemove={() => handleChange('search', '')}
            >
              Search: {filters.search}
            </Badge>
          )}
          
          {filters.status && (
            <Badge
              variant="primary"
              removable
              onRemove={() => handleChange('status', '')}
            >
              Status: {filters.status}
            </Badge>
          )}
          
          {filters.domain && (
            <Badge
              variant="primary"
              removable
              onRemove={() => handleChange('domain', '')}
            >
              Domain: {filters.domain}
            </Badge>
          )}
        </div>
      )}
    </div>
  )
}

export default JobFilters