import React, { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  CubeIcon,
  Squares2X2Icon,
  TableCellsIcon,
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
  TagIcon,
  ArrowTopRightOnSquareIcon,
} from '@heroicons/react/24/outline'
import { cn, formatNumber, formatPrice } from '@/utils/helpers'
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
  PriceHistoryModal,
  ExportSyncModal,
  CompetitorClusterModal,
  ProductSentimentModal,
  ProductInventoryForecastModal,
  PricingSimulatorModal,
  PromotionsTrackerModal,
  ProductSerpRankingModal,
  BuyBoxTrackerModal,
  TaxonomyAutoMapperModal,
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
  const [isTaxonomyModalOpen, setIsTaxonomyModalOpen] = useState(false)
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
  const { data, isLoading, refetch } = useQuery({
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
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <CubeIcon className="w-8 h-8 text-primary-600" />
            Product Catalog & Intelligence
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1 text-sm">
            {formatNumber(totalProducts)} products scraped • Click any card or use quick-action icons for AI pricing, stock forecasts & sentiment
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          {/* View toggle */}
          <div className="flex items-center bg-gray-100 dark:bg-gray-800 rounded-lg p-1 border border-gray-200/60 dark:border-gray-700">
            <button
              onClick={() => setViewMode('grid')}
              title="Grid View"
              className={cn(
                'p-1.5 rounded-md transition-colors',
                viewMode === 'grid'
                  ? 'bg-white dark:bg-gray-700 text-primary-600 dark:text-primary-400 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              <Squares2X2Icon className="w-5 h-5" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              title="Table View"
              className={cn(
                'p-1.5 rounded-md transition-colors',
                viewMode === 'table'
                  ? 'bg-white dark:bg-gray-700 text-primary-600 dark:text-primary-400 shadow-sm'
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

      {/* Catalog AI & Competitor Action Bar */}
      <div className="bg-white dark:bg-gray-800/90 border border-gray-200 dark:border-gray-700/80 rounded-xl p-3 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-1">
          <SparklesIcon className="w-4 h-4 text-primary-500" />
          <span>Catalog Intelligence Suite</span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Price Drops Quick Filter */}
          <button
            type="button"
            onClick={() =>
              handleFilterChange({
                ...filters,
                is_price_drop: filters.is_price_drop === 'true' ? '' : 'true',
              })
            }
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all',
              filters.is_price_drop === 'true'
                ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                : 'bg-gray-50 dark:bg-gray-900/60 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700 hover:border-emerald-500/50'
            )}
          >
            <ArrowTrendingDownIcon
              className={cn(
                'w-4 h-4',
                filters.is_price_drop === 'true' ? 'text-white' : 'text-emerald-500'
              )}
            />
            Price Drops Only
          </button>

          {/* Deduplicate & Match Competitors Button */}
          <button
            type="button"
            onClick={handleRunDeduplication}
            disabled={isDeduplicating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border bg-gray-50 dark:bg-gray-900/60 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700 hover:border-indigo-500/50 transition-all disabled:opacity-50"
            title="Deduplicate catalog and cluster identical products across competitor stores"
          >
            <ArrowsRightLeftIcon className="w-4 h-4 text-indigo-500" />
            {isDeduplicating ? 'Matching Catalog...' : 'Match Competitors'}
          </button>

          {/* Competitor Promotions & Coupons Explorer */}
          <button
            type="button"
            onClick={() => setIsCatalogPromotionsOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border bg-gray-50 dark:bg-gray-900/60 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700 hover:border-amber-500/50 transition-all"
          >
            <TicketIcon className="w-4 h-4 text-amber-500" />
            Coupons & Promos
          </button>

          {/* AI Catalog Categorization & Taxonomy Auto-Mapper */}
          <button
            type="button"
            onClick={() => setIsTaxonomyModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border bg-gray-50 dark:bg-gray-900/60 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700 hover:border-purple-500/50 transition-all"
          >
            <TagIcon className="w-4 h-4 text-purple-500" />
            AI Taxonomy Mapper
          </button>
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
              ? 'No products match your current filters.'
              : 'No products have been scraped yet. Start a scraping job to collect products.'
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
              onOpenHistory={(p) => setHistoryProduct(p)}
              onOpenSimulator={(p) => setSimulatorProduct(p)}
              onOpenForecast={(p) => setForecastProduct(p)}
              onOpenSentiment={(p) => setSentimentProduct(p)}
              onOpenBuyBox={(p) => setBuyboxProduct(p)}
              onOpenPromotions={(p) => setPromotionsProduct(p)}
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
                    Actions
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
                    onOpenHistory={(p) => setHistoryProduct(p)}
                    onOpenSimulator={(p) => setSimulatorProduct(p)}
                    onOpenForecast={(p) => setForecastProduct(p)}
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

      {/* AI Product Catalog Categorization & Taxonomy Auto-Mapper Modal */}
      <TaxonomyAutoMapperModal
        isOpen={isTaxonomyModalOpen}
        onClose={() => setIsTaxonomyModalOpen(false)}
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

function ProductDetailModal({
  product,
  isOpen,
  onClose,
  onOpenHistory,
  onOpenCluster,
  onOpenSentiment,
  onOpenForecast,
  onOpenSimulator,
  onOpenPromotions,
  onOpenSerp,
  onOpenBuyBox,
  onOpenSync,
}) {
  if (!product) return null

  const intelligenceTools = [
    {
      name: 'Price History & Trends',
      desc: 'Historical chart, lowest/highest record',
      icon: ChartBarIcon,
      color: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/50',
      onClick: () => {
        onClose()
        onOpenHistory(product)
      },
    },
    {
      name: 'AI Pricing Simulator',
      desc: 'Counterfactual margin & elasticity model',
      icon: CalculatorIcon,
      color: 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/50',
      onClick: () => {
        onClose()
        onOpenSimulator(product)
      },
    },
    {
      name: 'Stock Velocity Forecast',
      desc: 'Depletion rate & stockout prediction',
      icon: BoltIcon,
      color: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/50',
      onClick: () => {
        onClose()
        onOpenForecast(product)
      },
    },
    {
      name: 'Reviews & Sentiment',
      desc: 'Customer ratings & AI aspect analysis',
      icon: ChatBubbleBottomCenterTextIcon,
      color: 'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/50',
      onClick: () => {
        onClose()
        onOpenSentiment(product)
      },
    },
    {
      name: 'Buy Box Intelligence',
      desc: 'Marketplace win share & seller price delta',
      icon: TrophyIcon,
      color: 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-950/50',
      onClick: () => {
        onClose()
        onOpenBuyBox(product)
      },
    },
    {
      name: 'Coupons & Promos',
      desc: 'Detected voucher codes, BOGO & bundles',
      icon: TicketIcon,
      color: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50',
      onClick: () => {
        onClose()
        onOpenPromotions(product)
      },
    },
    {
      name: 'SERP Search Rankings',
      desc: 'Keyword organic & sponsored position',
      icon: MagnifyingGlassIcon,
      color: 'text-cyan-600 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-950/50',
      onClick: () => {
        onClose()
        onOpenSerp(product)
      },
    },
    ...(product.match_cluster_id && onOpenCluster
      ? [
          {
            name: 'Competitor Cluster',
            desc: 'Cross-store price & stock comparison',
            icon: ArrowsRightLeftIcon,
            color: 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/50',
            onClick: () => {
              onClose()
              onOpenCluster(product.match_cluster_id)
            },
          },
        ]
      : []),
  ]

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={product.name} size="xl">
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Image Column */}
          <div className="md:col-span-5">
            <div className="aspect-square bg-gray-100 dark:bg-gray-900 rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 flex items-center justify-center">
              {product.image_url ? (
                <img
                  src={product.image_url}
                  alt={product.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="flex flex-col items-center justify-center text-gray-400 gap-2">
                  <CubeIcon className="w-16 h-16 stroke-1" />
                  <span className="text-xs">No product image</span>
                </div>
              )}
            </div>
          </div>

          {/* Details Column */}
          <div className="md:col-span-7 space-y-4">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              {product.brand ? (
                <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-primary-50 text-primary-700 dark:bg-primary-950/60 dark:text-primary-300">
                  {product.brand}
                </span>
              ) : (
                <span />
              )}

              <span
                className={cn(
                  'px-2.5 py-1 text-xs font-semibold rounded-full',
                  product.in_stock
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                    : 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300'
                )}
              >
                {product.in_stock ? '● In Stock' : '○ Out of Stock'}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-900/60 border border-gray-200/70 dark:border-gray-700/70">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Current Scraped Price</p>
              <div className="flex items-baseline gap-3 flex-wrap">
                <p className="text-3xl font-extrabold text-gray-900 dark:text-white">
                  {formatPrice(product.price, product.currency)}
                </p>
                {product.normalized_price &&
                  product.normalized_currency &&
                  product.normalized_currency !== product.currency && (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400">
                      ≈ {product.normalized_currency} {product.normalized_price}
                    </span>
                  )}
                {product.original_price && product.original_price > product.price && (
                  <p className="text-sm text-gray-400 line-through">
                    {formatPrice(product.original_price, product.currency)}
                  </p>
                )}
              </div>

              {(product.lowest_price || product.highest_price) && (
                <div className="flex items-center gap-4 mt-2 pt-2 border-t border-gray-200/60 dark:border-gray-800 text-xs text-gray-500 dark:text-gray-400">
                  {product.lowest_price && (
                    <span>
                      Lowest: <strong className="text-emerald-600 dark:text-emerald-400">{formatPrice(product.lowest_price, product.currency)}</strong>
                    </span>
                  )}
                  {product.highest_price && (
                    <span>
                      Highest: <strong className="text-rose-600 dark:text-rose-400">{formatPrice(product.highest_price, product.currency)}</strong>
                    </span>
                  )}
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              {product.source_domain && (
                <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/60">
                  <span className="text-gray-400 block">Store Domain</span>
                  <span className="font-semibold text-gray-800 dark:text-gray-200 truncate block mt-0.5">
                    {product.source_domain}
                  </span>
                </div>
              )}
              {product.sku && (
                <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/60">
                  <span className="text-gray-400 block">SKU / Identifier</span>
                  <span className="font-mono font-semibold text-gray-800 dark:text-gray-200 truncate block mt-0.5">
                    {product.sku}
                  </span>
                </div>
              )}
              {product.category && (
                <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/60 col-span-2">
                  <span className="text-gray-400 block">Category Path</span>
                  <span className="font-medium text-gray-800 dark:text-gray-200 block mt-0.5">
                    {product.category_path || product.category}
                  </span>
                </div>
              )}
            </div>

            {product.description && (
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">
                  Description
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-3 leading-relaxed">
                  {product.description}
                </p>
              </div>
            )}

            {/* Product Variants & Inventory Section */}
            {product.variants && product.variants.length > 0 && (
              <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-gray-900 dark:text-white flex items-center gap-1.5 text-xs uppercase tracking-wider">
                    <span>Product Variants</span>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-primary-100 text-primary-800 dark:bg-primary-950/60 dark:text-primary-300">
                      {product.variants.length}
                    </span>
                  </h4>
                </div>

                <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                  {product.variants.map((v, idx) => (
                    <div
                      key={v.id || idx}
                      className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50 flex items-center justify-between gap-3 text-xs"
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
                        </div>
                      </div>

                      <div className="text-right shrink-0 flex items-center gap-2">
                        {v.price !== null && v.price !== undefined && (
                          <span className="font-semibold text-gray-900 dark:text-white">
                            {formatPrice(v.price, product.currency)}
                          </span>
                        )}
                        <span
                          className={cn(
                            'inline-block px-1.5 py-0.5 rounded text-[10px] font-medium',
                            v.in_stock
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400'
                              : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400'
                          )}
                        >
                          {v.in_stock ? 'In Stock' : 'Out'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* AI & Competitor Intelligence Action Grid */}
        <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
              <SparklesIcon className="w-4 h-4 text-primary-500" />
              Product Intelligence & Analytics Tools
            </h4>
            <span className="text-xs text-gray-400">Select a tool to launch deep analysis</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
            {intelligenceTools.map((tool) => (
              <button
                key={tool.name}
                type="button"
                onClick={tool.onClick}
                className="flex items-start gap-3 p-3 rounded-xl border border-gray-200 dark:border-gray-700/80 hover:border-primary-400 dark:hover:border-primary-500 bg-white dark:bg-gray-800/60 hover:bg-gray-50/80 dark:hover:bg-gray-800 text-left transition-all group shadow-sm"
              >
                <div className={cn('p-2 rounded-lg shrink-0 transition-transform group-hover:scale-105', tool.color)}>
                  <tool.icon className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-gray-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400 truncate">
                    {tool.name}
                  </p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400 line-clamp-1 mt-0.5">
                    {tool.desc}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      <ModalFooter>
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        {onOpenSync && (
          <Button
            variant="primary"
            icon={CloudArrowUpIcon}
            onClick={() => {
              onClose()
              onOpenSync(product)
            }}
          >
            Export & Sync Product
          </Button>
        )}
        <a href={product.url} target="_blank" rel="noopener noreferrer">
          <Button variant="outline" icon={ArrowTopRightOnSquareIcon}>
            View on Store
          </Button>
        </a>
      </ModalFooter>
    </Modal>
  )
}