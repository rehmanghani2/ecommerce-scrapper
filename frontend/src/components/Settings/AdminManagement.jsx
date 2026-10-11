import React, { useState } from 'react'
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
  SparklesIcon,
} from '@heroicons/react/24/outline'
import { Button, Card, CardHeader, CardTitle, Badge, PageLoader, Alert } from '@/components/Common'
import { apiGet, apiPatch, apiDelete } from '@/services/api'
import { formatDate } from '@/utils/helpers'
import toast from 'react-hot-toast'

export default function AdminManagement({ currentUser }) {
  const queryClient = useQueryClient()
  const [selectedUser, setSelectedUser] = useState(null)

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
                {overview?.total_products || 0}
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
              User Access & Role Management
            </CardTitle>
            <span className="text-xs text-gray-400">
              Grant or revoke superuser privileges and deactivate rogue accounts
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
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Scrapes</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {users?.map((u) => {
                const isCurrent = u.id === currentUser?.id
                return (
                  <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-950 text-primary-700 dark:text-primary-300 font-bold text-xs flex items-center justify-center uppercase">
                          {u.username[0]}
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900 dark:text-white text-sm flex items-center gap-1.5">
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

                    <td className="px-4 py-3 text-xs font-semibold text-gray-700 dark:text-gray-300">
                      {u.job_count} jobs
                    </td>

                    <td className="px-4 py-3">
                      {!isCurrent ? (
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
                      ) : (
                        <span className="text-xs text-gray-400 font-mono">—</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
