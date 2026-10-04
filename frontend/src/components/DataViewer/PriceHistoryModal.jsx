import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import {
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
  MinusIcon,
  ClockIcon,
  CalendarDaysIcon,
} from '@heroicons/react/24/outline'
import { Modal, ModalFooter, Button, Badge, Spinner } from '@/components/Common'
import { apiGet } from '@/services/api'
import { formatPrice } from '@/utils/helpers'

// Register ChartJS modules
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

export function PriceHistoryModal({ product, isOpen, onClose }) {
  if (!product) return null

  const currency = product.currency || 'USD'

  // Fetch chronological price history
  const { data: history = [], isLoading } = useQuery({
    queryKey: ['product-price-history', product.id],
    queryFn: () => apiGet(`/products/${product.id}/history`),
    enabled: isOpen && !!product.id,
  })

  // Format chart data
  const chartLabels = history.map((item) => {
    const d = new Date(item.recorded_at)
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  })

  const pricePoints = history.map((item) => item.price)

  const isPriceDrop = (product.price_change || 0) < 0
  const isPriceUp = (product.price_change || 0) > 0

  const chartColor = isPriceDrop ? 'rgba(16, 185, 129, 1)' : isPriceUp ? 'rgba(239, 68, 68, 1)' : 'rgba(99, 102, 241, 1)'
  const chartBg = isPriceDrop ? 'rgba(16, 185, 129, 0.15)' : isPriceUp ? 'rgba(239, 68, 68, 0.15)' : 'rgba(99, 102, 241, 0.15)'

  const chartData = {
    labels: chartLabels.length > 0 ? chartLabels : ['Initial'],
    datasets: [
      {
        label: `Price (${currency})`,
        data: pricePoints.length > 0 ? pricePoints : [product.price || 0],
        borderColor: chartColor,
        backgroundColor: chartBg,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: chartColor,
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context) => ` Price: ${formatPrice(context.parsed.y, currency)}`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { font: { size: 11 } },
      },
      y: {
        grid: { color: 'rgba(156, 163, 175, 0.15)' },
        ticks: {
          font: { size: 11 },
          callback: (value) => formatPrice(value, currency),
        },
      },
    },
  }

  const initialPrice = history.length > 0 ? history[0].price : product.price
  const currentPrice = product.price || 0
  const lowestPrice = product.lowest_price || currentPrice
  const highestPrice = product.highest_price || currentPrice
  const netChange = initialPrice ? ((currentPrice - initialPrice) / initialPrice) * 100 : 0

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Price History & Trend Analysis" size="xl">
      <div className="space-y-6">
        {/* Product Header */}
        <div className="flex items-start gap-4 p-4 bg-gray-50 dark:bg-gray-800/60 rounded-xl border border-gray-100 dark:border-gray-800">
          {product.image_url && (
            <img
              src={product.image_url}
              alt={product.name}
              className="w-16 h-16 object-cover rounded-lg border border-gray-200 dark:border-gray-700 flex-shrink-0"
              onError={(e) => { e.target.style.display = 'none' }}
            />
          )}
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900 dark:text-white line-clamp-1">{product.name}</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">
              {product.source_domain || 'Store Product'} • SKU: {product.sku || 'N/A'}
            </p>
            <div className="flex items-center gap-3 mt-2">
              <span className="text-xl font-bold text-gray-900 dark:text-white">
                {formatPrice(currentPrice, currency)}
              </span>
              {isPriceDrop && (
                <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400">
                  <ArrowTrendingDownIcon className="w-3.5 h-3.5" />
                  Price Drop {Math.abs(product.price_change_percentage || 0)}%
                </span>
              )}
              {isPriceUp && (
                <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400">
                  <ArrowTrendingUpIcon className="w-3.5 h-3.5" />
                  +{product.price_change_percentage}%
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Current Price</p>
            <p className="text-lg font-bold text-gray-900 dark:text-white mt-1">
              {formatPrice(currentPrice, currency)}
            </p>
          </div>
          <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Lowest Price</p>
            <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-1">
              {formatPrice(lowestPrice, currency)}
            </p>
          </div>
          <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Highest Price</p>
            <p className="text-lg font-bold text-gray-700 dark:text-gray-300 mt-1">
              {formatPrice(highestPrice, currency)}
            </p>
          </div>
          <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Net Change</p>
            <p className={`text-lg font-bold mt-1 ${netChange < 0 ? 'text-emerald-600' : netChange > 0 ? 'text-rose-600' : 'text-gray-600'}`}>
              {netChange > 0 ? '+' : ''}{netChange.toFixed(1)}%
            </p>
          </div>
        </div>

        {/* Interactive Price Trend Chart */}
        <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <CalendarDaysIcon className="w-5 h-5 text-primary-600" />
              <h4 className="font-semibold text-sm text-gray-900 dark:text-white">Price Trend Timeline</h4>
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {history.length} snapshots recorded
            </span>
          </div>

          <div className="h-64 relative">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <Spinner size="md" />
              </div>
            ) : history.length <= 1 ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-6 text-gray-500">
                <ClockIcon className="w-10 h-10 text-gray-400 mb-2" />
                <p className="text-sm font-medium">Tracking Started</p>
                <p className="text-xs text-gray-400 mt-1">
                  1 price point recorded ({formatPrice(currentPrice, currency)}). Subsequent crawls will plot historical trend curves here.
                </p>
              </div>
            ) : (
              <Line data={chartData} options={chartOptions} />
            )}
          </div>
        </div>

        {/* Historical Snapshots Table */}
        {history.length > 0 && (
          <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
            <div className="px-4 py-2.5 bg-gray-50 dark:bg-gray-800/80 border-b border-gray-200 dark:border-gray-700">
              <h5 className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                Historical Snapshots Log
              </h5>
            </div>
            <div className="max-h-48 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-800">
              {history.map((snapshot, idx) => {
                const prev = idx > 0 ? history[idx - 1] : null
                const diff = prev ? snapshot.price - prev.price : 0
                return (
                  <div key={snapshot.id || idx} className="px-4 py-2 flex items-center justify-between text-xs">
                    <span className="text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
                      <ClockIcon className="w-3.5 h-3.5" />
                      {new Date(snapshot.recorded_at).toLocaleString()}
                    </span>
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-gray-900 dark:text-white">
                        {formatPrice(snapshot.price, currency)}
                      </span>
                      {diff < 0 && (
                        <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                          ↓ {formatPrice(Math.abs(diff), currency)}
                        </span>
                      )}
                      {diff > 0 && (
                        <span className="text-rose-600 dark:text-rose-400 font-medium">
                          ↑ {formatPrice(diff, currency)}
                        </span>
                      )}
                      {diff === 0 && (
                        <span className="text-gray-400 font-normal">No change</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      <ModalFooter>
        <Button variant="secondary" onClick={onClose}>Close</Button>
        <a href={product.url} target="_blank" rel="noopener noreferrer">
          <Button variant="primary">View Live Product</Button>
        </a>
      </ModalFooter>
    </Modal>
  )
}
