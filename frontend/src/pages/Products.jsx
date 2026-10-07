import React, { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  CubeIcon,
  Squares2X2Icon,
  TableCellsIcon,
  ArrowDownTrayIcon,
  CloudArrowUpIcon,
  ArrowTrendingDownIcon,
  ChartBarIcon,
  ArrowsRightLeftIcon,
  SparklesIcon,
  ChatBubbleBottomCenterTextIcon,
  BoltIcon,
  CalculatorIcon,
  TicketIcon,
  MagnifyingGlassIcon,
  TrophyIcon,
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
import {
  ProductCard,
  ProductRow,
  ProductFilters,
  ExportButton,
  PriceHistoryModal,
  ExportSyncModal,
  CompetitorClusterModal,
  ProductSentimentModal,
  ProductInventoryForecastModal,
  PricingSimulatorModal,
  PromotionsTrackerModal,
  ProductSerpRankingModal,
  BuyBoxTrackerModal,
} from '@/components/DataViewer'
import { apiGet } from '@/services/api'
import matchingService from '@/services/matchingService'

export default function Products() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState('grid')
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [historyProduct, setHistoryProduct] = useState(null)
  const [selectedProductIds, setSelectedProductIds] = useState([])
  const [isExportSyncModalOpen, setIsExportSyncModalOpen] = useState(false)
  const [selectedClusterId, setSelectedClusterId] = useState(null)
  const [sentimentProduct, setSentimentProduct] = useState(null)
  const [forecastProduct, setForecastProduct] = useState(null)
  const [simulatorProduct, setSimulatorProduct] = useState(null)
  const [promotionsProduct, setPromotionsProduct] = useState(null)
  const [serpProduct, setSerpProduct] = useState(null)
  const [buyboxProduct, setBuyboxProduct] = useState(null)
  const [isCatalogPromotionsOpen, setIsCatalogPromotionsOpen] = useState(false)
  const [isDeduplicating, setIsDeduplicating] = useState(false)
  const [clusterNotice, setClusterNotice] = useState(null)

  // Parse filters from URL
  const filters = {
    search: searchParams.get('search') || '',
    category: searchParams.get('category') || '',
    brand: searchParams.get('brand') || '',
    min_price: searchParams.get('min_price') || '',
    max_price: searchParams.get('max_price') || '',
    in_stock: searchParams.get('in_stock') || '',
    domain: searchParams.get('domain') || '',
    is_price_drop: searchParams.get('is_price_drop') || '',
  }
  const page = parseInt(searchParams.get('page') || '1', 10)
  const pageSize = viewMode === 'grid' ? 12 : 20

  // Filter out empty strings before sending to API
  const activeFilters = Object.fromEntries(
    Object.entries(filters).filter(([_, v]) => v !== '')
  )

  // Fetch products
  const { data, isLoading, error, refetch } = useQuery({
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

  const handleToggleSelect = (id) => {
    setSelectedProductIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    )
  }

  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedProductIds(products.map((p) => p.id))
    } else {
      setSelectedProductIds([])
    }
  }

  const handleRunDeduplication = async () => {
    if (isDeduplicating) return
    setIsDeduplicating(true)
    setClusterNotice(null)
    try {
      const res = await matchingService.clusterAll({ threshold: 0.75, use_ai: false })
      setClusterNotice(res.message || 'Competitor catalog clustering complete!')
      refetch()
    } catch (err) {
      alert('Failed to cluster catalog: ' + (err?.response?.data?.detail || err.message || 'Error'))
    } finally {
      setIsDeduplicating(false)
    }
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
        
        <div className="flex items-center gap-3 flex-wrap">
          {/* Deduplicate & Match Competitors Button */}
          <Button
            icon={SparklesIcon}
            variant="secondary"
            onClick={handleRunDeduplication}
            isLoading={isDeduplicating}
            title="Deduplicate catalog and cluster identical products across competitor stores"
          >
            {isDeduplicating ? 'Matching...' : 'Match Competitors'}
          </Button>

          {/* Price Drops Quick Filter */}
          <button
            type="button"
            onClick={() => handleFilterChange({
              is_price_drop: filters.is_price_drop === 'true' ? '' : 'true'
            })}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all',
              filters.is_price_drop === 'true'
                ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
            )}
          >
            <ArrowTrendingDownIcon className="w-4 h-4 text-emerald-500" />
            Price Drops Only
          </button>

          {/* Competitor Promotions & Coupons Explorer */}
          <button
            onClick={() => setIsCatalogPromotionsOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-emerald-500/50 transition-all"
          >
            <TicketIcon className="w-4 h-4 text-emerald-500" />
            Coupons & Promos
          </button>

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
          
          <Button
            icon={CloudArrowUpIcon}
            variant={selectedProductIds.length > 0 ? 'primary' : 'secondary'}
            onClick={() => setIsExportSyncModalOpen(true)}
          >
            {selectedProductIds.length > 0
              ? `Export & Sync (${selectedProductIds.length})`
              : 'Export & Sync'}
          </Button>
        </div>
      </div>

      {/* Cluster notice banner */}
      {clusterNotice && (
        <div className="p-3 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 flex items-center justify-between text-xs text-indigo-900 dark:text-indigo-200">
          <div className="flex items-center gap-2">
            <SparklesIcon className="w-4 h-4 text-indigo-600 shrink-0" />
            <span>{clusterNotice}</span>
          </div>
          <button
            type="button"
            onClick={() => setClusterNotice(null)}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            Dismiss
          </button>
        </div>
      )}

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
              selected={selectedProductIds.includes(product.id)}
              onToggleSelect={handleToggleSelect}
              onViewCluster={(cid) => setSelectedClusterId(cid)}
            />
          ))}
        </div>
      ) : (
        <Card padding="none" className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-3 py-3 text-left w-10">
                    <input
                      type="checkbox"
                      checked={products.length > 0 && selectedProductIds.length === products.length}
                      onChange={(e) => handleSelectAll(e.target.checked)}
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
                    />
                  </th>
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
                    selected={selectedProductIds.includes(product.id)}
                    onToggleSelect={handleToggleSelect}
                    onViewCluster={(cid) => setSelectedClusterId(cid)}
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
        onOpenHistory={(p) => setHistoryProduct(p)}
        onOpenCluster={(cid) => setSelectedClusterId(cid)}
        onOpenSentiment={(p) => setSentimentProduct(p)}
        onOpenForecast={(p) => setForecastProduct(p)}
        onOpenSimulator={(p) => setSimulatorProduct(p)}
        onOpenPromotions={(p) => setPromotionsProduct(p)}
        onOpenSerp={(p) => setSerpProduct(p)}
        onOpenBuyBox={(p) => setBuyboxProduct(p)}
        onOpenSync={(p) => {
          setSelectedProductIds([p.id])
          setIsExportSyncModalOpen(true)
        }}
      />

      {/* Price History & Trend Modal */}
      <PriceHistoryModal
        product={historyProduct}
        isOpen={!!historyProduct}
        onClose={() => setHistoryProduct(null)}
      />

      {/* Cross-Store Competitor Comparison Modal */}
      <CompetitorClusterModal
        clusterId={selectedClusterId}
        isOpen={!!selectedClusterId}
        onClose={() => setSelectedClusterId(null)}
        onClusterUpdated={() => refetch()}
      />

      {/* Customer Reviews & AI Sentiment Intelligence Modal */}
      <ProductSentimentModal
        product={sentimentProduct}
        isOpen={!!sentimentProduct}
        onClose={() => setSentimentProduct(null)}
      />

      {/* Competitor Inventory Depletion & Stockout Predictor Modal */}
      <ProductInventoryForecastModal
        product={forecastProduct}
        isOpen={!!forecastProduct}
        onClose={() => setForecastProduct(null)}
      />

      {/* AI Competitor Strategy & Pricing Simulator Modal */}
      <PricingSimulatorModal
        product={simulatorProduct}
        isOpen={!!simulatorProduct}
        onClose={() => setSimulatorProduct(null)}
      />

      {/* Competitor Promotions & Coupon Intelligence Modals */}
      <PromotionsTrackerModal
        product={promotionsProduct}
        isOpen={!!promotionsProduct}
        onClose={() => setPromotionsProduct(null)}
      />

      <PromotionsTrackerModal
        product={null}
        isOpen={isCatalogPromotionsOpen}
        onClose={() => setIsCatalogPromotionsOpen(false)}
      />

      {/* Product SERP Ranking Positions Modal */}
      <ProductSerpRankingModal
        product={serpProduct}
        isOpen={!!serpProduct}
        onClose={() => setSerpProduct(null)}
      />

      {/* Marketplace Buy Box Win/Loss Predictor & Tracker Modal */}
      <BuyBoxTrackerModal
        product={buyboxProduct}
        isOpen={!!buyboxProduct}
        onClose={() => setBuyboxProduct(null)}
      />

      {/* 1-Click Export & Sync Modal */}
      <ExportSyncModal
        isOpen={isExportSyncModalOpen}
        onClose={() => setIsExportSyncModalOpen(false)}
        productIds={selectedProductIds}
        totalProductsCount={totalProducts}
      />
    </div>
  )
}

