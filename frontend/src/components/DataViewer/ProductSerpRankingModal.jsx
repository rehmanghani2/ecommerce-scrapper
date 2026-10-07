import React, { useState, useEffect } from 'react'
import {
  MagnifyingGlassIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  SparklesIcon,
  BuildingStorefrontIcon,
} from '@heroicons/react/24/outline'

import Modal from '@/components/Common/Modal'
import Spinner from '@/components/Common/Spinner'
import serpService from '@/services/serpService'

export default function ProductSerpRankingModal({ product, isOpen, onClose }) {
  const [rankings, setRankings] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!isOpen || !product?.id) return
    const fetchRankings = async () => {
      try {
        setLoading(true)
        const data = await serpService.getProductRankings(product.id)
        setRankings(data || [])
      } catch (err) {
        console.error('Error fetching product SERP rankings:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchRankings()
  }, [isOpen, product?.id])

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <MagnifyingGlassIcon className="h-6 w-6 text-indigo-500" />
          <span>Search Engine Rankings: {product?.name?.substring(0, 35)}...</span>
        </div>
      }
      size="lg"
    >
      <div className="space-y-4">
        <div className="bg-gray-900 border border-gray-800 p-4 rounded-xl flex items-center justify-between">
          <div>
            <div className="text-xs text-gray-400 font-semibold uppercase">Product Listed Name</div>
            <div className="text-sm font-bold text-gray-200 mt-0.5">{product?.name}</div>
            <div className="text-xs text-gray-500 mt-0.5">{product?.source_domain || 'Competitor store'}</div>
          </div>
          <div className="text-right">
            <span className="text-xs text-indigo-400 font-semibold uppercase">Keywords Found</span>
            <div className="text-2xl font-bold text-indigo-300">{rankings.length}</div>
          </div>
        </div>

        {loading ? (
          <div className="py-12 flex justify-center">
            <Spinner size="lg" />
          </div>
        ) : rankings.length === 0 ? (
          <div className="text-center py-10 bg-gray-900/50 rounded-xl border border-gray-800 p-6 text-gray-400">
            <MagnifyingGlassIcon className="h-10 w-10 text-gray-600 mx-auto mb-2" />
            <p className="text-sm">This product does not currently appear in any monitored search keywords.</p>
            <p className="text-xs text-gray-500 mt-1">
              Add keywords to monitor in the Search Rankings section to track positions on Amazon, Walmart, or eBay.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto border border-gray-800 rounded-xl">
            <table className="min-w-full divide-y divide-gray-800 text-left text-xs">
              <thead className="bg-gray-900/90 text-gray-400 uppercase tracking-wider font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Keyword Query</th>
                  <th className="py-2.5 px-3">Marketplace</th>
                  <th className="py-2.5 px-3">Rank Position</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Movement</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 bg-gray-900/30">
                {rankings.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-800/30 transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-gray-200">
                      "{r.keyword}"
                    </td>
                    <td className="py-2.5 px-3 text-gray-400">
                      {r.domain || r.marketplace}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded font-bold text-xs ${
                        r.rank_position <= 3
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : r.rank_position <= 10
                          ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                          : 'bg-gray-800 text-gray-300'
                      }`}>
                        #{r.rank_position}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      {r.is_sponsored ? (
                        <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold text-[10px]">
                          SPONSORED AD
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold text-[10px]">
                          ORGANIC
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      {r.rank_change > 0 ? (
                        <span className="inline-flex items-center gap-0.5 text-emerald-400 font-semibold">
                          <ArrowTrendingUpIcon className="h-3.5 w-3.5" /> +{r.rank_change}
                        </span>
                      ) : r.rank_change < 0 ? (
                        <span className="inline-flex items-center gap-0.5 text-red-400 font-semibold">
                          <ArrowTrendingDownIcon className="h-3.5 w-3.5" /> {r.rank_change}
                        </span>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Modal>
  )
}
