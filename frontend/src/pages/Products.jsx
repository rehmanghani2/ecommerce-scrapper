import React, { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  CubeIcon,
  Squares2X2Icon,
  TableCellsIcon,
  ArrowDownTrayIcon,
} from '@heroicons/react/24/outline'
import { cn, formatNumber } from '@/utils/helpers'
import {
  Button,
  Card,
  Pagination,
  EmptyState,
  PageLoader,
  Modal,
  ModalFooter,
} from '@/components/Common'
import { ProductCard, ProductRow, ProductFilters, ExportButton } from '@/components/DataViewer'
import { apiGet } from '@/services/api'

export default function Products() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState('grid')
  const [selectedProduct, setSelectedProduct] = useState(null)

  // Parse filters from URL
  const filters = {
    search: searchParams.get('search') || '',
    category: searchParams.get('category') || '',
    brand: searchParams.get('brand') || '',
    min_price: searchParams.get('min_price') || '',
    max_price: searchParams.get('max_price') || '',
    in_stock: searchParams.get('in_stock') || '',
    domain: searchParams.get('domain') || '',
  }
  const page = parseInt(searchParams.get('page') || '1', 10)
  const pageSize = viewMode === 'grid' ? 12 : 20

  // Filter out empty strings before sending to API
  const activeFilters = Object.fromEntries(
    Object.entries(filters).filter(([_, v]) => v !== '')
  )

  // Fetch products
  const { data, isLoading, error } = useQuery({
    queryKey: ['products', activeFilters, page, pageSize],
    queryFn: () => apiGet('/products', { ...activeFilters, page, page_size: pageSize }),
  })

  // Fetch filter options (categories, brands)
  const { data: filterOptions } = useQuery({
    queryKey: ['productFilterOptions'],
    queryFn: () => apiGet('/products/filter-options'),
  })

  const products = data?.products || []
  const totalProducts = data?.total || 0
  const totalPages = data?.pages || 1

  const handleFilterChange = (newFilters) => {
    const params = new URLSearchParams()
    Object.entries(newFilters).forEach(([key, value]) => {
      if (value) params.set(key, value)
    })
    params.set('page', '1')
    setSearchParams(params)
  }

  const handleClearFilters = () => {
    setSearchParams({})
  }

  const handlePageChange = (newPage) => {
    const params = new URLSearchParams(searchParams)
    params.set('page', newPage.toString())
    setSearchParams(params)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <CubeIcon className="w-8 h-8 text-primary-600" />
            Products
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            {formatNumber(totalProducts)} products scraped
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* View toggle */}
          <div className="flex items-center bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={cn(
                'p-2 rounded-md transition-colors',
                viewMode === 'grid'
                  ? 'bg-white dark:bg-gray-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              <Squares2X2Icon className="w-5 h-5" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={cn(
                'p-2 rounded-md transition-colors',
                viewMode === 'table'
                  ? 'bg-white dark:bg-gray-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              <TableCellsIcon className="w-5 h-5" />
            </button>
          </div>
          
          <Button icon={ArrowDownTrayIcon} variant="secondary">
            Export All
          </Button>
        </div>
      </div>

      {/* Filters */}
      <ProductFilters
        filters={filters}
        onChange={handleFilterChange}
        onClear={handleClearFilters}
        categories={filterOptions?.categories || []}
        brands={filterOptions?.brands || []}
      />

      {/* Products */}
      {isLoading ? (
        <PageLoader message="Loading products..." />
      ) : products.length === 0 ? (
        <EmptyState
          icon={CubeIcon}
          title="No products found"
          description={
            Object.values(filters).some(Boolean)
              ? "No products match your current filters."
              : "No products have been scraped yet. Start a scraping job to collect products."
          }
          action={
            Object.values(filters).some(Boolean) && (
              <Button variant="secondary" onClick={handleClearFilters}>
                Clear Filters
              </Button>
            )
          }
        />
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              onClick={() => setSelectedProduct(product)}
            />
          ))}
        </div>
      ) : (
        <Card padding="none" className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Image
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Product
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Brand
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Category
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Price
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Stock
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Link
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {products.map((product) => (
                  <ProductRow
                    key={product.id}
                    product={product}
                    onClick={() => setSelectedProduct(product)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center">
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={handlePageChange}
          />
        </div>
      )}

      {/* Product Detail Modal */}
      <ProductDetailModal
        product={selectedProduct}
        isOpen={!!selectedProduct}
        onClose={() => setSelectedProduct(null)}
      />
    </div>
  )
}

function ProductDetailModal({ product, isOpen, onClose }) {
  if (!product) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={product.name}
      size="lg"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Image */}
        <div className="aspect-square bg-gray-100 dark:bg-gray-800 rounded-lg overflow-hidden">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <CubeIcon className="w-16 h-16 text-gray-400" />
            </div>
          )}
        </div>

        {/* Details */}
        <div className="space-y-4">
          {product.brand && (
            <p className="text-sm font-medium text-primary-600 dark:text-primary-400">
              {product.brand}
            </p>
          )}
          
          <div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {product.price ? `£${product.price}` : 'Price not available'}
            </p>
            {product.original_price && product.original_price > product.price && (
              <p className="text-sm text-gray-500 line-through">
                £{product.original_price}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <span className={cn(
              'px-2 py-1 text-sm font-medium rounded',
              product.in_stock
                ? 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400'
                : 'bg-danger-100 text-danger-700 dark:bg-danger-900/30 dark:text-danger-400'
            )}>
              {product.in_stock ? 'In Stock' : 'Out of Stock'}
            </span>
          </div>

          {product.description && (
            <div>
              <h4 className="font-medium text-gray-900 dark:text-white mb-1">Description</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-4">
                {product.description}
              </p>
            </div>
          )}

          {product.category && (
            <div>
              <h4 className="font-medium text-gray-900 dark:text-white mb-1">Category</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {product.category_path || product.category}
              </p>
            </div>
          )}

          {product.sku && (
            <div>
              <h4 className="font-medium text-gray-900 dark:text-white mb-1">SKU</h4>
              <p className="text-sm font-mono text-gray-600 dark:text-gray-400">
                {product.sku}
              </p>
            </div>
          )}
        </div>
      </div>

      <ModalFooter>
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        <a href={product.url} target="_blank" rel="noopener noreferrer">
          <Button>View on Website</Button>
        </a>
      </ModalFooter>
    </Modal>
  )
}