function ProductDetailModal({ product, isOpen, onClose, onOpenHistory, onOpenCluster, onOpenSentiment, onOpenForecast, onOpenSimulator, onOpenPromotions, onOpenSerp, onOpenBuyBox, onOpenSync }) {
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
            <div className="flex items-baseline gap-2 flex-wrap">
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {product.currency || '£'} {product.price !== null && product.price !== undefined ? product.price : 'Price not available'}
              </p>
              {product.normalized_price && product.normalized_currency && product.normalized_currency !== product.currency && (
                <span className="text-sm font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400">
                  ≈ {product.normalized_currency} {product.normalized_price}
                </span>
              )}
            </div>
            {product.original_price && product.original_price > product.price && (
              <p className="text-sm text-gray-500 line-through">
                {product.currency || '£'} {product.original_price}
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

          {/* Product Variants & Inventory Section */}
          {product.variants && product.variants.length > 0 && (
            <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-semibold text-gray-900 dark:text-white flex items-center gap-1.5 text-sm">
                  <span>Product Variants & Inventory</span>
                  <span className="text-xs font-normal px-2 py-0.5 rounded-full bg-primary-100 text-primary-800 dark:bg-primary-950/60 dark:text-primary-300">
                    {product.variants.length} options
                  </span>
                </h4>
              </div>
              
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {product.variants.map((v, idx) => (
                  <div
                    key={v.id || idx}
                    className="p-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50 flex items-center justify-between gap-3 text-xs"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-gray-900 dark:text-white truncate">
                        {v.name}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5 text-gray-500 dark:text-gray-400 font-mono text-[11px]">
                        {v.sku && <span>SKU: {v.sku}</span>}
                        {v.stock_quantity !== null && v.stock_quantity !== undefined && (
                          <span>Qty: {v.stock_quantity}</span>
                        )}
                        {v.attributes && Object.keys(v.attributes).length > 0 && (
                          <span className="text-gray-600 dark:text-gray-300">
                            {Object.entries(v.attributes).map(([k, val]) => `${k}: ${val}`).join(' • ')}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      {v.price !== null && v.price !== undefined ? (
                        <p className="font-semibold text-gray-900 dark:text-white">
                          £{v.price}
                        </p>
                      ) : null}
                      <span className={cn(
                        "inline-block px-1.5 py-0.5 rounded text-[10px] font-medium mt-0.5",
                        v.in_stock
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400"
                          : "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400"
                      )}>
                        {v.stock_status || (v.in_stock ? 'In Stock' : 'Out of Stock')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <ModalFooter>
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        {product.match_cluster_id && onOpenCluster && (
          <Button
            variant="secondary"
            onClick={() => {
              onClose()
              onOpenCluster(product.match_cluster_id)
            }}
          >
            <ArrowsRightLeftIcon className="w-4 h-4 mr-1.5 text-indigo-600" />
            Competitor Prices
          </Button>
        )}
        <Button
          variant="secondary"
          onClick={() => {
            onClose()
            onOpenHistory(product)
          }}
        >
          <ChartBarIcon className="w-4 h-4 mr-1.5 text-primary-600" />
          Price History & Trends
        </Button>
        {onOpenSentiment && (
          <Button
            variant="secondary"
            onClick={() => {
              onClose()
              onOpenSentiment(product)
            }}
          >
            <ChatBubbleBottomCenterTextIcon className="w-4 h-4 mr-1.5 text-indigo-600" />
            Reviews & Sentiment
          </Button>
        )}
        {onOpenForecast && (
          <Button
            variant="secondary"
            onClick={() => {
              onClose()
              onOpenForecast(product)
            }}
          >
            <BoltIcon className="w-4 h-4 mr-1.5 text-amber-500" />
            Stock Velocity & Forecast
          </Button>
        )}
        {onOpenSimulator && (
          <Button
            variant="secondary"
            onClick={() => {
              onClose()
              onOpenSimulator(product)
            }}
          >
            <CalculatorIcon className="w-4 h-4 mr-1.5 text-primary-600" />
            AI Pricing Simulator
          </Button>
        )}
        {onOpenPromotions && (
          <Button
            variant="secondary"
            onClick={() => {
              onClose()
              onOpenPromotions(product)
            }}
          >
            <TicketIcon className="w-4 h-4 mr-1.5 text-emerald-500" />
            Coupons & Promos
          </Button>
        )}
        {onOpenSerp && (
          <Button
            variant="secondary"
            onClick={() => {
              onClose()
              onOpenSerp(product)
            }}
          >
            <MagnifyingGlassIcon className="w-4 h-4 mr-1.5 text-indigo-500" />
            SERP Rankings
          </Button>
        )}
        {onOpenBuyBox && (
          <Button
            variant="secondary"
            onClick={() => {
              onClose()
              onOpenBuyBox(product)
            }}
          >
            <TrophyIcon className="w-4 h-4 mr-1.5 text-amber-500" />
            Buy Box Intelligence
          </Button>
        )}
        {onOpenSync && (
          <Button
            variant="primary"
            onClick={() => {
              onClose()
              onOpenSync(product)
            }}
          >
            <CloudArrowUpIcon className="w-4 h-4 mr-1.5" />
            Export & Sync
          </Button>
        )}
        <a href={product.url} target="_blank" rel="noopener noreferrer">
          <Button variant="outline">View on Website</Button>
        </a>
      </ModalFooter>
    </Modal>
  )
}