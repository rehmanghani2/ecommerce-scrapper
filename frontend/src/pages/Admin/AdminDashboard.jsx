import React from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ShieldCheckIcon,
  UserGroupIcon,
  BriefcaseIcon,
  CubeIcon,
  ArrowRightIcon,
  ServerStackIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline'
import { Card, PageLoader } from '@/components/Common'
import { apiGet } from '@/services/api'
import { formatNumber, formatDate } from '@/utils/helpers'

export default function AdminDashboard() {
  const { data: overview, isLoading, refetch } = useQuery({
    queryKey: ['adminOverview'],
    queryFn: () => apiGet('/admin/overview'),
  })

  const { data: latestJobsData } = useQuery({
    queryKey: ['adminPlatformJobs', { page: 1, page_size: 6 }],
    queryFn: () => apiGet('/admin/jobs', { page: 1, page_size: 6 }),
  })

  const { data: usersData } = useQuery({
    queryKey: ['adminUsers'],
    queryFn: () => apiGet('/admin/users'),
  })

  if (isLoading) {
    return <PageLoader message="Loading administrator mission control..." />
  }

  const jobs = latestJobsData?.jobs || []
  const users = usersData || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-2.5">
            <ShieldCheckIcon className="w-7 h-7 text-rose-500" />
            Root Administrator Mission Control
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Global system management, multi-user accounts, platform job monitoring, and telemetry.
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors w-fit"
        >
          <ArrowPathIcon className="w-3.5 h-3.5" />
          Refresh Stats
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Users</p>
            <p className="text-2xl font-extrabold text-white mt-1">{overview?.total_users || 0}</p>
            <p className="text-[11px] text-emerald-400 mt-0.5">{overview?.active_users || 0} active</p>
          </div>
          <div className="p-3 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <UserGroupIcon className="w-6 h-6" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Superusers</p>
            <p className="text-2xl font-extrabold text-white mt-1">{overview?.superuser_count || 0}</p>
            <p className="text-[11px] text-purple-400 mt-0.5">Root privileges</p>
          </div>
          <div className="p-3 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <ShieldCheckIcon className="w-6 h-6" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Platform Jobs</p>
            <p className="text-2xl font-extrabold text-white mt-1">{overview?.total_jobs || 0}</p>
            <p className="text-[11px] text-blue-400 mt-0.5">All user pipelines</p>
          </div>
          <div className="p-3 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <BriefcaseIcon className="w-6 h-6" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Global Products</p>
            <p className="text-2xl font-extrabold text-white mt-1">
              {formatNumber(overview?.total_products || 0)}
            </p>
            <p className="text-[11px] text-emerald-400 mt-0.5">In catalog database</p>
          </div>
          <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CubeIcon className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Quick Launch Management Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/admin/users"
          className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-rose-500/50 transition-all group flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
                <UserGroupIcon className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                {users.length} Users
              </span>
            </div>
            <h3 className="font-bold text-white text-base group-hover:text-rose-400 transition-colors">
              User Accounts & Role Delegation
            </h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Inspect user profiles, promote superusers, suspend access, and review individual job runs.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-semibold text-rose-400">
            <span>Manage Users</span>
            <ArrowRightIcon className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
          </div>
        </Link>

        <Link
          to="/admin/jobs"
          className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-blue-500/50 transition-all group flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
                <BriefcaseIcon className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                Cross-User Jobs
              </span>
            </div>
            <h3 className="font-bold text-white text-base group-hover:text-blue-400 transition-colors">
              Global Platform Jobs Monitor
            </h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              View, search, and monitor every scraping job run by any user across all domains.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-semibold text-blue-400">
            <span>Inspect All Jobs</span>
            <ArrowRightIcon className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
          </div>
        </Link>

        <Link
          to="/admin/system"
          className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-emerald-500/50 transition-all group flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <ServerStackIcon className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                Infrastructure
              </span>
            </div>
            <h3 className="font-bold text-white text-base group-hover:text-emerald-400 transition-colors">
              System Telemetry & Health
            </h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Proxy rotation pool metrics, database engine connectivity, and server status.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-semibold text-emerald-400">
            <span>View Telemetry</span>
            <ArrowRightIcon className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
          </div>
        </Link>
      </div>

      {/* Recent Platform Jobs Stream */}
      <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <ClockIcon className="w-4 h-4 text-rose-500" />
            Recent Platform Scraping Activity
          </h3>
          <Link
            to="/admin/jobs"
            className="text-xs font-semibold text-rose-400 hover:text-rose-300 flex items-center gap-1"
          >
            View All Platform Jobs <ArrowRightIcon className="w-3.5 h-3.5" />
          </Link>
        </div>

        {jobs.length === 0 ? (
          <p className="text-xs text-slate-500 py-6 text-center">
            No scraping jobs have been executed on the platform yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-800 text-xs">
              <thead>
                <tr className="text-slate-400 uppercase font-semibold">
                  <th className="py-2.5 text-left">Job ID & Target</th>
                  <th className="py-2.5 text-left">User</th>
                  <th className="py-2.5 text-left">Domain</th>
                  <th className="py-2.5 text-left">Status</th>
                  <th className="py-2.5 text-left">Yield</th>
                  <th className="py-2.5 text-left">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {jobs.map((j) => (
                  <tr key={j.id} className="hover:bg-slate-800/40">
                    <td className="py-2.5 font-mono text-slate-300">
                      <Link to={`/jobs/${j.job_id}`} className="hover:text-rose-400">
                        {j.job_id}
                      </Link>
                    </td>
                    <td className="py-2.5 text-rose-300 font-semibold">@{j.username || 'demo'}</td>
                    <td className="py-2.5 text-slate-300">{j.domain}</td>
                    <td className="py-2.5">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold capitalize ${
                          j.status.toLowerCase() === 'completed'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : j.status.toLowerCase() === 'running'
                            ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}
                      >
                        {j.status}
                      </span>
                    </td>
                    <td className="py-2.5 font-bold text-white">
                      {formatNumber(j.total_products || 0)} items
                    </td>
                    <td className="py-2.5 text-slate-500">{j.created_at ? formatDate(j.created_at) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
