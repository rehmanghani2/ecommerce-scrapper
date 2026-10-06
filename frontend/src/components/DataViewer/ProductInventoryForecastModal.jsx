import React, { useState, useEffect } from 'react'
import {
  ChartBarIcon,
  BoltIcon,
  ClockIcon,
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  PlusIcon,
  CurrencyDollarIcon,
  BuildingStorefrontIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import Modal from '@/components/Common/Modal'
import Button from '@/components/Common/Button'
import Badge from '@/components/Common/Badge'
import Card from '@/components/Common/Card'
import Spinner from '@/components/Common/Spinner'
import inventoryService from '@/services/inventoryService'

export default function ProductInventoryForecastModal({ product, isOpen, onClose }) {
  const [loading, setLoading] = useState(true)
  const [forecast, setForecast] = useState(null)
  const [history, setHistory] = useState([])

  // Simulation form states
  const [newStock, setNewStock] = useState('')
  const [inStock, setInStock] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  const loadData = async () => {
    if (!product?.id) return
    try {
      setLoading(true)
      const [fcRes, histRes] = await Promise.all([
        inventoryService.getInventoryForecast(product.id).catch(() => null),
        inventoryService.getStockHistory(product.id).catch(() => []),
      ])
      setForecast(fcRes)
      setHistory(histRes || [])
      if (fcRes?.current_stock !== undefined && fcRes?.current_stock !== null) {
        setNewStock(fcRes.current_stock.toString())
        setInStock(fcRes.is_in_stock)
      } else if (product.stock_quantity !== undefined && product.stock_quantity !== null) {
        setNewStock(product.stock_quantity.toString())
        setInStock(product.in_stock ?? true)
      }
    } catch (err) {
      console.error('Error fetching inventory forecast:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen && product) {
      loadData()
    }
  }, [isOpen, product])

  const handleRecordStock = async (e) => {
    e.preventDefault()
    if (!product?.id) return
    try {
      setSubmitting(true)
      const stockVal = newStock !== '' ? parseInt(newStock, 10) : null
      const res = await inventoryService.recordStockObservation(product.id, {
        stock_quantity: isNaN(stockVal) ? null : stockVal,
        in_stock: inStock,
      })
      toast.success('Stock observation recorded!')
      setForecast(res.forecast)
      loadData()
    } catch (err) {
      toast.error('Failed to record stock observation')
    } finally {
      setSubmitting(false)
    }
  }

  if (!product) return null

  const getRiskBadge = (risk) => {
    switch (risk) {
      case 'high':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300">
            <ExclamationTriangleIcon className="w-4 h-4" />
            HIGH STOCKOUT RISK
          </span>
        )
      case 'medium':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
            <ClockIcon className="w-4 h-4" />
            MEDIUM STOCKOUT RISK
          </span>
        )
      case 'out_of_stock':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300">
            <XCircleIcon className="w-4 h-4" />
            COMPLETELY OUT OF STOCK
          </span>
        )
      case 'low':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
            <CheckCircleIcon className="w-4 h-4" />
            HEALTHY BUFFER
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300">
            ANALYZING BASELINE
          </span>
        )
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Competitor Inventory Depletion & Stockout Predictor"
      size="xl"
    >
      <div className="space-y-5">
        {/* Product Identity Header */}
        <div className="flex items-start justify-between gap-4 pb-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white line-clamp-1">
              {product.name}
            </h3>
            <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
              <span className="capitalize">{product.source_domain || 'Competitor'}</span>
              <span>•</span>
              <span className="font-semibold text-gray-900 dark:text-gray-200">
                ${product.price || '—'}
              </span>
              {product.sku && (
                <>
                  <span>•</span>
                  <span>SKU: {product.sku}</span>
                </>
              )}
            </div>
          </div>
          <div>
            {forecast?.stockout_risk_level && getRiskBadge(forecast.stockout_risk_level)}
          </div>
        </div>

        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center">
            <Spinner size="lg" />
            <p className="text-xs text-gray-500 mt-2">Computing competitor sales velocity & stockout forecast...</p>
          </div>
        ) : (
          <>
            {/* Key Metric Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Card className="p-3 border-l-4 border-l-primary-500">
                <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Current Stock</div>
                <div className="mt-1 text-xl font-bold text-gray-900 dark:text-white">
                  {forecast?.current_stock !== null && forecast?.current_stock !== undefined
                    ? `${forecast.current_stock} units`
                    : product.stock_quantity !== null && product.stock_quantity !== undefined
                    ? `${product.stock_quantity} units`
                    : 'In Stock'}
                </div>
                <div className="text-[11px] text-gray-400 mt-0.5">
                  {forecast?.is_in_stock ? 'Available' : 'Out of Stock'}
                </div>
              </Card>

              <Card className="p-3 border-l-4 border-l-sky-500">
                <div className="text-[11px] font-semibold text-sky-600 uppercase tracking-wider">Sales Velocity</div>
                <div className="mt-1 text-xl font-bold text-sky-600 dark:text-sky-400">
                  {forecast?.sales_velocity_per_day !== undefined
                    ? `${forecast.sales_velocity_per_day} / day`
                    : '—'}
                </div>
                <div className="text-[11px] text-gray-400 mt-0.5">Depletion run-rate</div>
              </Card>

              <Card className="p-3 border-l-4 border-l-amber-500">
                <div className="text-[11px] font-semibold text-amber-600 uppercase tracking-wider">Days to Stockout</div>
                <div className="mt-1 text-xl font-bold text-amber-600 dark:text-amber-400">
                  {forecast?.days_until_stockout !== null && forecast?.days_until_stockout !== undefined
                    ? `~${forecast.days_until_stockout} days`
                    : '—'}
                </div>
                <div className="text-[11px] text-gray-400 mt-0.5">
                  {forecast?.predicted_stockout_date
                    ? new Date(forecast.predicted_stockout_date).toLocaleDateString()
                    : 'Indeterminate'}
                </div>
              </Card>

              <Card className="p-3 border-l-4 border-l-emerald-500">
                <div className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider">Est. Daily Rev</div>
                <div className="mt-1 text-xl font-bold text-emerald-600 dark:text-emerald-400">
                  ${forecast?.estimated_daily_revenue || 0}
                </div>
                <div className="text-[11px] text-gray-400 mt-0.5">Velocity × Price</div>
              </Card>
            </div>

            {/* Strategic Opportunity Verdict */}
            {forecast?.opportunity_verdict && (
              <div
                className={`p-3.5 rounded-lg border text-xs leading-relaxed ${
                  forecast.stockout_risk_level === 'high' || forecast.stockout_risk_level === 'out_of_stock'
                    ? 'bg-rose-50 border-rose-200 text-rose-900 dark:bg-rose-950/30 dark:border-rose-900 dark:text-rose-200'
                    : forecast.stockout_risk_level === 'medium'
                    ? 'bg-amber-50 border-amber-200 text-amber-900 dark:bg-amber-950/30 dark:border-amber-900 dark:text-amber-200'
                    : 'bg-emerald-50 border-emerald-200 text-emerald-900 dark:bg-emerald-950/30 dark:border-emerald-900 dark:text-emerald-200'
                }`}
              >
                <div className="font-semibold text-sm mb-1 flex items-center gap-1.5">
                  <BoltIcon className="w-4 h-4" />
                  Merchant Intelligence & Opportunity Verdict
                </div>
                {forecast.opportunity_verdict}
              </div>
            )}

            {/* Simulation / Record New Observation Form */}
            <form onSubmit={handleRecordStock} className="p-3.5 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-900 dark:text-white flex items-center gap-1.5">
                  <BuildingStorefrontIcon className="w-4 h-4 text-primary-500" />
                  Record / Simulate Scraped Stock Observation
                </span>
                <span className="text-[11px] text-gray-500">Simulate scraper updates to test velocity</span>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-600 dark:text-gray-300">Stock Count:</label>
                  <input
                    type="number"
                    min="0"
                    placeholder="e.g. 15"
                    value={newStock}
                    onChange={(e) => setNewStock(e.target.value)}
                    className="w-24 text-xs px-2.5 py-1.5 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-600 dark:text-gray-300">In Stock:</label>
                  <input
                    type="checkbox"
                    checked={inStock}
                    onChange={(e) => setInStock(e.target.checked)}
                    className="w-4 h-4 rounded text-primary-600 focus:ring-primary-500"
                  />
                </div>

                <Button
                  type="submit"
                  size="sm"
                  variant="primary"
                  disabled={submitting}
                >
                  <PlusIcon className="w-3.5 h-3.5 mr-1" />
                  {submitting ? 'Recording...' : 'Record Observation'}
                </Button>
              </div>
            </form>

            {/* Historical Observations Timeline */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
                  Stock Depletion & Restock Log ({history.length} records)
                </h4>
                <div className="text-[11px] text-gray-500">
                  Total Sold: <strong className="text-gray-900 dark:text-white">{forecast?.total_units_sold || 0} units</strong> • Restocks: <strong className="text-gray-900 dark:text-white">{forecast?.total_restocks || 0}</strong>
                </div>
              </div>

              {history.length === 0 ? (
                <div className="py-6 text-center text-xs text-gray-400 bg-gray-50 dark:bg-gray-800/40 rounded-lg">
                  No stock change observations recorded yet. Use the simulator above or execute a scrape run to start tracking.
                </div>
              ) : (
                <div className="max-h-48 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-gray-50 dark:bg-gray-800/80 border-b border-gray-200 dark:border-gray-700 text-gray-500">
                        <th className="py-2 px-3 font-semibold">Timestamp</th>
                        <th className="py-2 px-3 font-semibold">Recorded Stock</th>
                        <th className="py-2 px-3 font-semibold">Change Delta</th>
                        <th className="py-2 px-3 font-semibold">Event Type</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                      {history.map((h) => (
                        <tr key={h.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30">
                          <td className="py-2 px-3 text-gray-500">
                            {h.recorded_at ? new Date(h.recorded_at).toLocaleString() : '—'}
                          </td>
                          <td className="py-2 px-3 font-semibold text-gray-900 dark:text-white">
                            {h.stock_quantity !== null ? `${h.stock_quantity} units` : (h.in_stock ? 'In Stock' : '0 (OOS)')}
                          </td>
                          <td className="py-2 px-3 font-medium">
                            {h.delta < 0 ? (
                              <span className="text-rose-600 flex items-center gap-1">
                                <ArrowTrendingDownIcon className="w-3.5 h-3.5" />
                                {h.delta} units
                              </span>
                            ) : h.delta > 0 ? (
                              <span className="text-emerald-600 flex items-center gap-1">
                                <ArrowTrendingUpIcon className="w-3.5 h-3.5" />
                                +{h.delta} units
                              </span>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                          </td>
                          <td className="py-2 px-3">
                            <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium uppercase ${
                              h.change_type === 'depletion'
                                ? 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300'
                                : h.change_type === 'restock'
                                ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                                : h.change_type === 'out_of_stock'
                                ? 'bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300'
                                : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                            }`}>
                              {h.change_type.replace('_', ' ')}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}

        <div className="flex justify-end pt-3 border-t border-gray-200 dark:border-gray-700">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  )
}
