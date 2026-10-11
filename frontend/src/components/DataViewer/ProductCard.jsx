import React from 'react'
import {
  CubeIcon,
  ArrowTopRightOnSquareIcon,
  CheckIcon,
  XMarkIcon,
  ChartBarIcon,
  CalculatorIcon,
  BoltIcon,
  ChatBubbleBottomCenterTextIcon,
  TrophyIcon,
  TicketIcon,
} from '@heroicons/react/24/outline'
import { cn, formatPrice } from '@/utils/helpers'
import { Card, Badge } from '@/components/Common'

export function ProductCard({
  product,
  onClick,
  selected = false,
  onToggleSelect = null,
  onViewCluster = null,
  onOpenHistory = null,
  onOpenSimulator = null,
  onOpenForecast = null,
  onOpenSentiment = null,
  onOpenBuyBox = null,
  onOpenPromotions = null,
}) {
  return (
    <Card
      hover
      padding="none"
      className={cn(
        'group overflow-hidden cursor-pointer relative flex flex-col justify-between transition-all duration-200 border border-gray-200/80 dark:border-gray-800 hover:border-primary-400/60 dark:hover:border-primary-500/50 hover:shadow-lg',
        selected && 'ring-2 ring-primary-500 bg-primary-50/10 dark:bg-primary-950/20'
      )}
      onClick={onClick}
    >
      <div>
        {/* Select checkbox badge */}
        {onToggleSelect && (
          <div
            className="absolute top-2.5 left-2.5 z-10 bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm rounded-md p-1 shadow-sm border border-gray-200/60 dark:border-gray-700"
            onClick={(e) => {
              e.stopPropagation()
              onToggleSelect(product.id)
            }}
          >
            <input
              type="checkbox"
              checked={selected}
              onChange={() => onToggleSelect(product.id)}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500 cursor-pointer block"
            />
          </div>
        )}

        {/* Image */}
        <div className="aspect-square bg-gray-100 dark:bg-gray-800/80 relative overflow-hidden">
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
            <div className="w-full h-full flex flex-col items-center justify-center text-gray-400 dark:text-gray-600 gap-1">
              <CubeIcon className="w-12 h-12 stroke-1" />
              <span className="text-[11px]">No Image</span>
            </div>
          )}

          {/* Stock badge */}
          <div className="absolute top-2.5 right-2.5 flex flex-col items-end gap-1">
            <Badge variant={product.in_stock ? 'success' : 'danger'} size="sm">
              {product.in_stock ? 'In Stock' : 'Out of Stock'}
            </Badge>
            {product.source_domain && (
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-gray-900/75 text-white backdrop-blur-sm max-w-[130px] truncate">
                {product.source_domain.replace(/^www\./, '')}
              </span>
            )}
          </div>

          {/* Price change floating pill */}
          {product.price_change < 0 && (
            <div className="absolute bottom-2 left-2">
              <span className="inline-flex items-center gap-0.5 text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-600 text-white shadow-sm">
                ↓ {Math.abs(product.price_change_percentage || 0)}% Drop
              </span>
            </div>
          )}
          {product.price_change > 0 && (
            <div className="absolute bottom-2 left-2">
              <span className="inline-flex items-center gap-0.5 text-xs font-bold px-2 py-0.5 rounded-full bg-rose-600 text-white shadow-sm">
                ↑ +{product.price_change_percentage}%
              </span>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-4 pb-3">
          {/* Brand & Category */}
          <div className="flex items-center justify-between gap-2 mb-1">
            {product.brand ? (
              <p className="text-xs font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-wider truncate">
                {product.brand}
              </p>
            ) : (
              <span className="text-xs text-gray-400 dark:text-gray-500 truncate">
                {product.category || 'Catalog Item'}
              </span>
            )}
            {product.variants && product.variants.length > 0 && (
              <span className="shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                {product.variants.length} variants
              </span>
            )}
          </div>

          {/* Name */}
          <h3 className="font-medium text-gray-900 dark:text-white line-clamp-2 mb-2.5 text-sm leading-snug min-h-[2.5rem]">
            {product.name}
          </h3>

          {/* Price */}
          <div className="flex items-baseline justify-between gap-2 flex-wrap">
            <div className="flex items-baseline gap-1.5 flex-wrap">
              <span className="text-lg font-bold text-gray-900 dark:text-white">
                {formatPrice(product.price, product.currency)}
              </span>

              {product.original_price && product.original_price > product.price && (
                <span className="text-xs text-gray-400 line-through">
                  {formatPrice(product.original_price, product.currency)}
                </span>
              )}

              {product.normalized_price &&
                product.normalized_currency &&
                product.normalized_currency !== product.currency && (
                  <span className="text-[11px] font-medium px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400">
                    ≈ {product.normalized_currency} {product.normalized_price}
                  </span>
                )}
            </div>

            {product.match_cluster_id && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  if (onViewCluster) onViewCluster(product.match_cluster_id)
                }}
                className="shrink-0 inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-indigo-100 hover:bg-indigo-200 text-indigo-800 dark:bg-indigo-950/60 dark:hover:bg-indigo-900/80 dark:text-indigo-300 transition-colors"
                title="View cross-store competitor prices"
              >
                ⚡ Competitors
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Quick Intelligence Bar */}
      {(onOpenHistory || onOpenSimulator || onOpenForecast || onOpenSentiment || onOpenBuyBox || onOpenPromotions) && (
        <div
          className="px-3 py-2 bg-gray-50/80 dark:bg-gray-800/50 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between gap-1"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center gap-1">
            {onOpenHistory && (
              <button
                type="button"
                onClick={() => onOpenHistory(product)}
                title="Price History & Trends"
                className="p-1.5 rounded-md text-gray-500 hover:text-primary-600 hover:bg-white dark:text-gray-400 dark:hover:text-primary-400 dark:hover:bg-gray-700 transition-colors"
              >
                <ChartBarIcon className="w-4 h-4" />
              </button>
            )}
            {onOpenSimulator && (
              <button
                type="button"
                onClick={() => onOpenSimulator(product)}
                title="AI Pricing Simulator"
                className="p-1.5 rounded-md text-gray-500 hover:text-indigo-600 hover:bg-white dark:text-gray-400 dark:hover:text-indigo-400 dark:hover:bg-gray-700 transition-colors"
              >
                <CalculatorIcon className="w-4 h-4" />
              </button>
            )}
            {onOpenForecast && (
              <button
                type="button"
                onClick={() => onOpenForecast(product)}
                title="Stock Velocity & Depletion Forecast"
                className="p-1.5 rounded-md text-gray-500 hover:text-amber-600 hover:bg-white dark:text-gray-400 dark:hover:text-amber-400 dark:hover:bg-gray-700 transition-colors"
              >
                <BoltIcon className="w-4 h-4" />
              </button>
            )}
            {onOpenSentiment && (
              <button
                type="button"
                onClick={() => onOpenSentiment(product)}
                title="Customer Reviews & AI Sentiment"
                className="p-1.5 rounded-md text-gray-500 hover:text-purple-600 hover:bg-white dark:text-gray-400 dark:hover:text-purple-400 dark:hover:bg-gray-700 transition-colors"
              >
                <ChatBubbleBottomCenterTextIcon className="w-4 h-4" />
              </button>
            )}
            {onOpenBuyBox && (
              <button
                type="button"
                onClick={() => onOpenBuyBox(product)}
                title="Buy Box Win/Loss Intelligence"
                className="p-1.5 rounded-md text-gray-500 hover:text-amber-500 hover:bg-white dark:text-gray-400 dark:hover:text-amber-300 dark:hover:bg-gray-700 transition-colors"
              >
                <TrophyIcon className="w-4 h-4" />
              </button>
            )}
            {onOpenPromotions && (
              <button
                type="button"
                onClick={() => onOpenPromotions(product)}
                title="Coupons & Promotions"
                className="p-1.5 rounded-md text-gray-500 hover:text-emerald-600 hover:bg-white dark:text-gray-400 dark:hover:text-emerald-400 dark:hover:bg-gray-700 transition-colors"
              >
                <TicketIcon className="w-4 h-4" />
              </button>
            )}
          </div>

          <a
            href={product.url}
            target="_blank"
            rel="noopener noreferrer"
            title="Open original product URL"
            className="p-1.5 rounded-md text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
          >
            <ArrowTopRightOnSquareIcon className="w-4 h-4" />
          </a>
        </div>
      )}
    </Card>
  )
}

