import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ShieldCheckIcon,
  UserGroupIcon,
  KeyIcon,
  CheckCircleIcon,
  XCircleIcon,
  TrashIcon,
  ArrowPathIcon,
  BriefcaseIcon,
  EyeIcon,
  ArrowTopRightOnSquareIcon,
  DocumentDuplicateIcon,
  MagnifyingGlassIcon,
  ClockIcon,
} from '@heroicons/react/24/outline'
import { Button, Card, CardHeader, CardTitle, PageLoader, Modal, ModalFooter } from '@/components/Common'
import { apiGet, apiPatch, apiDelete, apiPost } from '@/services/api'
import { formatDate, formatNumber } from '@/utils/helpers'
import { useAuth } from '@/hooks/useAuth'
import toast from 'react-hot-toast'

export default function AdminUsers() {
  const queryClient = useQueryClient()
  const { user: currentUser } = useAuth()
  const [selectedUserId, setSelectedUserId] = useState(null)
  const [searchFilter, setSearchFilter] = useState('')

  // Fetch user list
  const { data: users, isLoading, refetch } = useQuery({
    queryKey: ['adminUsers'],
    queryFn: () => apiGet('/admin/users'),
  })

  // Update user permissions / status
  const updateMutation = useMutation({
    mutationFn: ({ userId, data }) => apiPatch(`/admin/users/${userId}`, data),
    onSuccess: (updated) => {
      toast.success(`User @${updated.username} updated`)
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] })
      queryClient.invalidateQueries({ queryKey: ['adminOverview'] })
      if (selectedUserId === updated.id) {
        queryClient.invalidateQueries({ queryKey: ['adminUserDetails', updated.id] })
      }
    },
    onError: (err) => {
      toast.error(err?.response?.data?.detail || 'Failed to update user')
    },
  })

  // Delete user account
  const deleteMutation = useMutation({
    mutationFn: (userId) => apiDelete(`/admin/users/${userId}`),
    onSuccess: () => {
      toast.success('User account deleted')
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] })
      queryClient.invalidateQueries({ queryKey: ['adminOverview'] })
      setSelectedUserId(null)
    },
    onError: (err) => {
      toast.error(err?.response?.data?.detail || 'Failed to delete user')
    },
  })

  if (isLoading) {
    return <PageLoader message="Loading user directory..." />
  }

  const filteredUsers = (users || []).filter((u) => {
    if (!searchFilter) return true
    const q = searchFilter.toLowerCase()
    return (
      u.username.toLowerCase().includes(q) ||
      u.email.toLowerCase().includes(q) ||
      (u.full_name && u.full_name.toLowerCase().includes(q))
    )
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-2.5">
            <UserGroupIcon className="w-7 h-7 text-rose-500" />
            User Access & Permissions Directory
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage user roles, toggle superuser status, inspect personal job histories, and revoke access.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <MagnifyingGlassIcon className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Search users..."
              className="pl-9 pr-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 w-52 focus:outline-none focus:ring-1 focus:ring-rose-500"
            />
          </div>

          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            <ArrowPathIcon className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-800 text-xs">
            <thead className="bg-slate-950/60">
              <tr>
                <th className="px-5 py-3.5 text-left font-semibold text-slate-400 uppercase tracking-wider">
                  User Identity
                </th>
                <th className="px-5 py-3.5 text-left font-semibold text-slate-400 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-5 py-3.5 text-left font-semibold text-slate-400 uppercase tracking-wider">
                  Role / Privileges
                </th>
                <th className="px-5 py-3.5 text-left font-semibold text-slate-400 uppercase tracking-wider">
                  Account Status
                </th>
                <th className="px-5 py-3.5 text-left font-semibold text-slate-400 uppercase tracking-wider">
                  Total Jobs & Yield
                </th>
                <th className="px-5 py-3.5 text-left font-semibold text-slate-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 bg-slate-900/60">
              {filteredUsers.map((u) => {
                const isCurrent = u.id === currentUser?.id
                return (
                  <tr key={u.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-5 py-3.5">
                      <div
                        className="flex items-center gap-3 cursor-pointer group"
                        onClick={() => setSelectedUserId(u.id)}
                      >
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-rose-600/30 to-indigo-600/30 text-rose-300 font-bold text-xs flex items-center justify-center uppercase shrink-0 border border-rose-500/20">
                          {u.username[0]}
                        </div>
                        <div>
                          <p className="font-bold text-white text-sm flex items-center gap-1.5 group-hover:text-rose-400 transition-colors">
                            @{u.username}
                            {isCurrent && (
                              <span className="text-[10px] px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                                You
                              </span>
                            )}
                          </p>
                          <p className="text-xs text-slate-400">{u.full_name || 'No full name'}</p>
                        </div>
                      </div>
                    </td>

                    <td className="px-5 py-3.5 font-mono text-slate-300 text-xs">
                      {u.email}
                    </td>

                    <td className="px-5 py-3.5">
                      <button
                        type="button"
                        onClick={() => updateMutation.mutate({ userId: u.id, data: { is_superuser: !u.is_superuser } })}
                        disabled={isCurrent || updateMutation.isPending}
                        title={isCurrent ? "Cannot modify your own root privileges" : "Click to toggle superuser status"}
                        className="cursor-pointer disabled:cursor-not-allowed"
                      >
                        {u.is_superuser ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-purple-500/10 text-purple-300 border border-purple-500/30 shadow-sm">
                            <ShieldCheckIcon className="w-3.5 h-3.5 text-purple-400" /> Superuser
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 hover:bg-slate-700 transition-colors">
                            Standard User
                          </span>
                        )}
                      </button>
                    </td>

                    <td className="px-5 py-3.5">
                      <button
                        type="button"
                        onClick={() => updateMutation.mutate({ userId: u.id, data: { is_active: !u.is_active } })}
                        disabled={isCurrent || updateMutation.isPending}
                        title={isCurrent ? "Cannot deactivate yourself" : "Click to toggle active status"}
                        className="cursor-pointer disabled:cursor-not-allowed"
                      >
                        {u.is_active ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-400">
                            <CheckCircleIcon className="w-4 h-4" /> Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-rose-400">
                            <XCircleIcon className="w-4 h-4" /> Suspended
                          </span>
                        )}
                      </button>
                    </td>

                    <td className="px-5 py-3.5">
                      <p className="text-xs font-bold text-white">
                        {u.job_count} jobs
                      </p>
                      <p className="text-[11px] text-slate-400">
                        {formatNumber(u.total_products_scraped || 0)} products scraped
                      </p>
                    </td>

                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          icon={EyeIcon}
                          onClick={() => setSelectedUserId(u.id)}
                          title="Inspect user profile and all their jobs"
                        >
                          View Details & Jobs
                        </Button>
                        {!isCurrent && (
                          <button
                            type="button"
                            onClick={() => {
                              if (window.confirm(`Are you sure you want to delete user @${u.username}?`)) {
                                deleteMutation.mutate(u.id)
                              }
                            }}
                            disabled={deleteMutation.isPending}
                            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 transition-colors"
                            title="Delete user account"
                          >
                            <TrashIcon className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* User Full Profile & Jobs Inspection Modal */}
      {selectedUserId && (
        <UserDetailModal
          userId={selectedUserId}
          isOpen={!!selectedUserId}
          onClose={() => setSelectedUserId(null)}
          onUpdateUser={(data) => updateMutation.mutate({ userId: selectedUserId, data })}
        />
      )}
    </div>
  )
}

function UserDetailModal({ userId, isOpen, onClose, onUpdateUser }) {
  const queryClient = useQueryClient()
  const [jobFilter, setJobFilter] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')

  const { data: userDetail, isLoading } = useQuery({
    queryKey: ['adminUserDetails', userId],
    queryFn: () => apiGet(`/admin/users/${userId}/details`),
    enabled: isOpen && !!userId,
  })

  const regenKeyMutation = useMutation({
    mutationFn: () => apiPost(`/admin/users/${userId}/regenerate-api-key`),
    onSuccess: (res) => {
      toast.success(res.message || 'API Key regenerated')
      queryClient.invalidateQueries({ queryKey: ['adminUserDetails', userId] })
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] })
    },
    onError: (err) => {
      toast.error(err?.response?.data?.detail || 'Failed to regenerate key')
    },
  })

  if (!isOpen) return null

  const jobs = userDetail?.jobs || []
  const filteredJobs = jobs.filter((j) => {
    if (jobFilter !== 'all' && j.status.toLowerCase() !== jobFilter) return false
    if (searchTerm) {
      const q = searchTerm.toLowerCase()
      return (
        j.job_id.toLowerCase().includes(q) ||
        (j.name && j.name.toLowerCase().includes(q)) ||
        (j.domain && j.domain.toLowerCase().includes(q))
      )
    }
    return true
  })

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isLoading ? 'Loading User...' : `User Profile & Job History: @${userDetail?.username}`}
      size="xl"
    >
      {isLoading ? (
        <div className="py-12">
          <PageLoader message="Fetching user details and scraping jobs..." />
        </div>
      ) : (
        <div className="space-y-6">
          {/* User Profile Banner */}
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-rose-600 to-indigo-600 text-white font-bold text-lg flex items-center justify-center uppercase shadow-sm">
                {userDetail?.username[0]}
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-base font-bold text-white">
                    @{userDetail?.username}
                  </h3>
                  <span className="text-xs text-slate-400">({userDetail?.full_name || 'No full name provided'})</span>
                  {userDetail?.is_superuser && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/10 text-purple-300 border border-purple-500/30">
                      Superuser
                    </span>
                  )}
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      userDetail?.is_active
                        ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30'
                        : 'bg-rose-500/10 text-rose-300 border border-rose-500/30'
                    }`}
                  >
                    {userDetail?.is_active ? 'Active' : 'Suspended'}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Email: <strong className="text-slate-200">{userDetail?.email}</strong> • User ID: #{userDetail?.id}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <Button
                size="sm"
                variant={userDetail?.is_superuser ? 'secondary' : 'primary'}
                onClick={() => onUpdateUser({ is_superuser: !userDetail?.is_superuser })}
              >
                {userDetail?.is_superuser ? 'Revoke Superuser' : 'Make Superuser'}
              </Button>
              <Button
                size="sm"
                variant={userDetail?.is_active ? 'danger' : 'secondary'}
                onClick={() => onUpdateUser({ is_active: !userDetail?.is_active })}
              >
                {userDetail?.is_active ? 'Suspend User' : 'Activate User'}
              </Button>
            </div>
          </div>

          {/* Account Meta & API Key */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900 space-y-2">
              <p className="font-semibold text-white flex items-center gap-1.5">
                <ClockIcon className="w-4 h-4 text-rose-400" />
                Account Timestamps
              </p>
              <div className="space-y-1 text-slate-400">
                <p>Created: <strong className="text-slate-200">{formatDate(userDetail?.created_at, 'PPp')}</strong></p>
                <p>Last Login: <strong className="text-slate-200">{userDetail?.last_login ? formatDate(userDetail.last_login, 'PPp') : 'Never'}</strong></p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900 space-y-2">
              <div className="flex items-center justify-between">
                <p className="font-semibold text-white flex items-center gap-1.5">
                  <KeyIcon className="w-4 h-4 text-indigo-400" />
                  Programmatic API Key
                </p>
                <button
                  type="button"
                  onClick={() => regenKeyMutation.mutate()}
                  disabled={regenKeyMutation.isPending}
                  className="text-[11px] text-rose-400 hover:text-rose-300 font-semibold"
                >
                  {regenKeyMutation.isPending ? 'Generating...' : 'Regenerate'}
                </button>
              </div>
              <div className="flex items-center gap-2">
                <code className="flex-1 p-1.5 rounded bg-slate-950 font-mono text-[11px] text-slate-300 truncate border border-slate-800">
                  {userDetail?.api_key || 'No API key issued'}
                </code>
                {userDetail?.api_key && (
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(userDetail.api_key)
                      toast.success('Copied API Key')
                    }}
                    className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                    title="Copy API Key"
                  >
                    <DocumentDuplicateIcon className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* User Scraping Telemetry KPI Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
              <p className="text-[11px] font-semibold text-blue-400">Total Jobs</p>
              <p className="text-xl font-extrabold text-white mt-0.5">
                {userDetail?.stats?.total_jobs || 0}
              </p>
            </div>
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
              <p className="text-[11px] font-semibold text-emerald-400">Products Extracted</p>
              <p className="text-xl font-extrabold text-white mt-0.5">
                {formatNumber(userDetail?.stats?.total_products || 0)}
              </p>
            </div>
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
              <p className="text-[11px] font-semibold text-purple-400">Success Rate</p>
              <p className="text-xl font-extrabold text-white mt-0.5">
                {userDetail?.stats?.success_rate || 0}%
              </p>
            </div>
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
              <p className="text-[11px] font-semibold text-amber-400">Unique Domains</p>
              <p className="text-xl font-extrabold text-white mt-0.5">
                {userDetail?.stats?.unique_domains?.length || 0}
              </p>
            </div>
          </div>

          {/* User's Jobs Section */}
          <div className="space-y-3 pt-2 border-t border-slate-800">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="flex items-center gap-2">
                <BriefcaseIcon className="w-5 h-5 text-rose-500" />
                <h4 className="font-bold text-white text-sm">
                  Scraping Jobs Launched by @{userDetail?.username} ({jobs.length})
                </h4>
              </div>

              {/* Job Filters & Search */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className="relative">
                  <MagnifyingGlassIcon className="w-4 h-4 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search jobs..."
                    className="pl-8 pr-3 py-1 text-xs rounded-lg border border-slate-800 bg-slate-900 text-white w-40 focus:ring-1 focus:ring-rose-500"
                  />
                </div>

                <div className="flex items-center bg-slate-900 p-0.5 rounded-lg text-xs border border-slate-800">
                  {['all', 'completed', 'running', 'failed'].map((st) => (
                    <button
                      key={st}
                      type="button"
                      onClick={() => setJobFilter(st)}
                      className={`px-2.5 py-1 rounded capitalize font-medium transition-colors ${
                        jobFilter === st
                          ? 'bg-rose-600 text-white font-semibold'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      {st}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Jobs Table */}
            {filteredJobs.length === 0 ? (
              <div className="p-8 text-center rounded-xl border border-dashed border-slate-800 text-slate-500 text-xs">
                {jobs.length === 0
                  ? `User @${userDetail?.username} has not launched any scraping jobs yet.`
                  : 'No jobs match your current search / filter.'}
              </div>
            ) : (
              <div className="overflow-x-auto max-h-72 overflow-y-auto rounded-xl border border-slate-800">
                <table className="min-w-full divide-y divide-slate-800 text-xs">
                  <thead className="bg-slate-950 sticky top-0 z-10 text-slate-400">
                    <tr>
                      <th className="px-3 py-2 text-left font-semibold uppercase">Job</th>
                      <th className="px-3 py-2 text-left font-semibold uppercase">Domain</th>
                      <th className="px-3 py-2 text-left font-semibold uppercase">Status</th>
                      <th className="px-3 py-2 text-left font-semibold uppercase">Products</th>
                      <th className="px-3 py-2 text-left font-semibold uppercase">Pages</th>
                      <th className="px-3 py-2 text-left font-semibold uppercase">Date</th>
                      <th className="px-3 py-2 text-left font-semibold uppercase">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 bg-slate-900/60">
                    {filteredJobs.map((j) => (
                      <tr key={j.id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="px-3 py-2">
                          <Link
                            to={`/jobs/${j.job_id}`}
                            className="font-medium text-rose-400 hover:text-rose-300 font-mono"
                          >
                            {j.job_id}
                          </Link>
                          <p className="text-[11px] text-slate-400 truncate max-w-[180px]">{j.name}</p>
                        </td>
                        <td className="px-3 py-2 text-slate-300 font-medium">
                          {j.domain}
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold capitalize ${
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
                        <td className="px-3 py-2 font-bold text-white">
                          {formatNumber(j.total_products || 0)}
                        </td>
                        <td className="px-3 py-2 text-slate-400">
                          {j.scraped_pages || 0} / {j.total_pages || '∞'}
                        </td>
                        <td className="px-3 py-2 text-slate-400 whitespace-nowrap">
                          {j.created_at ? formatDate(j.created_at) : '—'}
                        </td>
                        <td className="px-3 py-2">
                          <Link
                            to={`/jobs/${j.job_id}`}
                            className="p-1 rounded text-slate-400 hover:text-rose-400 inline-block"
                            title="Inspect job execution"
                          >
                            <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                          </Link>
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

      <ModalFooter>
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </ModalFooter>
    </Modal>
  )
}
