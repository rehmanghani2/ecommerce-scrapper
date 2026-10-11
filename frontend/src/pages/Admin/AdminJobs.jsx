import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  BriefcaseIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  ArrowTopRightOnSquareIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline'
import { Button, PageLoader, Pagination } from '@/components/Common'
import { apiGet } from '@/services/api'
import { formatDate, formatDuration, formatNumber } from '@/utils/helpers'

export default function AdminJobs() {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['adminPlatformJobs', { page, status_filter: statusFilter, search: searchTerm }],
    queryFn: () =>
      apiGet('/admin/jobs', {
        page,
        page_size: 25,
        status_filter: statusFilter !== 'all' ? statusFilter : undefined,
        search: searchTerm || undefined,
      }),
  })

  const jobs = data?.jobs || []
  const total = data?.total || 0
  const totalPages = data?.pages || 1

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-2.5">
            <BriefcaseIcon className="w-7 h-7 text-blue-500" />
            Global Platform Scraping Jobs
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Monitoring all {total} scraping pipeline jobs executed by any user across the system.
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
        >
          <ArrowPathIcon className="w-3.5 h-3.5" />
          Refresh Jobs
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
          {['all', 'completed', 'running', 'failed', 'pending'].map((st) => (
            <button
              key={st}
              onClick={() => {
                setStatusFilter(st)
                setPage(1)
              }}
              className={`px-3 py-1.5 rounded-md capitalize font-semibold transition-colors ${
                statusFilter === st
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="relative">
          <MagnifyingGlassIcon className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              setPage(1)
            }}
            placeholder="Search job ID, domain, target URL..."
            className="pl-9 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 w-64 focus:ring-1 focus:ring-blue-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Jobs Table */}
      {isLoading ? (
        <PageLoader message="Loading platform jobs..." />
      ) : jobs.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-slate-900 border border-slate-800 text-slate-500 text-sm">
          No platform scraping jobs found matching your criteria.
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-800 text-xs">
              <thead className="bg-slate-950 text-slate-400">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold uppercase">Job ID & Name</th>
                  <th className="px-4 py-3 text-left font-semibold uppercase">Owner</th>
                  <th className="px-4 py-3 text-left font-semibold uppercase">Domain</th>
                  <th className="px-4 py-3 text-left font-semibold uppercase">Status</th>
                  <th className="px-4 py-3 text-left font-semibold uppercase">Yield</th>
                  <th className="px-4 py-3 text-left font-semibold uppercase">Pages</th>
                  <th className="px-4 py-3 text-left font-semibold uppercase">Duration</th>
                  <th className="px-4 py-3 text-left font-semibold uppercase">Date</th>
                  <th className="px-4 py-3 text-left font-semibold uppercase">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 bg-slate-900/60">
                {jobs.map((j) => (
                  <tr key={j.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3 font-mono">
                      <Link to={`/jobs/${j.job_id}`} className="font-bold text-blue-400 hover:underline">
                        {j.job_id}
                      </Link>
                      <p className="text-[11px] text-slate-400 truncate max-w-xs">{j.name}</p>
                    </td>

                    <td className="px-4 py-3 font-semibold text-rose-300">
                      @{j.username || 'demo'}
                    </td>

                    <td className="px-4 py-3 text-slate-300 font-medium">
                      {j.domain}
                    </td>

                    <td className="px-4 py-3">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold capitalize ${
                          j.status.toLowerCase() === 'completed'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : j.status.toLowerCase() === 'running'
                            ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse'
                            : j.status.toLowerCase() === 'failed'
                            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            : 'bg-slate-800 text-slate-300'
                        }`}
                      >
                        {j.status}
                      </span>
                    </td>

                    <td className="px-4 py-3 font-bold text-white">
                      {formatNumber(j.total_products || 0)} items
                    </td>

                    <td className="px-4 py-3 text-slate-400">
                      {j.scraped_pages || 0} / {j.total_pages || '∞'}
                    </td>

                    <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                      {j.duration ? formatDuration(j.duration) : '—'}
                    </td>

                    <td className="px-4 py-3 text-slate-400 whitespace-nowrap">
                      {j.created_at ? formatDate(j.created_at) : '—'}
                    </td>

                    <td className="px-4 py-3">
                      <Link
                        to={`/jobs/${j.job_id}`}
                        className="p-1 rounded text-slate-400 hover:text-white inline-block"
                        title="Open job details"
                      >
                        <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center pt-2">
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={(p) => setPage(p)}
          />
        </div>
      )}
    </div>
  )
}
