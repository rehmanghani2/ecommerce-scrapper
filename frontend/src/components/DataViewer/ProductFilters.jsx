import React from 'react'
import {
  MagnifyingGlassIcon,
  AdjustmentsHorizontalIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'
import { Input, Select, Button, Badge, Card } from '@/components/Common'

export function ProductFilters({
  filters,
  onChange,
  onClear,
  categories = [],
  brands = [],
  className,
}) {
  const hasFilters = Object.values(filters).some((v) => v !== '' && v !== null)

  const handleChange = (key, value) => {
    onChange({ ...filters, [key]: value })
  }

  return (
    <Card className={cn('p-4', className)}>
      <div className="flex flex-col lg:flex-row gap-4">
        {/* Search */}
        <div className="flex-1">
          <Input
            icon={MagnifyingGlassIcon}
            placeholder="Search products..."
            value={filters.search || ''}
            onChange={(e) => handleChange('search', e.target.value)}
          />
        </div>

        {/* Filters row */}
        <div className="flex flex-wrap gap-3">
          {/* Category */}
          <Select
            options={[
              { value: '', label: 'All Categories' },
              ...categories.map((c) => ({ value: c, label: c })),
            ]}
            value={filters.category || ''}
            onChange={(value) => handleChange('category', value)}
            className="w-40"
          />

          {/* Brand */}
          <Select
            options={[
              { value: '', label: 'All Brands' },
              ...brands.map((b) => ({ value: b, label: b })),
            ]}
            value={filters.brand || ''}
            onChange={(value) => handleChange('brand', value)}
            className="w-40"
          />

          {/* Price range */}
          <div className="flex items-center gap-2">
            <Input
              type="number"
              placeholder="Min"
              value={filters.min_price || ''}
              onChange={(e) => handleChange('min_price', e.target.value)}
              className="w-24"
            />
            <span className="text-gray-400">—</span>
            <Input
              type="number"
              placeholder="Max"
              value={filters.max_price || ''}
              onChange={(e) => handleChange('max_price', e.target.value)}
              className="w-24"
            />
          </div>

          {/* Stock filter */}
          <Select
            options={[
              { value: '', label: 'All Stock' },
              { value: 'true', label: 'In Stock' },
              { value: 'false', label: 'Out of Stock' },
            ]}
            value={filters.in_stock ?? ''}
            onChange={(value) => handleChange('in_stock', value)}
            className="w-32"
          />

          {/* Clear button */}
          {hasFilters && (
            <Button variant="ghost" icon={XMarkIcon} onClick={onClear}>
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* Active filters display */}
      {hasFilters && (
        <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t dark:border-gray-700">
          <AdjustmentsHorizontalIcon className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-500">Filters:</span>
          
          {filters.search && (
            <Badge removable onRemove={() => handleChange('search', '')}>
              Search: {filters.search}
            </Badge>
          )}
          {filters.category && (
            <Badge removable onRemove={() => handleChange('category', '')}>
              Category: {filters.category}
            </Badge>
          )}
          {filters.brand && (
            <Badge removable onRemove={() => handleChange('brand', '')}>
              Brand: {filters.brand}
            </Badge>
          )}
          {(filters.min_price || filters.max_price) && (
            <Badge
              removable
              onRemove={() => {
                handleChange('min_price', '')
                handleChange('max_price', '')
              }}
            >
              Price: {filters.min_price || '0'} - {filters.max_price || '∞'}
            </Badge>
          )}
          {filters.in_stock && (
            <Badge removable onRemove={() => handleChange('in_stock', '')}>
              {filters.in_stock === 'true' ? 'In Stock' : 'Out of Stock'}
            </Badge>
          )}
        </div>
      )}
    </Card>
  )
}

export default ProductFilters