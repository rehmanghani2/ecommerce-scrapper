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

export function ProductCard({ product, onClick, selected = false, onToggleSelect = null }) {
  return (
    <Card
      hover
      padding="none"
      className={cn(
        "overflow-hidden cursor-pointer relative",
        selected && "ring-2 ring-primary-500 bg-primary-50/10 dark:bg-primary-950/20"
      )}
      onClick={onClick}
    >
      {/* Select checkbox badge */}
      {onToggleSelect && (
        <div
          className="absolute top-2 left-2 z-10 bg-white/90 dark:bg-gray-900/90 rounded p-1 shadow-sm"
          onClick={(e) => {
            e.stopPropagation()
            onToggleSelect(product.id)
          }}
        >
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggleSelect(product.id)}
            className="rounded border-gray-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
          />
        </div>
      )}

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
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-lg font-bold text-gray-900 dark:text-white">
            {formatPrice(product.price, product.currency)}
          </span>
          
          {product.original_price && product.original_price > product.price && (
            <span className="text-sm text-gray-500 line-through">
              {formatPrice(product.original_price, product.currency)}
            </span>
          )}

          {product.price_change < 0 && (
            <span className="inline-flex items-center text-xs font-semibold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400">
              ↓ {Math.abs(product.price_change_percentage || 0)}%
            </span>
          )}

          {product.price_change > 0 && (
            <span className="inline-flex items-center text-xs font-semibold px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400">
              ↑ +{product.price_change_percentage}%
            </span>
          )}
        </div>
        
          {/* Category & Variants count */}
          <div className="flex items-center justify-between gap-2 mt-2">
            {product.category ? (
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {product.category_path || product.category}
              </p>
            ) : <span />}
            {product.variants && product.variants.length > 0 && (
              <span className="shrink-0 text-[11px] font-medium px-1.5 py-0.5 rounded bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                {product.variants.length} vars
              </span>
            )}
          </div>
        </div>
      </Card>
  )
}

// Compact product row for tables
export function ProductRow({ product, onClick, selected = false, onToggleSelect = null }) {
  return (
    <tr
      className={cn(
        "hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors",
        selected && "bg-primary-50/40 dark:bg-primary-950/30"
      )}
      onClick={onClick}
    >
      {/* Checkbox */}
      {onToggleSelect && (
        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggleSelect(product.id)}
            className="rounded border-gray-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
          />
        </td>
      )}

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
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="font-medium text-gray-900 dark:text-white">
            {formatPrice(product.price, product.currency)}
          </span>
          {product.price_change < 0 && (
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400">
              ↓ {Math.abs(product.price_change_percentage || 0)}%
            </span>
          )}
          {product.price_change > 0 && (
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400">
              ↑ +{product.price_change_percentage}%
            </span>
          )}
        </div>
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