// Compact product row for tables
export function ProductRow({
  product,
  onClick,
  selected = false,
  onToggleSelect = null,
  onViewCluster = null,
  onOpenHistory = null,
  onOpenSimulator = null,
  onOpenForecast = null,
}) {
  return (
    <tr
      className={cn(
        'hover:bg-gray-50 dark:hover:bg-gray-800/70 cursor-pointer transition-colors',
        selected && 'bg-primary-50/40 dark:bg-primary-950/30'
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
        <div className="w-12 h-12 rounded-lg bg-gray-100 dark:bg-gray-800 overflow-hidden border border-gray-200/60 dark:border-gray-700">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="w-full h-full object-cover"
              onError={(e) => {
                e.target.style.display = 'none'
              }}
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
        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
          {product.source_domain && (
            <span className="text-[11px] text-gray-400 dark:text-gray-500">
              {product.source_domain.replace(/^www\./, '')}
            </span>
          )}
          {product.sku && (
            <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
              SKU: {product.sku}
            </span>
          )}
          {product.match_cluster_id && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                if (onViewCluster) onViewCluster(product.match_cluster_id)
              }}
              className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-100 hover:bg-indigo-200 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-400 transition-colors"
              title="View cross-store competitor prices"
            >
              ⚡ Competitors
            </button>
          )}
        </div>
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
          <span className="font-semibold text-gray-900 dark:text-white">
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
          <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
            <CheckIcon className="w-4 h-4" /> In Stock
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-600 dark:text-rose-400">
            <XMarkIcon className="w-4 h-4" /> Out
          </span>
        )}
      </td>

      {/* Quick Actions & Link */}
      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-1">
          {onOpenHistory && (
            <button
              type="button"
              onClick={() => onOpenHistory(product)}
              title="Price History"
              className="p-1.5 rounded text-gray-400 hover:text-primary-600 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <ChartBarIcon className="w-4 h-4" />
            </button>
          )}
          {onOpenSimulator && (
            <button
              type="button"
              onClick={() => onOpenSimulator(product)}
              title="AI Pricing Simulator"
              className="p-1.5 rounded text-gray-400 hover:text-indigo-600 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <CalculatorIcon className="w-4 h-4" />
            </button>
          )}
          {onOpenForecast && (
            <button
              type="button"
              onClick={() => onOpenForecast(product)}
              title="Stock Velocity Forecast"
              className="p-1.5 rounded text-gray-400 hover:text-amber-600 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <BoltIcon className="w-4 h-4" />
            </button>
          )}
          <a
            href={product.url}
            target="_blank"
            rel="noopener noreferrer"
            title="Visit Store Page"
            className="p-1.5 rounded text-primary-600 hover:text-primary-700 dark:text-primary-400 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <ArrowTopRightOnSquareIcon className="w-4 h-4" />
          </a>
        </div>
      </td>
    </tr>
  )
}

export default ProductCard