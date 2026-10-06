import React, { useState, useEffect } from 'react'
import {
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  PlusCircleIcon,
  MinusCircleIcon,
  ArrowsRightLeftIcon,
  ArrowDownTrayIcon,
  CubeIcon,
  ArrowTopRightOnSquareIcon,
  MagnifyingGlassIcon,
  ClockIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import { Button, Spinner, Badge, Card } from '@/components/Common'
import { formatPrice, formatDate, cn } from '@/utils/helpers'
import diffService from '@/services/diffService'

export function CatalogDiffViewer({ jobId, initialDiff = null }) {
  const [loading, setLoading] = useState(false)
  const [diffData, setDiffData] = useState(initialDiff)
  const [error, setError] = useState(null)
  const [filterType, setFilterType] = useState('all') // 'all', 'added', 'removed', 'price_down', 'price_up', 'stock'
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!initialDiff && jobId) {
      loadDiff()
    }
  }, [jobId, initialDiff])

  const loadDiff = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await diffService.compareWithPrevious(jobId)
      if (res?.diff) {
        setDiffData(res.diff)
      } else {
        setError('No previous crawl available to compare.')
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || 'Failed to calculate catalog diff'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="py-16 flex flex-col items-center justify-center gap-3">
        <Spinner size="lg" />
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Calculating catalog differential intelligence against prior crawl...
        </p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8 text-center bg-gray-50 dark:bg-gray-850 rounded-xl border border-dashed border-gray-300 dark:border-gray-700">
        <ClockIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">
          Initial Baseline Crawl
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-md mx-auto">
          {error.includes('No previous crawl')
            ? 'This is the first recorded scraping job for this store domain. Differential change reports (added items, delistings, price shifts) will automatically populate on subsequent crawls.'
            : error}
        </p>
      </div>
    )
  }

  if (!diffData) return null

  const summary = diffData.summary || {}
  const added = diffData.added_products || []
  const removed = diffData.removed_products || []
  const priceChanges = diffData.price_changes || []
  const stockChanges = diffData.stock_changes || []

  // Combine changes for unified list
  const priceDown = priceChanges.filter((p) => p.direction === 'decreased')
  const priceUp = priceChanges.filter((p) => p.direction === 'increased')

  // Filtered items
  let displayItems = []
  if (filterType === 'all') {
    displayItems = [
      ...added.map((x) => ({ ...x, _category: 'added' })),
      ...removed.map((x) => ({ ...x, _category: 'removed' })),
      ...priceDown.map((x) => ({ ...x, _category: 'price_down' })),
      ...priceUp.map((x) => ({ ...x, _category: 'price_up' })),
      ...stockChanges.map((x) => ({ ...x, _category: 'stock' })),
    ]
  } else if (filterType === 'added') {
    displayItems = added.map((x) => ({ ...x, _category: 'added' }))
  } else if (filterType === 'removed') {
    displayItems = removed.map((x) => ({ ...x, _category: 'removed' }))
  } else if (filterType === 'price_down') {
    displayItems = priceDown.map((x) => ({ ...x, _category: 'price_down' }))
  } else if (filterType === 'price_up') {
    displayItems = priceUp.map((x) => ({ ...x, _category: 'price_up' }))
  } else if (filterType === 'stock') {
    displayItems = stockChanges.map((x) => ({ ...x, _category: 'stock' }))
  }

  if (search.trim()) {
    const q = search.toLowerCase()
    displayItems = displayItems.filter(
      (item) =>
        (item.name && item.name.toLowerCase().includes(q)) ||
        (item.sku && item.sku.toLowerCase().includes(q))
    )
  }

  const handleExportCsv = async () => {
    if (!summary?.job_a?.id || !summary?.job_b?.id) return
    try {
      await diffService.downloadDiffCsv(summary.job_a.id, summary.job_b.id)
    } catch (err) {
      alert('Failed to download CSV: ' + (err.message || 'Error'))
    }
  }

  return (
    <div className="space-y-6">
      {/* Crawl comparison header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-primary-600 dark:text-primary-400">
            Catalog Intelligence Comparison
          </span>
          <div className="flex items-center gap-2 mt-1 text-sm text-gray-900 dark:text-gray-100 flex-wrap">
            <span className="font-semibold">{summary?.domain || 'Competitor Store'}</span>
            <span className="text-gray-400">•</span>
            <span className="text-gray-600 dark:text-gray-300">
              Baseline: #{summary?.job_a?.id} ({formatDate(summary?.job_a?.created_at, 'PPp')})
            </span>
            <span className="text-gray-400">➔</span>
            <span className="text-gray-600 dark:text-gray-300 font-medium">
              Current: #{summary?.job_b?.id} ({formatDate(summary?.job_b?.created_at, 'PPp')})
            </span>
          </div>
        </div>

        {summary?.job_a?.id && summary?.job_b?.id && (
          <Button
            icon={ArrowDownTrayIcon}
            variant="outline"
            size="sm"
            onClick={handleExportCsv}
            className="shrink-0"
          >
            Export Diff (CSV)
          </Button>
        )}
      </div>

      {/* KPI metric cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Added */}
        <div
          onClick={() => setFilterType('added')}
          className={cn(
            'p-3 rounded-xl border cursor-pointer transition-all',
            filterType === 'added'
              ? 'ring-2 ring-emerald-500 bg-emerald-50/60 dark:bg-emerald-950/40 border-emerald-300'
              : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-emerald-300'
          )}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">New Items</span>
            <PlusCircleIcon className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
            +{summary.added_count || 0}
          </p>
        </div>

        {/* Removed */}
        <div
          onClick={() => setFilterType('removed')}
          className={cn(
            'p-3 rounded-xl border cursor-pointer transition-all',
            filterType === 'removed'
              ? 'ring-2 ring-rose-500 bg-rose-50/60 dark:bg-rose-950/40 border-rose-300'
              : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-rose-300'
          )}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Delisted</span>
            <MinusCircleIcon className="w-4 h-4 text-rose-600 dark:text-rose-400" />
          </div>
          <p className="text-xl font-bold text-rose-600 dark:text-rose-400 mt-1">
            -{summary.removed_count || 0}
          </p>
        </div>

        {/* Price Drops */}
        <div
          onClick={() => setFilterType('price_down')}
          className={cn(
            'p-3 rounded-xl border cursor-pointer transition-all',
            filterType === 'price_down'
              ? 'ring-2 ring-emerald-500 bg-emerald-50/60 dark:bg-emerald-950/40 border-emerald-300'
              : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-emerald-300'
          )}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Price Drops</span>
            <ArrowTrendingDownIcon className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
            ↓ {summary.price_decreased_count || 0}
          </p>
        </div>

        {/* Price Increases */}
        <div
          onClick={() => setFilterType('price_up')}
          className={cn(
            'p-3 rounded-xl border cursor-pointer transition-all',
            filterType === 'price_up'
              ? 'ring-2 ring-amber-500 bg-amber-50/60 dark:bg-amber-950/40 border-amber-300'
              : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-amber-300'
          )}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Price Increases</span>
            <ArrowTrendingUpIcon className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>
          <p className="text-xl font-bold text-amber-600 dark:text-amber-400 mt-1">
            ↑ {summary.price_increased_count || 0}
          </p>
        </div>

        {/* Stock Changes */}
        <div
          onClick={() => setFilterType('stock')}
          className={cn(
            'p-3 rounded-xl border cursor-pointer transition-all',
            filterType === 'stock'
              ? 'ring-2 ring-indigo-500 bg-indigo-50/60 dark:bg-indigo-950/40 border-indigo-300'
              : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-indigo-300'
          )}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Stock Shifts</span>
            <ArrowsRightLeftIcon className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          </div>
          <p className="text-xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">
            ⚡ {summary.stock_changed_count || 0}
          </p>
        </div>

        {/* Net Growth */}
        <div className="p-3 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Net Catalog</span>
          <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">
            {summary.net_catalog_growth > 0 ? `+${summary.net_catalog_growth}` : summary.net_catalog_growth || 0}
          </p>
        </div>
      </div>

      {/* Filter tabs and search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            type="button"
            onClick={() => setFilterType('all')}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
              filterType === 'all'
                ? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900'
                : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-200'
            )}
          >
            All Changes ({added.length + removed.length + priceChanges.length + stockChanges.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterType('added')}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
              filterType === 'added'
                ? 'bg-emerald-600 text-white'
                : 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400 hover:bg-emerald-100'
            )}
          >
            Added (+{added.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterType('removed')}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
              filterType === 'removed'
                ? 'bg-rose-600 text-white'
                : 'bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-400 hover:bg-rose-100'
            )}
          >
            Delisted (-{removed.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterType('price_down')}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
              filterType === 'price_down'
                ? 'bg-emerald-600 text-white'
                : 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400 hover:bg-emerald-100'
            )}
          >
            Price Drops (↓{priceDown.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterType('price_up')}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
              filterType === 'price_up'
                ? 'bg-amber-600 text-white'
                : 'bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-400 hover:bg-amber-100'
            )}
          >
            Price Increases (↑{priceUp.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterType('stock')}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
              filterType === 'stock'
                ? 'bg-indigo-600 text-white'
                : 'bg-indigo-50 text-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-400 hover:bg-indigo-100'
            )}
          >
            Stock Shifts ({stockChanges.length})
          </button>
        </div>

        <div className="relative w-full sm:w-64">
          <MagnifyingGlassIcon className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search changed products..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:ring-1 focus:ring-primary-500 outline-none"
          />
        </div>
      </div>

      {/* Differential change table */}
      <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        {displayItems.length === 0 ? (
          <div className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
            No changes found matching the current filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Change Type</th>
                  <th className="px-4 py-3 text-left">Product</th>
                  <th className="px-4 py-3 text-right">Price Shift</th>
                  <th className="px-4 py-3 text-center">Stock</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {displayItems.map((item, idx) => {
                  return (
                    <tr
                      key={item.id || idx}
                      className="hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors"
                    >
                      {/* Change badge */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        {item._category === 'added' && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                            + NEW ADDITION
                          </span>
                        )}
                        {item._category === 'removed' && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-200 dark:border-rose-800">
                            - DELISTED
                          </span>
                        )}
                        {item._category === 'price_down' && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                            ↓ PRICE DROP
                          </span>
                        )}
                        {item._category === 'price_up' && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
                            ↑ PRICE INCREASE
                          </span>
                        )}
                        {item._category === 'stock' && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
                            ⚡ {item.status === 'back_in_stock' ? 'BACK IN STOCK' : 'OUT OF STOCK'}
                          </span>
                        )}
                      </td>

                      {/* Product Name & SKU */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          {item.image_url ? (
                            <img
                              src={item.image_url}
                              alt={item.name}
                              className="w-10 h-10 rounded object-cover shrink-0 border border-gray-200 dark:border-gray-700"
                            />
                          ) : (
                            <div className="w-10 h-10 rounded bg-gray-100 dark:bg-gray-800 flex items-center justify-center shrink-0">
                              <CubeIcon className="w-5 h-5 text-gray-400" />
                            </div>
                          )}
                          <div className="min-w-0 max-w-sm">
                            <p className="font-medium text-gray-900 dark:text-white truncate" title={item.name}>
                              {item.name}
                            </p>
                            <div className="flex items-center gap-2 text-xs text-gray-500 font-mono mt-0.5">
                              {item.brand && <span>{item.brand}</span>}
                              {item.sku && <span>SKU: {item.sku}</span>}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Price Shift */}
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        {item._category === 'price_down' || item._category === 'price_up' ? (
                          <div>
                            <div className="flex items-center justify-end gap-1.5 text-xs text-gray-400">
                              <span className="line-through">{formatPrice(item.old_price, item.currency)}</span>
                              <span>➔</span>
                              <span className="font-bold text-gray-900 dark:text-white text-sm">
                                {formatPrice(item.new_price, item.currency)}
                              </span>
                            </div>
                            <span
                              className={cn(
                                'text-[11px] font-bold px-1.5 py-0.2 rounded inline-block mt-0.5',
                                item.direction === 'decreased'
                                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400'
                                  : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400'
                              )}
                            >
                              {item.direction === 'decreased' ? '↓' : '↑'} {item.percentage}% ({formatPrice(Math.abs(item.difference), item.currency)})
                            </span>
                          </div>
                        ) : item.price !== null && item.price !== undefined ? (
                          <span className="font-semibold text-gray-900 dark:text-white">
                            {formatPrice(item.price, item.currency)}
                          </span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>

                      {/* Stock */}
                      <td className="px-4 py-3 text-center whitespace-nowrap">
                        {item._category === 'stock' ? (
                          <span
                            className={cn(
                              'text-xs font-semibold px-2 py-0.5 rounded-full',
                              item.new_in_stock
                                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400'
                                : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400'
                            )}
                          >
                            {item.new_in_stock ? 'In Stock' : 'Out of Stock'}
                          </span>
                        ) : (
                          <Badge variant={item.in_stock ? 'success' : 'danger'} size="sm">
                            {item.in_stock ? 'In Stock' : 'Out of Stock'}
                          </Badge>
                        )}
                      </td>

                      {/* Link */}
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        {item.url ? (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs font-semibold text-primary-600 hover:text-primary-700 dark:text-primary-400"
                          >
                            View
                            <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5" />
                          </a>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default CatalogDiffViewer
