import React, { useState, useEffect } from 'react'
import {
  SparklesIcon,
  StarIcon,
  HandThumbUpIcon,
  HandThumbDownIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ChatBubbleBottomCenterTextIcon,
  TagIcon,
  UserCircleIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline'
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid'
import { Modal, ModalFooter, Button, Spinner, Badge } from '@/components/Common'
import { cn, formatDate } from '@/utils/helpers'
import reviewService from '@/services/reviewService'

export function ProductSentimentModal({ product, isOpen, onClose }) {
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [sentimentData, setSentimentData] = useState(null)
  const [reviews, setReviews] = useState([])
  const [reviewFilter, setReviewFilter] = useState('all') // 'all', 'positive', 'neutral', 'negative'
  const [error, setError] = useState(null)

  useEffect(() => {
    if (isOpen && product?.id) {
      loadData()
    } else {
      setSentimentData(null)
      setReviews([])
      setError(null)
    }
  }, [isOpen, product?.id])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      // Fetch reviews and sentiment in parallel
      const [reviewsRes, sentimentRes] = await Promise.allSettled([
        reviewService.getProductReviews(product.id, { limit: 100 }),
        reviewService.getProductSentiment(product.id),
      ])

      if (reviewsRes.status === 'fulfilled' && reviewsRes.value?.reviews) {
        setReviews(reviewsRes.value.reviews)
      }

      if (sentimentRes.status === 'fulfilled' && sentimentRes.value?.sentiment_summary) {
        setSentimentData(sentimentRes.value.sentiment_summary)
      } else {
        setSentimentData(null)
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load reviews')
    } finally {
      setLoading(false)
    }
  }

  const handleRunAIAnalysis = async () => {
    setAnalyzing(true)
    try {
      const res = await reviewService.analyzeSentiment(product.id, { use_ai: true })
      if (res?.sentiment_summary) {
        setSentimentData(res.sentiment_summary)
        // Refresh reviews list
        const rev = await reviewService.getProductReviews(product.id, { limit: 100 })
        if (rev?.reviews) setReviews(rev.reviews)
      }
    } catch (err) {
      alert('AI Sentiment Analysis error: ' + (err?.response?.data?.detail || err.message))
    } finally {
      setAnalyzing(false)
    }
  }

  if (!isOpen) return null

  const filteredReviews = reviewFilter === 'all'
    ? reviews
    : reviews.filter((r) => r.sentiment === reviewFilter)

  const posPct = sentimentData?.positive_percentage ?? 0
  const neuPct = sentimentData?.neutral_percentage ?? 0
  const negPct = sentimentData?.negative_percentage ?? 0

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Customer Reviews & AI Sentiment Intelligence"
      size="xl"
    >
      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center gap-3">
          <Spinner size="lg" />
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Analyzing customer sentiment and competitor flaws...
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Header Product & Overview Card */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-gray-50 to-indigo-50/50 dark:from-gray-800 dark:to-indigo-950/20 border border-gray-200 dark:border-gray-700">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-gray-900 dark:text-white line-clamp-1">
                  {product.name}
                </h3>
                <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {product.brand && <span className="font-semibold">{product.brand}</span>}
                  <span>•</span>
                  <span>{reviews.length} customer reviews extracted</span>
                  {product.rating && (
                    <>
                      <span>•</span>
                      <span className="flex items-center text-amber-500 font-bold">
                        <StarIconSolid className="w-3.5 h-3.5 mr-0.5" />
                        {product.rating} / 5.0
                      </span>
                    </>
                  )}
                </div>
              </div>

              <Button
                icon={SparklesIcon}
                variant="primary"
                size="sm"
                onClick={handleRunAIAnalysis}
                isLoading={analyzing}
                className="shrink-0"
              >
                {analyzing ? 'Mining Themes...' : 'Analyze with AI'}
              </Button>
            </div>

            {/* Sentiment Meter */}
            {sentimentData && (
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700/80">
                <div className="flex items-center justify-between text-xs font-semibold mb-1.5">
                  <span className="text-emerald-600 dark:text-emerald-400">
                    Positive {posPct}%
                  </span>
                  <span className="text-gray-500 dark:text-gray-400">
                    Neutral {neuPct}%
                  </span>
                  <span className="text-rose-600 dark:text-rose-400">
                    Negative {negPct}%
                  </span>
                </div>
                <div className="w-full h-2.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden flex">
                  <div style={{ width: `${posPct}%` }} className="h-full bg-emerald-500 transition-all duration-500" />
                  <div style={{ width: `${neuPct}%` }} className="h-full bg-amber-400 transition-all duration-500" />
                  <div style={{ width: `${negPct}%` }} className="h-full bg-rose-500 transition-all duration-500" />
                </div>
              </div>
            )}
          </div>

          {/* AI Executive Summary Verdict */}
          {sentimentData?.summary_verdict && (
            <div className="p-3.5 rounded-xl bg-indigo-50/80 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-xs">
              <div className="flex items-center gap-1.5 font-semibold text-indigo-900 dark:text-indigo-300 mb-1">
                <SparklesIcon className="w-4 h-4 text-indigo-600" />
                <span>Executive AI Intelligence Verdict</span>
              </div>
              <p className="text-indigo-950/90 dark:text-indigo-200 leading-relaxed">
                {sentimentData.summary_verdict}
              </p>
            </div>
          )}

          {/* Key Competitor Weaknesses & Strengths Grid */}
          {sentimentData && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Competitor Weaknesses & Flaws */}
              <div className="p-4 rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/30 dark:bg-rose-950/20 space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-rose-700 dark:text-rose-400 flex items-center gap-1.5">
                  <XCircleIcon className="w-4 h-4" />
                  Competitor Weaknesses & Vulnerabilities
                </h4>
                <div className="space-y-1.5">
                  {(sentimentData.key_weaknesses || []).map((weakness, i) => (
                    <div
                      key={i}
                      className="p-2 rounded-lg bg-white dark:bg-gray-800 border border-rose-100 dark:border-rose-900/40 text-xs text-gray-800 dark:text-gray-200 flex items-start gap-2 shadow-sm"
                    >
                      <span className="text-rose-500 font-bold shrink-0">•</span>
                      <span>{weakness}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Product Strengths */}
              <div className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/30 dark:bg-emerald-950/20 space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 flex items-center gap-1.5">
                  <CheckCircleIcon className="w-4 h-4" />
                  Key Product Strengths
                </h4>
                <div className="space-y-1.5">
                  {(sentimentData.key_strengths || []).map((strength, i) => (
                    <div
                      key={i}
                      className="p-2 rounded-lg bg-white dark:bg-gray-800 border border-emerald-100 dark:border-emerald-900/40 text-xs text-gray-800 dark:text-gray-200 flex items-start gap-2 shadow-sm"
                    >
                      <span className="text-emerald-500 font-bold shrink-0">•</span>
                      <span>{strength}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Customer Reviews Section */}
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
                <ChatBubbleBottomCenterTextIcon className="w-4 h-4 text-gray-400" />
                Customer Reviews ({reviews.length})
              </h4>

              {/* Sentiment filter pills */}
              <div className="flex items-center gap-1">
                {['all', 'positive', 'neutral', 'negative'].map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setReviewFilter(type)}
                    className={cn(
                      'px-2.5 py-1 rounded-lg text-xs font-semibold capitalize transition-colors',
                      reviewFilter === type
                        ? type === 'positive'
                          ? 'bg-emerald-600 text-white'
                          : type === 'negative'
                          ? 'bg-rose-600 text-white'
                          : 'bg-gray-900 text-white dark:bg-white dark:text-gray-900'
                        : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-200'
                    )}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            {filteredReviews.length === 0 ? (
              <div className="py-8 text-center text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/40 rounded-xl border border-dashed border-gray-300 dark:border-gray-700">
                No customer reviews found matching filter.
              </div>
            ) : (
              <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                {filteredReviews.map((rev, idx) => (
                  <div
                    key={rev.id || idx}
                    className="p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/80 space-y-1.5 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-gray-900 dark:text-white">
                          {rev.author || 'Anonymous'}
                        </span>
                        {rev.verified_purchase && (
                          <span className="inline-flex items-center text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                            <ShieldCheckIcon className="w-3.5 h-3.5 mr-0.5" />
                            Verified
                          </span>
                        )}
                      </div>

                      {/* Stars & Sentiment Pill */}
                      <div className="flex items-center gap-2">
                        {rev.rating !== null && rev.rating !== undefined && (
                          <div className="flex items-center text-amber-500">
                            {[...Array(5)].map((_, s) => (
                              <StarIconSolid
                                key={s}
                                className={cn(
                                  'w-3 h-3',
                                  s < Math.round(rev.rating) ? 'text-amber-400' : 'text-gray-200 dark:text-gray-700'
                                )}
                              />
                            ))}
                          </div>
                        )}
                        <span
                          className={cn(
                            'text-[10px] font-bold px-2 py-0.2 rounded-full uppercase',
                            rev.sentiment === 'positive'
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400'
                              : rev.sentiment === 'negative'
                              ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400'
                              : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                          )}
                        >
                          {rev.sentiment}
                        </span>
                      </div>
                    </div>

                    {rev.title && (
                      <p className="font-semibold text-gray-800 dark:text-gray-200">
                        {rev.title}
                      </p>
                    )}

                    <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                      {rev.content}
                    </p>

                    {/* Key topics tagged */}
                    {rev.key_topics && rev.key_topics.length > 0 && (
                      <div className="flex items-center gap-1.5 pt-1 flex-wrap">
                        {rev.key_topics.map((t, ti) => (
                          <span
                            key={ti}
                            className="inline-flex items-center text-[10px] px-2 py-0.2 rounded bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-800"
                          >
                            <TagIcon className="w-2.5 h-2.5 mr-1" />
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <ModalFooter>
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </ModalFooter>
    </Modal>
  )
}

export default ProductSentimentModal
