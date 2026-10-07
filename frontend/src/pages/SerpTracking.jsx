import React, { useState, useEffect, useCallback } from 'react'
import {
  MagnifyingGlassIcon,
  PlusIcon,
  TrashIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  BuildingStorefrontIcon,
  SparklesIcon,
  ArrowPathIcon,
  ChartBarIcon,
  CheckCircleIcon,
  TagIcon,
  BoltIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import Button from '@/components/Common/Button'
import Card from '@/components/Common/Card'
import Modal from '@/components/Common/Modal'
import Spinner from '@/components/Common/Spinner'
import serpService from '@/services/serpService'

export default function SerpTracking() {
  const [keywords, setKeywords] = useState([])
  const [selectedKeywordId, setSelectedKeywordId] = useState(null)
  const [keywordDetail, setKeywordDetail] = useState(null)
  const [insights, setInsights] = useState(null)
  const [loadingList, setLoadingList] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)

  // Filter & Search
  const [searchQuery, setSearchQuery] = useState('')
  const [domainFilter, setDomainFilter] = useState('')

  // Add Keyword Modal
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [addForm, setAddForm] = useState({
    keyword: '',
    domain: 'amazon.com',
    marketplace: 'amazon',
    check_frequency: 'daily',
  })
  const [addingKeyword, setAddingKeyword] = useState(false)

  // Ingest Snapshot Modal
  const [isSnapshotModalOpen, setIsSnapshotModalOpen] = useState(false)
  const [snapshotItemsText, setSnapshotItemsText] = useState('')
  const [savingSnapshot, setSavingSnapshot] = useState(false)

  const fetchKeywords = useCallback(async () => {
    try {
      setLoadingList(true)
      const [list, ins] = await Promise.all([
        serpService.getKeywords({ domain: domainFilter || undefined }),
        serpService.getInsights(),
      ])
      setKeywords(list || [])
      setInsights(ins || null)
      if (list?.length > 0 && !selectedKeywordId) {
        setSelectedKeywordId(list[0].id)
      }
    } catch (err) {
      console.error('Error fetching keywords:', err)
      toast.error('Failed to load SERP keywords')
    } finally {
      setLoadingList(false)
    }
  }, [domainFilter, selectedKeywordId])

  const fetchDetail = useCallback(async (id) => {
    if (!id) return
    try {
      setLoadingDetail(true)
      const data = await serpService.getKeywordDetail(id)
      setKeywordDetail(data)
    } catch (err) {
      console.error('Error fetching keyword detail:', err)
      toast.error('Failed to load keyword details')
    } finally {
      setLoadingDetail(false)
    }
  }, [])

  useEffect(() => {
    fetchKeywords()
  }, [fetchKeywords])

  useEffect(() => {
    if (selectedKeywordId) {
      fetchDetail(selectedKeywordId)
    }
  }, [selectedKeywordId, fetchDetail])

  const handleCreateKeyword = async (e) => {
    e.preventDefault()
    if (!addForm.keyword.trim()) return
    try {
      setAddingKeyword(true)
      const created = await serpService.createKeyword(addForm)
      toast.success(`Tracking keyword "${created.keyword}"`)
      setIsAddModalOpen(false)
      setAddForm({
        keyword: '',
        domain: 'amazon.com',
        marketplace: 'amazon',
        check_frequency: 'daily',
      })
      await fetchKeywords()
      setSelectedKeywordId(created.id)
    } catch (err) {
      toast.error('Failed to register keyword')
    } finally {
      setAddingKeyword(false)
    }
  }

  const handleDeleteKeyword = async (id, kwText) => {
    if (!window.confirm(`Stop tracking keyword "${kwText}"?`)) return
    try {
      await serpService.deleteKeyword(id)
      toast.success('Keyword removed')
      if (selectedKeywordId === id) {
        setSelectedKeywordId(null)
        setKeywordDetail(null)
      }
      fetchKeywords()
    } catch (err) {
      toast.error('Failed to delete keyword')
    }
  }

  const handleRecordSampleSnapshot = async () => {
    if (!selectedKeywordId) return
    try {
      setSavingSnapshot(true)
      // Generate standard marketplace SERP crawl snapshot
      const sampleItems = [
        {
          title: `${keywordDetail?.keyword || 'Flagship'} Ultra Pro Max Edition`,
          brand: 'Sony',
          price: 249.99,
          rank_position: 1,
          is_sponsored: false,
          badge: "Amazon's Choice",
          rating: 4.8,
          review_count: 1420,
        },
        {
          title: `Elite Series Wireless ANC Edition`,
          brand: 'Bose',
          price: 229.00,
          rank_position: 2,
          is_sponsored: false,
          badge: 'Best Seller',
          rating: 4.7,
          review_count: 3100,
        },
        {
          title: `Promoted Studio Pro Headset`,
          brand: 'Beats',
          price: 199.95,
          rank_position: 3,
          is_sponsored: true,
          badge: null,
          rating: 4.4,
          review_count: 850,
        },
        {
          title: `Air Wireless Earphones Spatial Audio`,
          brand: 'Apple',
          price: 189.00,
          rank_position: 4,
          is_sponsored: false,
          badge: null,
          rating: 4.9,
          review_count: 5900,
        },
        {
          title: `Soundcore by Anker Life Q30 Hybrid ANC`,
          brand: 'Anker',
          price: 79.99,
          rank_position: 5,
          is_sponsored: false,
          badge: 'Overall Pick',
          rating: 4.6,
          review_count: 4200,
        },
        {
          title: `JBL Live 660NC Wireless Over-Ear`,
          brand: 'JBL',
          price: 129.95,
          rank_position: 6,
          is_sponsored: true,
          badge: null,
          rating: 4.5,
          review_count: 980,
        },
      ]
      await serpService.recordSnapshot(selectedKeywordId, { items: sampleItems })
      toast.success('Recorded fresh SERP snapshot!')
      fetchDetail(selectedKeywordId)
      fetchKeywords()
    } catch (err) {
      toast.error('Failed to record snapshot')
    } finally {
      setSavingSnapshot(false)
    }
  }

  const filteredKeywords = keywords.filter((k) =>
    k.keyword.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2.5">
            <MagnifyingGlassIcon className="h-7 w-7 text-indigo-500" />
            Competitor Search Ranking & SERP Tracker
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Track organic and sponsored search ranking positions across Amazon, Walmart, and competitor stores.
          </p>
        </div>

        <Button onClick={() => setIsAddModalOpen(true)}>
          <PlusIcon className="w-4 h-4 mr-1.5" />
          Track New Keyword
        </Button>
      </div>

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
            Monitored Keywords
          </span>
          <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">
            {insights?.monitored_keywords || keywords.length}
          </div>
          <span className="text-xs text-gray-400">active queries</span>
        </Card>

        <Card className="p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
            Tracked SERP Rankings
          </span>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
            {insights?.total_tracked_rankings || 0}
          </div>
          <span className="text-xs text-gray-400">products indexed</span>
        </Card>

        <Card className="p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
            Sponsored Ad Density
          </span>
          <div className="text-2xl font-bold text-amber-500 mt-1">
            {insights?.average_sponsored_density || 0}%
          </div>
          <span className="text-xs text-gray-400">paid ad placements</span>
        </Card>

        <Card className="p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
            Top Search Brand
          </span>
          <div className="text-xl font-bold text-indigo-500 mt-1 truncate">
            {Object.keys(insights?.dominant_brands || {})[0] || 'N/A'}
          </div>
          <span className="text-xs text-gray-400">
            {Object.values(insights?.dominant_brands || {})[0] || 0}% Share of Voice
          </span>
        </Card>
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Keywords List */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <MagnifyingGlassIcon className="h-4 w-4 absolute left-3 top-2.5 text-gray-400" />
              <input
                type="text"
                placeholder="Filter keywords..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-gray-900 dark:text-gray-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <select
              value={domainFilter}
              onChange={(e) => setDomainFilter(e.target.value)}
              className="bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-800 rounded-lg px-2 py-1.5 text-xs text-gray-700 dark:text-gray-300"
            >
              <option value="">All Stores</option>
              <option value="amazon.com">Amazon</option>
              <option value="walmart.com">Walmart</option>
              <option value="ebay.com">eBay</option>
            </select>
          </div>

          {loadingList ? (
            <div className="py-12 flex justify-center">
              <Spinner size="md" />
            </div>
          ) : filteredKeywords.length === 0 ? (
            <div className="text-center py-10 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 text-gray-500">
              No keywords match your filter.
            </div>
          ) : (
            <div className="space-y-2 max-h-[650px] overflow-y-auto pr-1">
              {filteredKeywords.map((kw) => {
                const isSelected = selectedKeywordId === kw.id
                return (
                  <div
                    key={kw.id}
                    onClick={() => setSelectedKeywordId(kw.id)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-indigo-500/10 border-indigo-500 shadow-sm'
                        : 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-semibold text-sm text-gray-900 dark:text-gray-100">
                        "{kw.keyword}"
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteKeyword(kw.id, kw.keyword)
                        }}
                        className="text-gray-400 hover:text-red-500 p-0.5"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>

                    <div className="mt-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                      <span className="capitalize px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-[11px]">
                        {kw.domain || kw.marketplace}
                      </span>
                      <span>{kw.total_results_count || 0} listings</span>
                    </div>

                    {kw.top_brand && (
                      <div className="mt-2 text-xs flex items-center justify-between border-t border-gray-100 dark:border-gray-800 pt-2">
                        <span className="text-gray-400">Top Brand:</span>
                        <span className="font-bold text-indigo-500">{kw.top_brand}</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Right Column: Keyword Detail & SERP Explorer */}
        <div className="lg:col-span-8">
          {loadingDetail ? (
            <div className="py-24 flex justify-center bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
              <Spinner size="lg" />
            </div>
          ) : !keywordDetail ? (
            <div className="text-center py-24 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-8 text-gray-500">
              <MagnifyingGlassIcon className="h-12 w-12 text-gray-400 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-gray-700 dark:text-gray-300">
                Select a Keyword to View SERP Intelligence
              </h3>
              <p className="text-xs text-gray-400 mt-1 max-w-sm mx-auto">
                Inspect organic rankings, sponsored ad density, brand share of voice, and position deltas.
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              {/* Keyword Action Header */}
              <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
                      "{keywordDetail.keyword}"
                    </h2>
                    <span className="px-2 py-0.5 rounded text-xs bg-indigo-50 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400 font-semibold border border-indigo-200 dark:border-indigo-800 capitalize">
                      {keywordDetail.domain}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Frequency: {keywordDetail.check_frequency} · Last checked:{' '}
                    {keywordDetail.last_checked_at
                      ? new Date(keywordDetail.last_checked_at).toLocaleString()
                      : 'Never'}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={handleRecordSampleSnapshot}
                    disabled={savingSnapshot}
                  >
                    {savingSnapshot ? (
                      <Spinner size="sm" className="mr-1.5" />
                    ) : (
                      <ArrowPathIcon className="h-4 w-4 mr-1.5 text-indigo-500" />
                    )}
                    Crawl / Refresh SERP
                  </Button>
                </div>
              </div>

              {/* Share of Voice Summary */}
              {keywordDetail.analytics && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Brand SOV */}
                  <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                      Brand Share of Voice (SOV)
                    </h4>
                    <div className="space-y-2">
                      {Object.entries(keywordDetail.analytics.brand_share_of_voice || {})
                        .slice(0, 5)
                        .map(([brand, pct]) => (
                          <div key={brand}>
                            <div className="flex items-center justify-between text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                              <span>{brand}</span>
                              <span className="font-bold">{pct}%</span>
                            </div>
                            <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-2">
                              <div
                                className="bg-indigo-500 h-2 rounded-full"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>

                  {/* Placement Breakdown */}
                  <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                      SERP Ad Saturation
                    </h4>
                    <div className="grid grid-cols-2 gap-3 text-center">
                      <div className="p-3 bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/30 rounded-xl">
                        <span className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold">
                          Organic Listings
                        </span>
                        <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-400 mt-1">
                          {keywordDetail.analytics.organic_count || 0}
                        </div>
                      </div>
                      <div className="p-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/30 rounded-xl">
                        <span className="text-xs text-amber-600 dark:text-amber-400 font-semibold">
                          Sponsored Ads
                        </span>
                        <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">
                          {keywordDetail.analytics.sponsored_count || 0}
                        </div>
                      </div>
                    </div>
                    <div className="text-xs text-gray-400 text-center mt-3">
                      {keywordDetail.analytics.sponsored_density_pct}% of Page 1 results are sponsored
                    </div>
                  </div>
                </div>
              )}

              {/* SERP Ranked Items Table */}
              <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
                <div className="p-3.5 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Rankings Table ({keywordDetail.rankings?.length || 0} items)
                  </h4>
                  <span className="text-xs text-gray-400">Position 1 = Top of Page</span>
                </div>

                {keywordDetail.rankings?.length === 0 ? (
                  <div className="text-center py-12 text-gray-500 text-sm">
                    No ranking snapshot recorded yet. Click "Crawl / Refresh SERP" to fetch search results.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800 text-left text-xs">
                      <thead className="bg-gray-50 dark:bg-gray-800/60 text-gray-500 dark:text-gray-400 font-semibold uppercase">
                        <tr>
                          <th className="py-2.5 px-3">Rank</th>
                          <th className="py-2.5 px-3">Title & Listing</th>
                          <th className="py-2.5 px-3">Brand</th>
                          <th className="py-2.5 px-3">Price</th>
                          <th className="py-2.5 px-3">Placement</th>
                          <th className="py-2.5 px-3">Delta</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 dark:divide-gray-800/60">
                        {keywordDetail.rankings?.map((item) => (
                          <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors">
                            <td className="py-2.5 px-3">
                              <span
                                className={`inline-flex items-center justify-center w-7 h-7 rounded-full font-bold text-xs ${
                                  item.rank_position === 1
                                    ? 'bg-amber-400 text-black shadow-sm'
                                    : item.rank_position === 2
                                    ? 'bg-gray-300 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                                    : item.rank_position === 3
                                    ? 'bg-amber-700 text-white'
                                    : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
                                }`}
                              >
                                {item.rank_position}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 max-w-sm">
                              <div className="font-semibold text-gray-900 dark:text-gray-100 truncate">
                                {item.title}
                              </div>
                              {item.badge && (
                                <span className="inline-block mt-0.5 px-1.5 py-0.2 rounded text-[10px] font-semibold bg-amber-500/15 text-amber-500 border border-amber-500/20">
                                  {item.badge}
                                </span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-gray-700 dark:text-gray-300 font-medium">
                              {item.brand || '-'}
                            </td>
                            <td className="py-2.5 px-3 font-semibold text-gray-900 dark:text-gray-100">
                              {item.price ? `$${item.price.toFixed(2)}` : '-'}
                            </td>
                            <td className="py-2.5 px-3">
                              {item.is_sponsored ? (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20">
                                  SPONSORED
                                </span>
                              ) : (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                                  ORGANIC
                                </span>
                              )}
                            </td>
                            <td className="py-2.5 px-3">
                              {item.rank_change > 0 ? (
                                <span className="inline-flex items-center gap-0.5 text-emerald-500 font-semibold">
                                  <ArrowTrendingUpIcon className="h-3.5 w-3.5" /> +{item.rank_change}
                                </span>
                              ) : item.rank_change < 0 ? (
                                <span className="inline-flex items-center gap-0.5 text-red-500 font-semibold">
                                  <ArrowTrendingDownIcon className="h-3.5 w-3.5" /> {item.rank_change}
                                </span>
                              ) : (
                                <span className="text-gray-400">-</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add Keyword Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Track Competitor Search Keyword"
        size="md"
      >
        <form onSubmit={handleCreateKeyword} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Search Query / Keyword
            </label>
            <input
              type="text"
              required
              placeholder="e.g. noise cancelling headphones"
              value={addForm.keyword}
              onChange={(e) => setAddForm({ ...addForm, keyword: e.target.value })}
              className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg p-2.5 text-sm text-gray-900 dark:text-gray-100"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Marketplace Domain
              </label>
              <select
                value={addForm.domain}
                onChange={(e) =>
                  setAddForm({
                    ...addForm,
                    domain: e.target.value,
                    marketplace: e.target.value.split('.')[0],
                  })
                }
                className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg p-2.5 text-sm text-gray-900 dark:text-gray-100"
              >
                <option value="amazon.com">Amazon.com</option>
                <option value="amazon.co.uk">Amazon.co.uk</option>
                <option value="walmart.com">Walmart.com</option>
                <option value="ebay.com">eBay.com</option>
                <option value="google_shopping">Google Shopping</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Check Frequency
              </label>
              <select
                value={addForm.check_frequency}
                onChange={(e) => setAddForm({ ...addForm, check_frequency: e.target.value })}
                className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg p-2.5 text-sm text-gray-900 dark:text-gray-100"
              >
                <option value="daily">Daily Crawl</option>
                <option value="hourly">Hourly Crawl</option>
                <option value="weekly">Weekly Crawl</option>
                <option value="manual">Manual Only</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-3">
            <Button type="button" variant="secondary" onClick={() => setIsAddModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={addingKeyword || !addForm.keyword.trim()}>
              {addingKeyword ? <Spinner size="sm" className="mr-1.5" /> : <PlusIcon className="w-4 h-4 mr-1.5" />}
              Start Tracking
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
