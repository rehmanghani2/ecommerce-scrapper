import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ServerStackIcon,
  ShieldCheckIcon,
  CircleStackIcon,
  GlobeAltIcon,
  CheckCircleIcon,
  ArrowPathIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline'
import { Card, PageLoader } from '@/components/Common'
import { apiGet } from '@/services/api'
import { formatNumber } from '@/utils/helpers'

export default function AdminSystem() {
  const { data: telemetry, isLoading, refetch } = useQuery({
    queryKey: ['adminTelemetry'],
    queryFn: () => apiGet('/admin/system/telemetry'),
  })

  if (isLoading) {
    return <PageLoader message="Querying system telemetry..." />
  }

  const db = telemetry?.database || {}
  const pool = telemetry?.proxy_pool || {}
  const env = telemetry?.environment || {}

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-2.5">
            <ServerStackIcon className="w-7 h-7 text-emerald-500" />
            Infrastructure & System Telemetry
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time proxy rotation health, database engines, and runtime configuration status.
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
        >
          <ArrowPathIcon className="w-3.5 h-3.5" />
          Poll Telemetry
        </button>
      </div>

      {/* Primary Nodes Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Database Node */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <CircleStackIcon className="w-6 h-6" />
            </div>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <CheckCircleIcon className="w-3.5 h-3.5" /> Connected
            </span>
          </div>

          <div>
            <h3 className="font-bold text-white text-base">Database Engine</h3>
            <p className="text-xs text-slate-400 mt-0.5">{db.engine}</p>
          </div>

          <div className="pt-3 border-t border-slate-800 space-y-2 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Total Users:</span>
              <strong className="text-white">{db.users_count || 0}</strong>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Total Jobs:</span>
              <strong className="text-white">{db.jobs_count || 0}</strong>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Catalog Products:</span>
              <strong className="text-white">{formatNumber(db.products_count || 0)}</strong>
            </div>
          </div>
        </div>

        {/* Proxy Pool Node */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <GlobeAltIcon className="w-6 h-6" />
            </div>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <CheckCircleIcon className="w-3.5 h-3.5" /> Auto-Failover Active
            </span>
          </div>

          <div>
            <h3 className="font-bold text-white text-base">Rotating Proxy Pool</h3>
            <p className="text-xs text-slate-400 mt-0.5">Automated ban detection on 403 / 429</p>
          </div>

          <div className="pt-3 border-t border-slate-800 space-y-2 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Configured Proxies:</span>
              <strong className="text-white">{pool.total_proxies || 0}</strong>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Healthy Nodes:</span>
              <strong className="text-emerald-400">{pool.healthy_proxies || 0}</strong>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Quarantined / Banned:</span>
              <strong className="text-rose-400">{pool.banned_proxies || 0}</strong>
            </div>
          </div>
        </div>

        {/* Core Engine Runtime */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="p-2.5 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <CpuChipIcon className="w-6 h-6" />
            </div>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20">
              v{env.version || '1.0.0'}
            </span>
          </div>

          <div>
            <h3 className="font-bold text-white text-base">Scraper Core Service</h3>
            <p className="text-xs text-slate-400 mt-0.5">{env.app_name}</p>
          </div>

          <div className="pt-3 border-t border-slate-800 space-y-2 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Playwright Headless:</span>
              <strong className="text-emerald-400">Chromium & Firefox Installed</strong>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Async Workers:</span>
              <strong className="text-white">Active (BackgroundTasks)</strong>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Debug Mode:</span>
              <strong className="text-slate-300">{env.debug ? 'True' : 'False'}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
