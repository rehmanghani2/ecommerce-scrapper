import React, { useState, useEffect } from 'react'
import {
  TrophyIcon,
  ShoppingBagIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  AdjustmentsHorizontalIcon,
  ClockIcon,
  BuildingStorefrontIcon,
  CalculatorIcon,
  PlusCircleIcon,
} from '@heroicons/react/24/outline'

import Modal from '@/components/Common/Modal'
import Spinner from '@/components/Common/Spinner'
import Button from '@/components/Common/Button'
import { formatPrice, formatDate } from '@/utils/helpers'
import buyboxService from '@/services/buyboxService'

const formatCurrency = (val) => {
  if (val === null || val === undefined) return '—'
  return `$${Number(val).toFixed(2)}`
}

const formatDateTime = (val) => {
  if (!val) return '—'
  return formatDate(val, 'MMM d, yyyy h:mm a')
}

export default function BuyBoxTrackerModal({ product, isOpen, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview') // 'overview', 'simulator', 'history', 'record'

  // Simulator state
  const [simPrice, setSimPrice] = useState('')
  const [simFulfillment, setSimFulfillment] = useState('fba')
  const [simulating, setSimulating] = useState(false)
  const [simResult, setSimResult] = useState(null)

  // Record observation state
  const [obsWinner, setObsWinner] = useState('')
  const [obsPrice, setObsPrice] = useState('')
  const [obsFulfillment, setObsFulfillment] = useState('fba')
  const [obsSuppressed, setObsSuppressed] = useState(false)
  const [recording, setRecording] = useState(false)

  const fetchBuyBox = async () => {
    if (!product?.id) return
    try {
      setLoading(true)
      setError(null)
      const res = await buyboxService.getProductBuyBox(product.id)
      setData(res)
      if (res?.tracked_seller_price || res?.winner_price) {
        setSimPrice(String(res.tracked_seller_price || res.winner_price || ''))
        setSimFulfillment(res.tracked_seller_fulfillment || 'fba')
      }
    } catch (err) {
      console.error('Error fetching buy box:', err)
      setError(err?.response?.data?.detail || err.message || 'Failed to load Buy Box details')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen && product?.id) {
      fetchBuyBox()
      setSimResult(null)
    }
  }, [isOpen, product?.id])

  const handleSimulate = async (e) => {
    e?.preventDefault()
    if (!product?.id || !data) return
    try {
      setSimulating(true)
      const payload = {
        winner_price: parseFloat(data.winner_price || product.price || 0),
        winner_fulfillment: data.fulfillment_type || 'fba',
        seller_price: parseFloat(simPrice || data.tracked_seller_price || product.price || 0),
        seller_fulfillment: simFulfillment,
        is_suppressed: data.is_suppressed || false,
        is_amazon_sold: (data.current_winner || '').toLowerCase().includes('amazon'),
      }
      const res = await buyboxService.evaluateWinProbability(product.id, payload)
      setSimResult(res)
    } catch (err) {
      alert('Simulation error: ' + (err?.response?.data?.detail || err.message))
    } finally {
      setSimulating(false)
    }
  }

  const handleRecordObservation = async (e) => {
    e?.preventDefault()
    if (!product?.id) return
    try {
      setRecording(true)
      const payload = {
        current_winner: obsWinner.trim() || data?.current_winner || 'Competitor',
        winner_price: parseFloat(obsPrice || data?.winner_price || product.price || 0),
        fulfillment_type: obsFulfillment,
        is_suppressed: obsSuppressed,
        tracked_seller_name: data?.tracked_seller_name || 'My Store',
        tracked_seller_price: parseFloat(data?.tracked_seller_price || product.price || 0),
        tracked_seller_fulfillment: data?.tracked_seller_fulfillment || 'fba',
      }
      const updated = await buyboxService.recordObservation(product.id, payload)
      setData(updated)
      setObsWinner('')
      setObsPrice('')
      setActiveTab('history')
    } catch (err) {
      alert('Record observation error: ' + (err?.response?.data?.detail || err.message))
    } finally {
      setRecording(false)
    }
  }

  const getWinColorClass = (pct) => {
    if (pct >= 70) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
    if (pct >= 40) return 'text-amber-400 bg-amber-500/10 border-amber-500/30'
    return 'text-rose-400 bg-rose-500/10 border-rose-500/30'
  }

  const getProgressColor = (pct) => {
    if (pct >= 70) return 'bg-emerald-500'
    if (pct >= 40) return 'bg-amber-500'
    return 'bg-rose-500'
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <TrophyIcon className="h-6 w-6 text-amber-400" />
          <span>Buy Box Intelligence: {product?.name?.substring(0, 35)}...</span>
        </div>
      }
      size="xl"
    >
      <div className="space-y-5">
        {/* Navigation tabs */}
        <div className="flex border-b border-gray-200 dark:border-gray-800 gap-4 text-sm font-medium">
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            className={`pb-2.5 px-1 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === 'overview'
                ? 'border-amber-500 text-amber-500 dark:text-amber-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <TrophyIcon className="w-4 h-4" />
            Live State & Win Odds
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('simulator')}
            className={`pb-2.5 px-1 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === 'simulator'
                ? 'border-amber-500 text-amber-500 dark:text-amber-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <CalculatorIcon className="w-4 h-4" />
            Pricing Strategy Simulator
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('history')}
            className={`pb-2.5 px-1 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === 'history'
                ? 'border-amber-500 text-amber-500 dark:text-amber-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <ClockIcon className="w-4 h-4" />
            Ownership History & Handoffs ({data?.history?.length || 0})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('record')}
            className={`pb-2.5 px-1 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === 'record'
                ? 'border-amber-500 text-amber-500 dark:text-amber-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <PlusCircleIcon className="w-4 h-4" />
            Record Observation
          </button>
        </div>

        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center">
            <Spinner size="lg" />
            <span className="text-xs text-gray-400 mt-3">Evaluating Buy Box parameters...</span>
          </div>
        ) : error ? (
          <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-sm">
            {error}
          </div>
        ) : data ? (
          <>
            {/* OVERVIEW TAB */}
            {activeTab === 'overview' && (
              <div className="space-y-4">
                {/* Status Header Banner */}
                <div className="p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-gray-900 border-gray-800">
                  <div className="flex items-center gap-3">
                    <div className="p-3 bg-gray-800 rounded-xl">
                      {data.is_suppressed ? (
                        <ExclamationTriangleIcon className="w-6 h-6 text-amber-400" />
                      ) : data.is_tracked_seller_winner ? (
                        <CheckCircleIcon className="w-6 h-6 text-emerald-400" />
                      ) : (
                        <XCircleIcon className="w-6 h-6 text-rose-400" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold uppercase text-gray-400">Current Ownership</span>
                        {data.is_suppressed ? (
                          <span className="px-2 py-0.5 rounded text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                            Suppressed
                          </span>
                        ) : data.is_tracked_seller_winner ? (
                          <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                            Won (Held)
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                            Lost to Competitor
                          </span>
                        )}
                        <span className="text-xs uppercase bg-gray-800 text-gray-300 px-2 py-0.5 rounded border border-gray-700">
                          {data.marketplace}
                        </span>
                      </div>
                      <div className="text-lg font-bold text-gray-100 mt-1 flex items-center gap-2">
                        <span>{data.is_suppressed ? 'No Buy Box Awarded' : data.current_winner}</span>
                        {!data.is_suppressed && (
                          <span className="text-xs px-2 py-0.5 bg-gray-800 text-gray-300 rounded font-semibold uppercase">
                            {data.fulfillment_type?.toUpperCase()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="text-right sm:border-l sm:border-gray-800 sm:pl-6 w-full sm:w-auto flex sm:flex-col justify-between items-center sm:items-end">
                    <span className="text-xs font-semibold text-gray-400 uppercase">Current Winner Price</span>
                    <span className="text-2xl font-extrabold text-amber-400">
                      {formatCurrency(data.winner_price)}
                    </span>
                  </div>
                </div>

                {/* Key Metrics Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {/* Metric 1: Win Probability */}
                  <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-semibold uppercase text-gray-400">Win Probability</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-bold border ${getWinColorClass(data.win_probability_pct)}`}>
                        {data.win_probability_pct}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${getProgressColor(data.win_probability_pct)}`}
                        style={{ width: `${Math.min(100, Math.max(0, data.win_probability_pct))}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-400 line-clamp-2 mt-1">{data.status_verdict}</p>
                  </div>

                  {/* Metric 2: Optimal Target Winning Price */}
                  <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-1">
                    <span className="text-xs font-semibold uppercase text-gray-400">Target Winning Price (P*)</span>
                    <div className="text-2xl font-bold text-emerald-400">
                      {formatCurrency(data.target_winning_price)}
                    </div>
                    <div className="text-xs text-gray-400 flex items-center gap-1">
                      {data.target_winning_price < (data.tracked_seller_price || data.winner_price) ? (
                        <span className="text-amber-400 flex items-center">
                          <ArrowTrendingDownIcon className="w-3.5 h-3.5 mr-0.5" />
                          Requires undercut to displace
                        </span>
                      ) : (
                        <span className="text-emerald-400 flex items-center">
                          <CheckCircleIcon className="w-3.5 h-3.5 mr-0.5" />
                          Parity / FBA advantage
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Metric 3: Win Share */}
                  <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-1">
                    <span className="text-xs font-semibold uppercase text-gray-400">Historic Win Share</span>
                    <div className="text-2xl font-bold text-indigo-300">
                      {data.analytics?.win_share_pct || 0}%
                    </div>
                    <span className="text-xs text-gray-400">
                      Over {data.analytics?.total_observations || 0} tracked observations
                    </span>
                  </div>
                </div>

                {/* Details Breakdown */}
                <div className="bg-gray-900/60 border border-gray-800 p-4 rounded-xl space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400">Your Store Position</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                    <div>
                      <div className="text-gray-500">Tracked Merchant</div>
                      <div className="font-semibold text-gray-200 mt-0.5">{data.tracked_seller_name || 'My Store'}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Your Offer Price</div>
                      <div className="font-semibold text-gray-200 mt-0.5">{formatCurrency(data.tracked_seller_price)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Fulfillment Method</div>
                      <div className="font-semibold text-gray-200 uppercase mt-0.5">{data.tracked_seller_fulfillment}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Competitors Competing</div>
                      <div className="font-semibold text-gray-200 mt-0.5">{data.competing_sellers_count || 1} sellers</div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* SIMULATOR TAB */}
            {activeTab === 'simulator' && (
              <div className="space-y-4">
                <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
                  <div className="flex items-center gap-2 text-sm font-bold text-gray-200">
                    <CalculatorIcon className="w-5 h-5 text-indigo-400" />
                    <span>Test Different Pricing & Fulfillment Scenarios</span>
                  </div>
                  <p className="text-xs text-gray-400">
                    Simulate how lowering or raising your price, or switching between FBA (Fulfilled by Amazon) and FBM
                    (Fulfilled by Merchant) alters your Buy Box win rotation against{' '}
                    <strong className="text-gray-200">{data.current_winner}</strong> (${data.winner_price}).
                  </p>

                  <form onSubmit={handleSimulate} className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Your Simulated Price ($)</label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={simPrice}
                        onChange={(e) => setSimPrice(e.target.value)}
                        placeholder="e.g. 74.99"
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-amber-500"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Your Fulfillment Channel</label>
                      <select
                        value={simFulfillment}
                        onChange={(e) => setSimFulfillment(e.target.value)}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-amber-500"
                      >
                        <option value="fba">FBA (Fulfilled by Amazon / 2-Day)</option>
                        <option value="fbm">FBM (Merchant Fulfilled)</option>
                      </select>
                    </div>

                    <div className="flex items-end">
                      <Button
                        type="submit"
                        variant="primary"
                        className="w-full justify-center"
                        isLoading={simulating}
                      >
                        Calculate Odds
                      </Button>
                    </div>
                  </form>
                </div>

                {/* Simulation Result Display */}
                {simResult && (
                  <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-3 animate-fade-in">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-gray-400">Simulation Output</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-bold border ${getWinColorClass(simResult.win_probability_pct)}`}>
                        {simResult.win_probability_pct}% Win Chance
                      </span>
                    </div>

                    <div className="w-full bg-gray-800 rounded-full h-2.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${getProgressColor(simResult.win_probability_pct)}`}
                        style={{ width: `${Math.min(100, Math.max(0, simResult.win_probability_pct))}%` }}
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3 pt-2 text-xs">
                      <div className="p-3 bg-gray-800/60 rounded-lg border border-gray-700/60">
                        <span className="text-gray-400 block mb-0.5">Recommended Winning Target</span>
                        <span className="text-lg font-bold text-emerald-400">{formatCurrency(simResult.target_winning_price)}</span>
                      </div>
                      <div className="p-3 bg-gray-800/60 rounded-lg border border-gray-700/60">
                        <span className="text-gray-400 block mb-0.5">Algorithm Verdict</span>
                        <span className="font-medium text-gray-200">{simResult.status_verdict}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* HISTORY TAB */}
            {activeTab === 'history' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-gray-400">
                  <span>Logged handoffs and state transition events</span>
                  <span className="font-semibold text-gray-300">{data.history?.length || 0} events recorded</span>
                </div>

                {(!data.history || data.history.length === 0) ? (
                  <div className="text-center py-10 bg-gray-900/50 rounded-xl border border-gray-800 p-6 text-gray-400">
                    <ClockIcon className="h-8 w-8 text-gray-600 mx-auto mb-2" />
                    <p className="text-sm">No historical Buy Box transitions logged yet.</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto border border-gray-800 rounded-xl">
                    <table className="min-w-full divide-y divide-gray-800 text-left text-xs">
                      <thead className="bg-gray-900 text-gray-400 uppercase font-semibold">
                        <tr>
                          <th className="py-2.5 px-3">Event</th>
                          <th className="py-2.5 px-3">Winner</th>
                          <th className="py-2.5 px-3">Channel</th>
                          <th className="py-2.5 px-3">Winning Price</th>
                          <th className="py-2.5 px-3">Delta</th>
                          <th className="py-2.5 px-3">Recorded At</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800/60 bg-gray-900/30">
                        {data.history.map((h) => (
                          <tr key={h.id} className="hover:bg-gray-800/30 transition-colors">
                            <td className="py-2.5 px-3">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded font-bold uppercase text-[10px] ${
                                h.event_type === 'won'
                                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                  : h.event_type === 'lost'
                                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                  : h.event_type === 'suppressed'
                                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                  : 'bg-gray-800 text-gray-300'
                              }`}>
                                {h.event_type}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 font-semibold text-gray-200">
                              {h.winner_name || 'N/A'}
                            </td>
                            <td className="py-2.5 px-3 uppercase text-gray-400">
                              {h.fulfillment_type || 'FBA'}
                            </td>
                            <td className="py-2.5 px-3 font-bold text-amber-300">
                              {formatCurrency(h.winner_price)}
                            </td>
                            <td className="py-2.5 px-3">
                              {h.price_delta_vs_previous > 0 ? (
                                <span className="text-rose-400 font-medium">+{formatCurrency(h.price_delta_vs_previous)}</span>
                              ) : h.price_delta_vs_previous < 0 ? (
                                <span className="text-emerald-400 font-medium">{formatCurrency(h.price_delta_vs_previous)}</span>
                              ) : (
                                <span className="text-gray-500">$0.00</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-gray-400">
                              {formatDateTime(h.recorded_at)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* RECORD OBSERVATION TAB */}
            {activeTab === 'record' && (
              <form onSubmit={handleRecordObservation} className="p-4 bg-gray-900 border border-gray-800 rounded-xl space-y-4">
                <div className="flex items-center gap-2 text-sm font-bold text-gray-200">
                  <PlusCircleIcon className="w-5 h-5 text-amber-400" />
                  <span>Manual or Scraped Buy Box Snapshot Entry</span>
                </div>
                <p className="text-xs text-gray-400">
                  Inject a freshly observed Buy Box crawl state for this ASIN/SKU. The system will detect if ownership
                  transitioned (won/lost/suppressed) and log an event.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">Buy Box Winner Name</label>
                    <input
                      type="text"
                      value={obsWinner}
                      onChange={(e) => setObsWinner(e.target.value)}
                      placeholder="e.g. My Store or Amazon.com"
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-amber-500"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">Winning Price ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={obsPrice}
                      onChange={(e) => setObsPrice(e.target.value)}
                      placeholder="e.g. 89.99"
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-amber-500"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">Winner Fulfillment</label>
                    <select
                      value={obsFulfillment}
                      onChange={(e) => setObsFulfillment(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-amber-500"
                    >
                      <option value="fba">FBA (Fulfilled by Amazon)</option>
                      <option value="fbm">FBM (Merchant Fulfilled)</option>
                    </select>
                  </div>

                  <div className="flex items-center pt-5">
                    <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-gray-300">
                      <input
                        type="checkbox"
                        checked={obsSuppressed}
                        onChange={(e) => setObsSuppressed(e.target.checked)}
                        className="rounded border-gray-700 bg-gray-800 text-amber-500 focus:ring-amber-500"
                      />
                      <span>Buy Box is Suppressed (No Add to Cart button)</span>
                    </label>
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <Button
                    type="submit"
                    variant="primary"
                    isLoading={recording}
                  >
                    Save Buy Box Observation
                  </Button>
                </div>
              </form>
            )}
          </>
        ) : null}
      </div>
    </Modal>
  )
}
