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
  CubeIcon,
  BriefcaseIcon,
  EyeIcon,
  ArrowTopRightOnSquareIcon,
  DocumentDuplicateIcon,
  MagnifyingGlassIcon,
  ClockIcon,
  GlobeAltIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { Button, Card, CardHeader, CardTitle, Badge, PageLoader, Modal, ModalFooter } from '@/components/Common'
import { apiGet, apiPatch, apiDelete, apiPost } from '@/services/api'
import { formatDate, formatDuration, formatNumber } from '@/utils/helpers'
import toast from 'react-hot-toast'

export default function AdminManagement({ currentUser }) {
  const queryClient = useQueryClient()
  const [selectedUserId, setSelectedUserId] = useState(null)

  // Fetch admin system overview
  const { data: overview, isLoading: overviewLoading, refetch: refetchOverview } = useQuery({
    queryKey: ['adminOverview'],
    queryFn: () => apiGet('/admin/overview'),
  })

  // Fetch user list
  const { data: users, isLoading: usersLoading, refetch: refetchUsers } = useQuery({
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

  const isLoading = overviewLoading || usersLoading

  if (isLoading) {
    return <PageLoader message="Loading admin control panel..." />
  }

  return (
    <div className="space-y-6">
      {/* Superuser Banner */}
      <div className="p-4 rounded-2xl bg-gradient-to-r from-primary-900 via-indigo-900 to-purple-900 text-white shadow-md flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3.5">
          <div className="p-3 bg-white/10 backdrop-blur-md rounded-xl text-yellow-300">
            <ShieldCheckIcon className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-lg">Full Admin & Root Access Enabled</h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-yellow-400 text-gray-900 shadow-sm">
                Superuser Active
              </span>
            </div>
            <p className="text-xs text-indigo-200 mt-0.5">
              Logged in as <strong className="text-white">@{currentUser?.username}</strong> ({currentUser?.email}) with unrestricted system privileges
            </p>
          </div>
        </div>

        <Button
          variant="secondary"
          size="sm"
          icon={ArrowPathIcon}
          onClick={() => {
            refetchOverview()
            refetchUsers()
          }}
          className="bg-white/10 hover:bg-white/20 text-white border-white/20"
        >
          Refresh Telemetry
        </Button>
      </div>

      {/* System Telemetry KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-white dark:bg-gray-800">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Total Registered Users</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {overview?.total_users || 0}
              </p>
            </div>
            <div className="p-3 rounded-xl bg-primary-50 dark:bg-primary-950/60 text-primary-600 dark:text-primary-400">
              <UserGroupIcon className="w-6 h-6" />
            </div>
          </div>
        </Card>

        <Card className="bg-white dark:bg-gray-800">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Active Superusers</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {overview?.superuser_count || 0}
              </p>
            </div>
            <div className="p-3 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
              <ShieldCheckIcon className="w-6 h-6" />
            </div>
          </div>
        </Card>

        <Card className="bg-white dark:bg-gray-800">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Platform Scraping Jobs</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {overview?.total_jobs || 0}
              </p>
            </div>
            <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400">
              <BriefcaseIcon className="w-6 h-6" />
            </div>
          </div>
        </Card>

        <Card className="bg-white dark:bg-gray-800">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Global Products DB</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {formatNumber(overview?.total_products || 0)}
              </p>
            </div>
            <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400">
              <CubeIcon className="w-6 h-6" />
            </div>
          </div>
        </Card>
      </div>

      {/* User Accounts Management Table */}
      <Card padding="none" className="overflow-hidden bg-white dark:bg-gray-800">
        <CardHeader className="p-4 border-b border-gray-100 dark:border-gray-700/80">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <UserGroupIcon className="w-5 h-5 text-primary-500" />
              User Access & Full Job History Control
            </CardTitle>
            <span className="text-xs text-gray-400">
              Click any user to inspect their full profile, API keys, and scraped jobs
            </span>
          </div>
        </CardHeader>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800/80">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">User Identity</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Email</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Role / Access</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Jobs & Yield</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {users?.map((u) => {
                const isCurrent = u.id === currentUser?.id
                return (
                  <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                    <td className="px-4 py-3">
                      <div
                        className="flex items-center gap-2.5 cursor-pointer group"
                        onClick={() => setSelectedUserId(u.id)}
                      >
                        <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-950 text-primary-700 dark:text-primary-300 font-bold text-xs flex items-center justify-center uppercase shrink-0">
                          {u.username[0]}
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900 dark:text-white text-sm flex items-center gap-1.5 group-hover:text-primary-600 transition-colors">
                            @{u.username}
                            {isCurrent && (
                              <span className="text-[10px] px-1.5 py-0.2 rounded bg-primary-50 text-primary-700 border border-primary-200 dark:bg-primary-900/40 dark:text-primary-300">
                                You
                              </span>
                            )}
                          </p>
                          <p className="text-xs text-gray-400">{u.full_name || 'No full name'}</p>
                        </div>
                      </div>
                    </td>

                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 font-mono text-xs">
                      {u.email}
                    </td>

                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => updateMutation.mutate({ userId: u.id, data: { is_superuser: !u.is_superuser } })}
                        disabled={isCurrent || updateMutation.isPending}
                        title={isCurrent ? "Cannot modify your own root privileges" : "Click to toggle superuser status"}
                        className="cursor-pointer disabled:cursor-not-allowed"
                      >
                        {u.is_superuser ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300 shadow-sm border border-purple-200 dark:border-purple-800">
                            <ShieldCheckIcon className="w-3.5 h-3.5 text-purple-600" /> Superuser
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 transition-colors">
                            Standard User
                          </span>
                        )}
                      </button>
                    </td>

                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => updateMutation.mutate({ userId: u.id, data: { is_active: !u.is_active } })}
                        disabled={isCurrent || updateMutation.isPending}
                        title={isCurrent ? "Cannot deactivate yourself" : "Click to toggle active status"}
                        className="cursor-pointer disabled:cursor-not-allowed"
                      >
                        {u.is_active ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                            <CheckCircleIcon className="w-4 h-4" /> Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-rose-600 dark:text-rose-400">
                            <XCircleIcon className="w-4 h-4" /> Suspended
                          </span>
                        )}
                      </button>
                    </td>

                    <td className="px-4 py-3">
                      <p className="text-xs font-semibold text-gray-900 dark:text-white">
                        {u.job_count} jobs
                      </p>
                      <p className="text-[11px] text-gray-500 dark:text-gray-400">
                        {formatNumber(u.total_products_scraped || 0)} items scraped
                      </p>
                    </td>

                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          icon={EyeIcon}
                          onClick={() => setSelectedUserId(u.id)}
                          title="Inspect user profile & jobs"
                        >
                          View Details
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
                            className="p-1.5 rounded-lg text-gray-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
                            title="Delete user"
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
      </Card>

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
  const [jobFilter, setJobFilter] = useState('all') // all, completed, running, failed
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
          {/* User Profile Card */}
          <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/80 border border-gray-200/80 dark:border-gray-700/80 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-600 to-indigo-600 text-white font-bold text-lg flex items-center justify-center uppercase shadow-sm">
                {userDetail?.username[0]}
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-base font-bold text-gray-900 dark:text-white">
                    @{userDetail?.username}
                  </h3>
                  <span className="text-xs text-gray-400">({userDetail?.full_name || 'No full name provided'})</span>
                  {userDetail?.is_superuser && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300">
                      Superuser
                    </span>
                  )}
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      userDetail?.is_active
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                        : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                    }`}
                  >
                    {userDetail?.is_active ? 'Active' : 'Suspended'}
                  </span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Email: <strong className="text-gray-700 dark:text-gray-300">{userDetail?.email}</strong> • User ID: #{userDetail?.id}
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
            <div className="p-3.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 space-y-2">
              <p className="font-semibold text-gray-900 dark:text-white flex items-center gap-1.5">
                <ClockIcon className="w-4 h-4 text-primary-500" />
                Account Timestamps
              </p>
              <div className="space-y-1 text-gray-500 dark:text-gray-400">
                <p>Created: <strong className="text-gray-700 dark:text-gray-300">{formatDate(userDetail?.created_at, 'PPp')}</strong></p>
                <p>Last Login: <strong className="text-gray-700 dark:text-gray-300">{userDetail?.last_login ? formatDate(userDetail.last_login, 'PPp') : 'Never'}</strong></p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 space-y-2">
              <div className="flex items-center justify-between">
                <p className="font-semibold text-gray-900 dark:text-white flex items-center gap-1.5">
                  <KeyIcon className="w-4 h-4 text-indigo-500" />
                  Programmatic API Key
                </p>
                <button
                  type="button"
                  onClick={() => regenKeyMutation.mutate()}
                  disabled={regenKeyMutation.isPending}
                  className="text-[11px] text-primary-600 hover:text-primary-700 font-semibold"
                >
                  {regenKeyMutation.isPending ? 'Generating...' : 'Regenerate'}
                </button>
              </div>
              <div className="flex items-center gap-2">
                <code className="flex-1 p-1.5 rounded bg-gray-100 dark:bg-gray-900 font-mono text-[11px] text-gray-700 dark:text-gray-300 truncate">
                  {userDetail?.api_key || 'No API key issued'}
                </code>
                {userDetail?.api_key && (
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(userDetail.api_key)
                      toast.success('Copied API Key')
                    }}
                    className="p-1.5 rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 text-gray-600 dark:text-gray-300"
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
            <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200/60 dark:border-blue-900/40">
              <p className="text-[11px] font-semibold text-blue-700 dark:text-blue-300">Total Jobs</p>
              <p className="text-xl font-extrabold text-blue-900 dark:text-blue-100 mt-0.5">
                {userDetail?.stats?.total_jobs || 0}
              </p>
            </div>
            <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200/60 dark:border-emerald-900/40">
              <p className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-300">Products Extracted</p>
              <p className="text-xl font-extrabold text-emerald-900 dark:text-emerald-100 mt-0.5">
                {formatNumber(userDetail?.stats?.total_products || 0)}
              </p>
            </div>
            <div className="p-3 rounded-xl bg-purple-50 dark:bg-purple-950/40 border border-purple-200/60 dark:border-purple-900/40">
              <p className="text-[11px] font-semibold text-purple-700 dark:text-purple-300">Success Rate</p>
              <p className="text-xl font-extrabold text-purple-900 dark:text-purple-100 mt-0.5">
                {userDetail?.stats?.success_rate || 0}%
              </p>
            </div>
            <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200/60 dark:border-amber-900/40">
              <p className="text-[11px] font-semibold text-amber-700 dark:text-amber-300">Unique Domains</p>
              <p className="text-xl font-extrabold text-amber-900 dark:text-amber-100 mt-0.5">
                {userDetail?.stats?.unique_domains?.length || 0}
              </p>
            </div>
          </div>

          {/* User's Jobs Section */}
          <div className="space-y-3 pt-2 border-t border-gray-200 dark:border-gray-700">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="flex items-center gap-2">
                <BriefcaseIcon className="w-5 h-5 text-primary-500" />
                <h4 className="font-bold text-gray-900 dark:text-white text-sm">
                  Scraping Jobs Launched by @{userDetail?.username} ({jobs.length})
                </h4>
              </div>

              {/* Job Filters & Search */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className="relative">
                  <MagnifyingGlassIcon className="w-4 h-4 text-gray-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search jobs / domain..."
                    className="pl-8 pr-3 py-1 text-xs rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white w-44 focus:ring-1 focus:ring-primary-500"
                  />
                </div>

                <div className="flex items-center bg-gray-100 dark:bg-gray-800 p-0.5 rounded-lg text-xs">
                  {['all', 'completed', 'running', 'failed'].map((st) => (
                    <button
                      key={st}
                      type="button"
                      onClick={() => setJobFilter(st)}
                      className={`px-2.5 py-1 rounded capitalize font-medium transition-colors ${
                        jobFilter === st
                          ? 'bg-white dark:bg-gray-700 text-primary-600 dark:text-primary-300 shadow-sm font-semibold'
                          : 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'
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
              <div className="p-8 text-center rounded-xl border border-dashed border-gray-200 dark:border-gray-700 text-gray-400 text-xs">
                {jobs.length === 0
                  ? `User @${userDetail?.username} has not launched any scraping jobs yet.`
                  : 'No jobs match your current search / filter.'}
              </div>
            ) : (
              <div className="overflow-x-auto max-h-72 overflow-y-auto rounded-xl border border-gray-200 dark:border-gray-700">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-xs">
                  <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0 z-10">
                    <tr>
                      <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Job</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Domain</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Status</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Products</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Pages</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Created</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800/60">
                    {filteredJobs.map((j) => (
                      <tr key={j.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/80 transition-colors">
                        <td className="px-3 py-2">
                          <Link
                            to={`/jobs/${j.job_id}`}
                            className="font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400 font-mono"
                          >
                            {j.job_id}
                          </Link>
                          <p className="text-[11px] text-gray-400 truncate max-w-[180px]">{j.name}</p>
                        </td>
                        <td className="px-3 py-2 text-gray-600 dark:text-gray-300 font-medium">
                          {j.domain}
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold capitalize ${
                              j.status.toLowerCase() === 'completed'
                                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                                : j.status.toLowerCase() === 'running'
                                ? 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 animate-pulse'
                                : j.status.toLowerCase() === 'failed'
                                ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                                : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
                            }`}
                          >
                            {j.status}
                          </span>
                        </td>
                        <td className="px-3 py-2 font-bold text-gray-900 dark:text-white">
                          {formatNumber(j.total_products || 0)}
                        </td>
                        <td className="px-3 py-2 text-gray-500">
                          {j.scraped_pages || 0} / {j.total_pages || '∞'}
                        </td>
                        <td className="px-3 py-2 text-gray-400 whitespace-nowrap">
                          {j.created_at ? formatDate(j.created_at) : '—'}
                        </td>
                        <td className="px-3 py-2">
                          <Link
                            to={`/jobs/${j.job_id}`}
                            className="p-1 rounded text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 inline-block"
                            title="Open full job details"
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
