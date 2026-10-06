import React, { useState, useEffect } from 'react'
import {
  ArrowsRightLeftIcon,
  SparklesIcon,
  CheckCircleIcon,
  ArrowTopRightOnSquareIcon,
  BuildingStorefrontIcon,
  CubeIcon,
  TagIcon,
  CurrencyDollarIcon,
  ArrowTrendingDownIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import { Modal, ModalFooter, Button, Spinner, Badge } from '@/components/Common'
import { formatPrice, cn } from '@/utils/helpers'
import matchingService from '@/services/matchingService'

export function CompetitorClusterModal({ clusterId, isOpen, onClose, onClusterUpdated }) {
  const [loading, setLoading] = useState(false)
  const [clusterData, setClusterData] = useState(null)
  const [error, setError] = useState(null)
  const [unclustering, setUnclustering] = useState(false)

  useEffect(() => {
    if (isOpen && clusterId) {
      fetchCluster()
    } else {
      setClusterData(null)
      setError(null)
    }
  }, [isOpen, clusterId])

  const fetchCluster = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await matchingService.getCluster(clusterId)
      if (res?.cluster) {
        setClusterData(res.cluster)
      } else {
        setError('Cluster not found')
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load competitor cluster')
    } finally {
      setLoading(false)
    }
  }

  const handleUncluster = async () => {
    if (!window.confirm('Are you sure you want to decouple this product cluster?')) return
    setUnclustering(true)
    try {
      await matchingService.uncluster(clusterId)
      if (onClusterUpdated) onClusterUpdated()
      onClose()
    } catch (err) {
      alert('Failed to uncluster products: ' + err.message)
    } finally {
      setUnclustering(false)
    }
  }

  if (!isOpen) return null

  const products = clusterData?.products || []
  const lowestPrice = clusterData?.lowest_price ?? 0
  const highestPrice = clusterData?.highest_price ?? 0
  const savings = clusterData?.price_difference ?? 0
  const savingsPct = clusterData?.savings_percentage ?? 0
  const currency = clusterData?.currency || 'USD'

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Cross-Store Competitor Comparison"
      size="xl"
    >
      {loading ? (
        <div className="py-12 flex flex-col items-center justify-center gap-3">
          <Spinner size="lg" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading cross-catalog competitor offerings...</p>
        </div>
      ) : error ? (
        <div className="py-8 text-center text-rose-600 dark:text-rose-400">
          <p className="font-medium">{error}</p>
          <Button variant="secondary" className="mt-4" onClick={fetchCluster}>
            Retry
          </Button>
        </div>
      ) : clusterData ? (
        <div className="space-y-6">
          {/* Canonical Product Overview */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-primary-50 to-indigo-50 dark:from-primary-950/40 dark:to-indigo-950/30 border border-primary-100 dark:border-primary-900/50">
            <div className="flex items-start justify-between gap-4">
              <div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800 dark:bg-indigo-900/60 dark:text-indigo-300 mb-2">
                  <SparklesIcon className="w-3.5 h-3.5" />
                  Cluster ID: {clusterId}
                </span>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white line-clamp-2">
                  {clusterData.canonical_name}
                </h3>
              </div>
            </div>

            {/* Price Spread KPI Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
              <div className="p-3 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">Lowest Competitor</span>
                <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                  {formatPrice(lowestPrice, currency)}
                </p>
              </div>

              <div className="p-3 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">Highest Competitor</span>
                <p className="text-lg font-bold text-rose-600 dark:text-rose-400 mt-0.5">
                  {formatPrice(highestPrice, currency)}
                </p>
              </div>

              <div className="p-3 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">Price Spread / Gap</span>
                <p className="text-lg font-bold text-primary-600 dark:text-primary-400 mt-0.5">
                  {formatPrice(savings, currency)}
                </p>
              </div>

              <div className="p-3 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">Max Savings</span>
                <p className="text-lg font-bold text-amber-600 dark:text-amber-400 mt-0.5">
                  {savingsPct}%
                </p>
              </div>
            </div>
          </div>

          {/* Competitor Listings Comparison Table */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-3 flex items-center justify-between">
              <span>Matched Competitor Listings ({products.length} Stores)</span>
              <span className="text-xs font-normal text-gray-500">Sorted by best price</span>
            </h4>

            <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
                <thead className="bg-gray-50 dark:bg-gray-800 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="px-4 py-3 text-left">Store / Domain</th>
                    <th className="px-4 py-3 text-left">Product Title</th>
                    <th className="px-4 py-3 text-right">Price</th>
                    <th className="px-4 py-3 text-center">Confidence</th>
                    <th className="px-4 py-3 text-center">Stock</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-900">
                  {products.map((item, idx) => {
                    const isLowest = item.price !== null && Number(item.price) === lowestPrice
                    const isHighest = item.price !== null && Number(item.price) === highestPrice && lowestPrice !== highestPrice

                    return (
                      <tr
                        key={item.id || idx}
                        className={cn(
                          'hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors',
                          isLowest && 'bg-emerald-50/40 dark:bg-emerald-950/20'
                        )}
                      >
                        {/* Domain */}
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-white whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <BuildingStorefrontIcon className="w-4 h-4 text-gray-400" />
                            <span className="capitalize">{item.source_domain || 'Unknown'}</span>
                          </div>
                        </td>

                        {/* Title & Image */}
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            {item.image_url ? (
                              <img
                                src={item.image_url}
                                alt={item.name}
                                className="w-9 h-9 rounded object-cover shrink-0 border border-gray-200 dark:border-gray-700"
                              />
                            ) : (
                              <div className="w-9 h-9 rounded bg-gray-100 dark:bg-gray-800 flex items-center justify-center shrink-0">
                                <CubeIcon className="w-5 h-5 text-gray-400" />
                              </div>
                            )}
                            <div className="min-w-0 max-w-xs">
                              <p className="text-gray-900 dark:text-gray-100 font-medium truncate" title={item.name}>
                                {item.name}
                              </p>
                              {item.sku && (
                                <p className="text-[11px] text-gray-500 font-mono">SKU: {item.sku}</p>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Price */}
                        <td className="px-4 py-3 text-right whitespace-nowrap">
                          <div className="inline-flex flex-col items-end">
                            <span className={cn(
                              'font-bold text-base',
                              isLowest ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-900 dark:text-white'
                            )}>
                              {formatPrice(item.price, item.currency || currency)}
                            </span>
                            {isLowest && (
                              <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300">
                                Best Price
                              </span>
                            )}
                            {isHighest && (
                              <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-300">
                                Highest
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Match Confidence */}
                        <td className="px-4 py-3 text-center whitespace-nowrap">
                          {item.match_confidence !== null && item.match_confidence !== undefined ? (
                            <span className={cn(
                              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold',
                              item.match_confidence >= 0.95
                                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400'
                                : item.match_confidence >= 0.80
                                ? 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-400'
                                : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-400'
                            )}>
                              <CheckCircleIcon className="w-3.5 h-3.5" />
                              {Math.round(item.match_confidence * 100)}%
                            </span>
                          ) : (
                            <span className="text-xs text-gray-400">100%</span>
                          )}
                        </td>

                        {/* Stock */}
                        <td className="px-4 py-3 text-center whitespace-nowrap">
                          <Badge variant={item.in_stock ? 'success' : 'danger'} size="sm">
                            {item.in_stock ? 'In Stock' : 'Out of Stock'}
                          </Badge>
                        </td>

                        {/* Action */}
                        <td className="px-4 py-3 text-right whitespace-nowrap">
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs font-semibold text-primary-600 hover:text-primary-700 dark:text-primary-400"
                          >
                            Visit Store
                            <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5" />
                          </a>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}

      <ModalFooter>
        <div className="flex items-center justify-between w-full">
          <Button
            variant="danger"
            onClick={handleUncluster}
            disabled={unclustering || !clusterData}
            isLoading={unclustering}
          >
            Dissolve Cluster
          </Button>

          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </ModalFooter>
    </Modal>
  )
}

export default CompetitorClusterModal
