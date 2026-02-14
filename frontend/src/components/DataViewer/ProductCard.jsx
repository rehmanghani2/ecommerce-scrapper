import React from 'react'
import {
  CurrencyPoundIcon,
  TagIcon,
  ArrowTopRightOnSquareIcon,
  CheckIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { cn, formatPrice, truncate } from '@/utils/helpers'
import { Card, Badge } from '@/components/Common'

export function ProductCard({ product, onClick }) {
  return (
    <Card
      hover
      padding="none"
      className="overflow-hidden cursor-pointer"
      onClick={onClick}
    >
      {/* Image */}
      <div className="aspect-square bg-gray-100 dark:bg-gray-800 relative overflow-hidden">
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
            onError={(e) => {
              e.target.style.display = 'none'
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <CubeIcon className="w-12 h-12" />
          </div>
        )}
        
        {/* Stock badge */}
        <div className="absolute top-2 right-2">
          <Badge variant={product.in_stock ? 'success' : 'danger'} size="sm">
            {product.in_stock ? 'In Stock' : 'Out of Stock'}
          </Badge>
        </div>
      </div>
      
      {/* Content */}
      <div className="p-4">
        {/* Brand */}
        {product.brand && (
          <p className="text-xs font-medium text-primary-600 dark:text-primary-400 uppercase tracking-wide mb-1">
            {product.brand}
          </p>
        )}
        
        {/* Name */}
        <h3 className="font-medium text-gray-900 dark:text-white line-clamp-2 mb-2">
          {product.name}
        </h3>
        
        {/* Price */}
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-gray-900 dark:text-white">
            {formatPrice(product.price, product.currency)}
          </span>
          
          {product.original_price && product.original_price > product.price && (
            <span className="text-sm text-gray-500 line-through">
              {formatPrice(product.original_price, product.currency)}
            </span>
          )}
        </div>
        
        {/* Category */}
        {product.category && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 truncate">
            {product.category_path || product.category}
          </p>
        )}
      </div>
    </Card>
  )
}

// Compact product row for tables
export function ProductRow({ product, onClick }) {
  return (
    <tr
      className="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
      onClick={onClick}
    >
      {/* Image */}
      <td className="px-4 py-3">
        <div className="w-12 h-12 rounded-lg bg-gray-100 dark:bg-gray-800 overflow-hidden">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400">
              <CubeIcon className="w-6 h-6" />
            </div>
          )}
        </div>
      </td>
      
      {/* Name & SKU */}
      <td className="px-4 py-3">
        <p className="font-medium text-gray-900 dark:text-white truncate max-w-xs">
          {product.name}
        </p>
        {product.sku && (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            SKU: {product.sku}
          </p>
        )}
      </td>
      
      {/* Brand */}
      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
        {product.brand || '—'}
      </td>
      
      {/* Category */}
      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 truncate max-w-xs">
        {product.category || '—'}
      </td>
      
      {/* Price */}
      <td className="px-4 py-3">
        <span className="font-medium text-gray-900 dark:text-white">
          {formatPrice(product.price, product.currency)}
        </span>
      </td>
      
      {/* Stock */}
      <td className="px-4 py-3">
        {product.in_stock ? (
          <CheckIcon className="w-5 h-5 text-success-500" />
        ) : (
          <XMarkIcon className="w-5 h-5 text-danger-500" />
        )}
      </td>
      
      {/* Link */}
      <td className="px-4 py-3">
        <a
          href={product.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-primary-600 hover:text-primary-700 dark:text-primary-400"
        >
          <ArrowTopRightOnSquareIcon className="w-5 h-5" />
        </a>
      </td>
    </tr>
  )
}

export default ProductCard