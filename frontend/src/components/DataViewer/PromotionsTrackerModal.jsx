import React, { useState, useEffect, useCallback } from 'react'
import {
  TagIcon,
  TicketIcon,
  SparklesIcon,
  PlusIcon,
  TrashIcon,
  ClipboardDocumentCheckIcon,
  ClipboardDocumentIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowTrendingDownIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  ArrowPathIcon,
  BuildingStorefrontIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import Modal from '@/components/Common/Modal'
import Button from '@/components/Common/Button'
import Card from '@/components/Common/Card'
import Spinner from '@/components/Common/Spinner'
import promotionService from '@/services/promotionService'

export default function PromotionsTrackerModal({ product, isOpen, onClose }) {
  const isCatalogMode = !product

  // Active tab: 'active' | 'detect' | 'create' (or 'catalog' for catalog mode)
  const [activeTab, setActiveTab] = useState(isCatalogMode ? 'catalog' : 'active')

  // Product promotions state
  const [promotions, setPromotions] = useState([])
  const [loading, setLoading] = useState(false)
  const [copiedCode, setCopiedCode] = useState(null)

  // Detector state
  const [rawText, setRawText] = useState('')
  const [useAi, setUseAi] = useState(false)
  const [detecting, setDetecting] = useState(false)
  const [detectedPromos, setDetectedPromos] = useState([])

  // Manual creation state
  const [formData, setFormData] = useState({
    promo_type: 'coupon_code',
    title: '',
    coupon_code: '',
    discount_type: 'percentage',
    discount_value: '',
    minimum_spend: '',
    bogo_buy_qty: '1',
    bogo_get_qty: '1',
    bogo_discount_pct: '100',
    volume_min_qty: '3',
    banner_text: '',
    description: '',
  })
  const [creating, setCreating] = useState(false)

  // Catalog mode state
  const [catalogPromos, setCatalogPromos] = useState([])
  const [catalogTotal, setCatalogTotal] = useState(0)
  const [catalogInsights, setCatalogInsights] = useState(null)
  const [filterType, setFilterType] = useState('')
  const [filterDomain, setFilterDomain] = useState('')

  // Fetch product promotions
  const fetchProductPromotions = useCallback(async () => {
    if (!product?.id) return
    try {
      setLoading(true)
      const data = await promotionService.getProductPromotions(product.id)
      setPromotions(data || [])
    } catch (err) {
      console.error('Error fetching product promotions:', err)
      toast.error('Failed to load promotions')
    } finally {
      setLoading(false)
    }
  }, [product?.id])

  // Fetch catalog promotions & insights
  const fetchCatalogData = useCallback(async () => {
    try {
      setLoading(true)
      const [promoRes, insightRes] = await Promise.all([
        promotionService.getActivePromotions({
          promo_type: filterType || undefined,
          domain: filterDomain || undefined,
          limit: 50,
        }),
        promotionService.getPromotionInsights(filterDomain || undefined),
      ])
      setCatalogPromos(promoRes?.items || [])
      setCatalogTotal(promoRes?.total || 0)
      setCatalogInsights(insightRes || null)
    } catch (err) {
      console.error('Error fetching catalog promotions:', err)
      toast.error('Failed to load catalog promotions')
    } finally {
      setLoading(false)
    }
  }, [filterType, filterDomain])

  useEffect(() => {
    if (!isOpen) return
    if (isCatalogMode) {
      fetchCatalogData()
    } else {
      fetchProductPromotions()
    }
  }, [isOpen, isCatalogMode, fetchProductPromotions, fetchCatalogData])

  const handleCopyCode = (code) => {
    if (!code) return
    navigator.clipboard.writeText(code)
    setCopiedCode(code)
    toast.success(`Copied code "${code}"`)
    setTimeout(() => setCopiedCode(null), 2500)
  }

  const handleToggle = async (promoId) => {
    try {
      await promotionService.togglePromotion(promoId)
      toast.success('Promotion status updated')
      if (isCatalogMode) fetchCatalogData()
      else fetchProductPromotions()
    } catch (err) {
      toast.error('Failed to update promotion status')
    }
  }

  const handleDelete = async (promoId) => {
    if (!window.confirm('Delete this promotion record?')) return
    try {
      await promotionService.deletePromotion(promoId)
      toast.success('Promotion deleted')
      if (isCatalogMode) fetchCatalogData()
      else fetchProductPromotions()
    } catch (err) {
      toast.error('Failed to delete promotion')
    }
  }

  const handleDetect = async (e) => {
    e.preventDefault()
    if (!rawText.trim()) return
    try {
      setDetecting(true)
      const results = await promotionService.detectPromotions({
        text: rawText,
        product_title: product?.name || '',
        original_price: Number(product?.price || 0),
        use_ai: useAi,
      })
      setDetectedPromos(results || [])
      if (results?.length > 0) {
        toast.success(`Detected ${results.length} promotion(s)!`)
      } else {
        toast('No active promotion patterns found in this text.', { icon: '🔍' })
      }
    } catch (err) {
      toast.error('Promotion detection failed')
    } finally {
      setDetecting(false)
    }
  }

  const handleSaveDetected = async (detectedItem) => {
    if (!product?.id) return
    try {
      await promotionService.createPromotion(product.id, {
        promo_type: detectedItem.promo_type || 'coupon_code',
        title: detectedItem.title || 'Detected Promotion',
        coupon_code: detectedItem.coupon_code,
        discount_type: detectedItem.discount_type || 'percentage',
        discount_value: detectedItem.discount_value,
        bogo_buy_qty: detectedItem.bogo_buy_qty,
        bogo_get_qty: detectedItem.bogo_get_qty,
        bogo_discount_pct: detectedItem.bogo_discount_pct,
        volume_min_qty: detectedItem.volume_min_qty,
        minimum_spend: detectedItem.minimum_spend,
        banner_text: detectedItem.banner_text,
        description: detectedItem.description,
      })
      toast.success('Promotion attached to product!')
      fetchProductPromotions()
      setActiveTab('active')
    } catch (err) {
      toast.error('Failed to attach promotion')
    }
  }

  const handleManualCreate = async (e) => {
    e.preventDefault()
    if (!product?.id) return
    try {
      setCreating(true)
      await promotionService.createPromotion(product.id, {
        ...formData,
        discount_value: formData.discount_value ? Number(formData.discount_value) : undefined,
        minimum_spend: formData.minimum_spend ? Number(formData.minimum_spend) : undefined,
        bogo_buy_qty: formData.bogo_buy_qty ? Number(formData.bogo_buy_qty) : undefined,
        bogo_get_qty: formData.bogo_get_qty ? Number(formData.bogo_get_qty) : undefined,
        bogo_discount_pct: formData.bogo_discount_pct ? Number(formData.bogo_discount_pct) : undefined,
        volume_min_qty: formData.volume_min_qty ? Number(formData.volume_min_qty) : undefined,
      })
      toast.success('Promotion registered successfully')
      fetchProductPromotions()
      setActiveTab('active')
      setFormData({
        promo_type: 'coupon_code',
        title: '',
        coupon_code: '',
        discount_type: 'percentage',
        discount_value: '',
        minimum_spend: '',
        bogo_buy_qty: '1',
        bogo_get_qty: '1',
        bogo_discount_pct: '100',
        volume_min_qty: '3',
        banner_text: '',
        description: '',
      })
    } catch (err) {
      toast.error('Failed to create promotion')
    } finally {
      setCreating(false)
    }
  }

  // Best promotion calculation for single product
  const origPrice = Number(product?.price || 0)
  const activeList = promotions.filter((p) => p.is_active)
  const bestSavings = activeList.length > 0 ? Math.max(...activeList.map((p) => p.savings_amount || 0)) : 0
  const bestEffectivePrice = origPrice > 0 ? Math.max(0, origPrice - bestSavings) : 0

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <TicketIcon className="h-6 w-6 text-emerald-500" />
          <span>
            {isCatalogMode
              ? 'Competitor Promotion & Coupon Intelligence'
              : `Promotions & Coupons: ${product?.name?.substring(0, 40)}...`}
          </span>
        </div>
      }
      size="2xl"
    >
      <div className="space-y-6">
        {/* Top Product Context Banner (Single Product Mode) */}
        {!isCatalogMode && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div>
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Listed Retail Price
              </div>
              <div className="text-2xl font-bold text-gray-200 mt-1">
                ${origPrice.toFixed(2)}
              </div>
              <div className="text-xs text-gray-500 mt-0.5">{product?.source_domain || 'Competitor listing'}</div>
            </div>

            <div>
              <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                Effective Net Price
              </div>
              <div className="text-2xl font-bold text-emerald-400 mt-1 flex items-center gap-1.5">
                ${bestEffectivePrice.toFixed(2)}
                {bestSavings > 0 && (
                  <ArrowTrendingDownIcon className="h-5 w-5 text-emerald-400" />
                )}
              </div>
              <div className="text-xs text-emerald-500 mt-0.5">
                {bestSavings > 0 ? `-$${bestSavings.toFixed(2)} with best active promo` : 'No coupons applied'}
              </div>
            </div>

            <div>
              <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                Active Promotions
              </div>
              <div className="text-2xl font-bold text-indigo-300 mt-1">
                {activeList.length} <span className="text-sm font-normal text-gray-400">offers</span>
              </div>
              <div className="text-xs text-gray-400 mt-0.5">
                {activeList.filter((p) => p.coupon_code).length} promo codes detected
              </div>
            </div>
          </div>
        )}

        {/* Tab Switcher (Single Product Mode) */}
        {!isCatalogMode && (
          <div className="flex border-b border-gray-800 gap-4">
            <button
              onClick={() => setActiveTab('active')}
              className={`pb-2.5 text-sm font-medium border-b-2 flex items-center gap-2 transition-colors ${
                activeTab === 'active'
                  ? 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              <TicketIcon className="h-4 w-4" />
              Active Coupons ({promotions.length})
            </button>
            <button
              onClick={() => setActiveTab('detect')}
              className={`pb-2.5 text-sm font-medium border-b-2 flex items-center gap-2 transition-colors ${
                activeTab === 'detect'
                  ? 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              <SparklesIcon className="h-4 w-4" />
              Live Promo Detector
            </button>
            <button
              onClick={() => setActiveTab('create')}
              className={`pb-2.5 text-sm font-medium border-b-2 flex items-center gap-2 transition-colors ${
                activeTab === 'create'
                  ? 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              <PlusIcon className="h-4 w-4" />
              Add Coupon / Offer
            </button>
          </div>
        )}

        {/* ----------------- TAB: ACTIVE PROMOTIONS (PRODUCT) ----------------- */}
        {!isCatalogMode && activeTab === 'active' && (
          <div className="space-y-4">
            {loading ? (
              <div className="py-12 flex justify-center">
                <Spinner size="lg" />
              </div>
            ) : promotions.length === 0 ? (
              <div className="text-center py-10 bg-gray-900/50 rounded-xl border border-gray-800 p-6">
                <TagIcon className="h-10 w-10 text-gray-600 mx-auto mb-2" />
                <h4 className="text-base font-semibold text-gray-300">No Promotions Detected Yet</h4>
                <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
                  Use the Promo Detector tab to paste product banner text, or add a coupon code manually.
                </p>
                <div className="mt-4 flex justify-center gap-3">
                  <Button size="sm" variant="secondary" onClick={() => setActiveTab('detect')}>
                    <SparklesIcon className="h-4 w-4 mr-1.5" />
                    Detect Promo
                  </Button>
                  <Button size="sm" onClick={() => setActiveTab('create')}>
                    <PlusIcon className="h-4 w-4 mr-1.5" />
                    Add Coupon
                  </Button>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {promotions.map((promo) => (
                  <div
                    key={promo.id}
                    className={`rounded-xl border p-4 transition-all ${
                      promo.is_active
                        ? 'bg-gray-900/90 border-emerald-500/30 shadow-lg shadow-emerald-500/5'
                        : 'bg-gray-900/40 border-gray-800 opacity-60'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 capitalize">
                          {promo.promo_type?.replace('_', ' ')}
                        </span>
                        {promo.is_active ? (
                          <span className="inline-flex items-center text-xs text-emerald-400">
                            <CheckCircleIcon className="h-3.5 w-3.5 mr-1" /> Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-xs text-gray-500">
                            <XCircleIcon className="h-3.5 w-3.5 mr-1" /> Paused
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleToggle(promo.id)}
                          title={promo.is_active ? 'Deactivate' : 'Activate'}
                          className="p-1 text-gray-400 hover:text-gray-200 transition-colors"
                        >
                          <ArrowPathIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(promo.id)}
                          title="Delete promotion"
                          className="p-1 text-red-400 hover:text-red-300 transition-colors"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    <h5 className="font-semibold text-gray-200 mt-2 text-sm">{promo.title}</h5>

                    {/* Coupon Code Pill */}
                    {promo.coupon_code && (
                      <div className="mt-2.5 flex items-center justify-between bg-black/40 border border-gray-700/80 rounded-lg px-3 py-1.5">
                        <div className="flex items-center gap-2">
                          <TicketIcon className="h-4 w-4 text-emerald-400" />
                          <span className="font-mono text-sm font-bold text-emerald-300 tracking-wider">
                            {promo.coupon_code}
                          </span>
                        </div>
                        <button
                          onClick={() => handleCopyCode(promo.coupon_code)}
                          className="flex items-center gap-1 text-xs text-gray-400 hover:text-emerald-400 transition-colors"
                        >
                          {copiedCode === promo.coupon_code ? (
                            <>
                              <ClipboardDocumentCheckIcon className="h-4 w-4 text-emerald-400" />
                              <span className="text-emerald-400">Copied</span>
                            </>
                          ) : (
                            <>
                              <ClipboardDocumentIcon className="h-4 w-4" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}

                    {/* Price Impact Summary */}
                    <div className="mt-3 grid grid-cols-2 gap-2 text-xs bg-gray-800/40 rounded-lg p-2.5 border border-gray-800">
                      <div>
                        <span className="text-gray-500">Effective Price:</span>
                        <div className="font-bold text-gray-200 text-sm">
                          ${promo.effective_price ? promo.effective_price.toFixed(2) : '-'}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-500">Savings:</span>
                        <div className="font-bold text-emerald-400 text-sm">
                          -${promo.savings_amount ? promo.savings_amount.toFixed(2) : '0.00'}
                          {promo.discount_value && (
                            <span className="text-xs font-normal text-gray-400 ml-1">
                              ({promo.discount_value}
                              {promo.discount_type === 'percentage' ? '%' : '$'})
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {promo.banner_text && (
                      <div className="mt-2.5 text-xs text-gray-400 italic bg-gray-900/60 p-2 rounded border border-gray-800/60">
                        "{promo.banner_text}"
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ----------------- TAB: LIVE PROMO DETECTOR (PRODUCT) ----------------- */}
        {!isCatalogMode && activeTab === 'detect' && (
          <div className="space-y-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <h4 className="text-sm font-semibold text-gray-200 flex items-center gap-1.5 mb-1">
                <SparklesIcon className="h-4 w-4 text-emerald-400" />
                Raw Promo Snippet & Banner Inspector
              </h4>
              <p className="text-xs text-gray-400 mb-3">
                Paste any competitor promotional headline, discount banner, or clip coupon text to instantly extract coupon codes, discount rates, and net price adjustments.
              </p>

              <form onSubmit={handleDetect} className="space-y-3">
                <textarea
                  rows={3}
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder="e.g.: Special offer: Clip $15.00 coupon at checkout! Or save 25% using promo code SAVE25 at checkout. Buy 2 get 1 free."
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm text-gray-200 focus:outline-none focus:border-emerald-500"
                />

                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useAi}
                      onChange={(e) => setUseAi(e.target.checked)}
                      className="rounded border-gray-700 bg-gray-800 text-emerald-500 focus:ring-0"
                    />
                    <span>Enable Gemini 2.5 Flash Deep Extraction</span>
                  </label>

                  <Button type="submit" disabled={detecting || !rawText.trim()} size="sm">
                    {detecting ? (
                      <>
                        <Spinner size="sm" className="mr-1.5" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <SparklesIcon className="h-4 w-4 mr-1.5" />
                        Detect Offers
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </div>

            {/* Detected Results */}
            {detectedPromos.length > 0 && (
              <div className="space-y-3">
                <h5 className="text-xs font-semibold uppercase text-emerald-400 tracking-wider">
                  Detected Promotions ({detectedPromos.length})
                </h5>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {detectedPromos.map((item, idx) => (
                    <div
                      key={idx}
                      className="bg-gray-900 border border-emerald-500/40 rounded-xl p-4 flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 uppercase">
                            {item.promo_type?.replace('_', ' ')}
                          </span>
                          {item.coupon_code && (
                            <span className="font-mono text-xs font-bold text-emerald-300 bg-black/40 px-2 py-0.5 rounded">
                              {item.coupon_code}
                            </span>
                          )}
                        </div>
                        <h6 className="font-bold text-gray-200 mt-2 text-sm">{item.title}</h6>
                        <p className="text-xs text-gray-400 mt-1">{item.description}</p>

                        <div className="mt-3 flex items-center justify-between text-xs bg-gray-800/60 rounded p-2">
                          <span className="text-gray-400">Net Price:</span>
                          <span className="font-bold text-emerald-400 text-sm">
                            ${item.effective_price?.toFixed(2)}
                          </span>
                        </div>
                      </div>

                      <Button
                        size="sm"
                        variant="secondary"
                        className="mt-3 w-full"
                        onClick={() => handleSaveDetected(item)}
                      >
                        <PlusIcon className="h-4 w-4 mr-1.5" />
                        Attach to Product
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ----------------- TAB: CREATE PROMOTION (PRODUCT) ----------------- */}
        {!isCatalogMode && activeTab === 'create' && (
          <form onSubmit={handleManualCreate} className="space-y-4 bg-gray-900 p-5 rounded-xl border border-gray-800">
            <h4 className="text-sm font-semibold text-gray-200">Register New Promotion</h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Promo Type</label>
                <select
                  value={formData.promo_type}
                  onChange={(e) => setFormData({ ...formData, promo_type: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-gray-200"
                >
                  <option value="coupon_code">Coupon Code</option>
                  <option value="fixed_amount_discount">Clip Fixed Amount Coupon ($)</option>
                  <option value="percentage_discount">Clip Percentage Voucher (%)</option>
                  <option value="bogo">BOGO (Buy-One-Get-One)</option>
                  <option value="volume_tier">Volume / Bulk Tier</option>
                  <option value="flash_sale">Flash Sale</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Promotion Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Save $20 with SPRING20"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-gray-200"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Coupon Code (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. SPRING20"
                  value={formData.coupon_code}
                  onChange={(e) => setFormData({ ...formData, coupon_code: e.target.value.toUpperCase() })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-gray-200 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Discount Type</label>
                <select
                  value={formData.discount_type}
                  onChange={(e) => setFormData({ ...formData, discount_type: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-gray-200"
                >
                  <option value="percentage">Percentage Off (%)</option>
                  <option value="fixed_amount">Fixed Amount Off ($)</option>
                  <option value="bogo">BOGO Calculation</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">
                  Discount Value ({formData.discount_type === 'percentage' ? '%' : '$'})
                </label>
                <input
                  type="number"
                  step="0.01"
                  placeholder={formData.discount_type === 'percentage' ? '20' : '15.00'}
                  value={formData.discount_value}
                  onChange={(e) => setFormData({ ...formData, discount_value: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-gray-200"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Minimum Spend Threshold ($)</label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="e.g. 50.00"
                  value={formData.minimum_spend}
                  onChange={(e) => setFormData({ ...formData, minimum_spend: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-gray-200"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Banner Quote or Quote Text</label>
              <input
                type="text"
                placeholder="e.g. Limited time: Clip $20 coupon at checkout!"
                value={formData.banner_text}
                onChange={(e) => setFormData({ ...formData, banner_text: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-sm text-gray-200"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={() => setActiveTab('active')}>
                Cancel
              </Button>
              <Button type="submit" disabled={creating || !formData.title}>
                {creating ? <Spinner size="sm" className="mr-1.5" /> : <PlusIcon className="h-4 w-4 mr-1.5" />}
                Save Promotion
              </Button>
            </div>
          </form>
        )}

        {/* ----------------- CATALOG MODE: ENTIRE STORE INTELLIGENCE ----------------- */}
        {isCatalogMode && (
          <div className="space-y-5">
            {/* KPI Summary Cards */}
            {catalogInsights && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-gray-900 border border-gray-800 p-3.5 rounded-xl">
                  <span className="text-xs text-gray-400 font-semibold uppercase">Active Promotions</span>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">
                    {catalogInsights.total_active_promotions}
                  </div>
                  <span className="text-xs text-gray-500">across catalog</span>
                </div>
                <div className="bg-gray-900 border border-gray-800 p-3.5 rounded-xl">
                  <span className="text-xs text-gray-400 font-semibold uppercase">Avg Coupon Depth</span>
                  <div className="text-2xl font-bold text-indigo-400 mt-1">
                    {catalogInsights.average_discount_percentage}%
                  </div>
                  <span className="text-xs text-gray-500">discount rate</span>
                </div>
                <div className="bg-gray-900 border border-gray-800 p-3.5 rounded-xl">
                  <span className="text-xs text-gray-400 font-semibold uppercase">Avg Dollar Savings</span>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">
                    ${catalogInsights.average_savings_amount?.toFixed(2)}
                  </div>
                  <span className="text-xs text-gray-500">per item</span>
                </div>
                <div className="bg-gray-900 border border-gray-800 p-3.5 rounded-xl">
                  <span className="text-xs text-gray-400 font-semibold uppercase">Top Discounter</span>
                  <div className="text-base font-bold text-amber-400 mt-1 truncate">
                    {Object.keys(catalogInsights.competitor_promo_counts || {})[0] || 'N/A'}
                  </div>
                  <span className="text-xs text-gray-500">
                    {Object.values(catalogInsights.competitor_promo_counts || {})[0] || 0} promos active
                  </span>
                </div>
              </div>
            )}

            {/* Filters */}
            <div className="flex flex-wrap items-center justify-between gap-3 bg-gray-900/60 p-3 rounded-xl border border-gray-800">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Filter by domain (e.g. amazon)..."
                  value={filterDomain}
                  onChange={(e) => setFilterDomain(e.target.value)}
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-200"
                />
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-200"
                >
                  <option value="">All Promo Types</option>
                  <option value="coupon_code">Coupon Codes</option>
                  <option value="fixed_amount_discount">Fixed Clip Coupons</option>
                  <option value="percentage_discount">Percentage Vouchers</option>
                  <option value="bogo">BOGO Deals</option>
                  <option value="volume_tier">Volume Tiers</option>
                  <option value="flash_sale">Flash Sales</option>
                </select>
              </div>

              <div className="text-xs text-gray-400">
                Found <span className="text-emerald-400 font-bold">{catalogTotal}</span> active offers
              </div>
            </div>

            {/* Catalog Promos Table */}
            {loading ? (
              <div className="py-12 flex justify-center">
                <Spinner size="lg" />
              </div>
            ) : catalogPromos.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                No active competitor promotions found matching filters.
              </div>
            ) : (
              <div className="overflow-x-auto border border-gray-800 rounded-xl">
                <table className="min-w-full divide-y divide-gray-800 text-left text-xs">
                  <thead className="bg-gray-900/80 text-gray-400 font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="py-3 px-3">Product</th>
                      <th className="py-3 px-3">Competitor</th>
                      <th className="py-3 px-3">Promotion</th>
                      <th className="py-3 px-3">Coupon Code</th>
                      <th className="py-3 px-3">Listed Price</th>
                      <th className="py-3 px-3">Net Price</th>
                      <th className="py-3 px-3">Savings</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/60 bg-gray-900/30">
                    {catalogPromos.map((item) => (
                      <tr key={item.id} className="hover:bg-gray-800/30 transition-colors">
                        <td className="py-2.5 px-3 max-w-xs truncate text-gray-200 font-medium">
                          {item.product_name}
                        </td>
                        <td className="py-2.5 px-3 text-gray-400">
                          {item.source_domain || 'Unknown'}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="font-semibold text-gray-300">{item.title}</span>
                          <span className="ml-1.5 px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 capitalize">
                            {item.promo_type?.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono">
                          {item.coupon_code ? (
                            <button
                              onClick={() => handleCopyCode(item.coupon_code)}
                              className="inline-flex items-center gap-1 px-2 py-0.5 bg-black/40 border border-gray-700 text-emerald-300 font-bold rounded hover:border-emerald-500 transition-colors"
                            >
                              <span>{item.coupon_code}</span>
                              <ClipboardDocumentIcon className="h-3 w-3 text-gray-400" />
                            </button>
                          ) : (
                            <span className="text-gray-500">Auto-applied</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-gray-400">
                          ${item.original_price?.toFixed(2) || '-'}
                        </td>
                        <td className="py-2.5 px-3 text-emerald-400 font-bold">
                          ${item.effective_price?.toFixed(2) || '-'}
                        </td>
                        <td className="py-2.5 px-3 text-emerald-400 font-semibold">
                          -${item.savings_amount?.toFixed(2) || '0.00'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  )
}
