import React, { useState, useEffect, useCallback } from 'react'
import {
  ServerStackIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  NoSymbolIcon,
  ArrowPathIcon,
  PlusIcon,
  PlayIcon,
  TrashIcon,
  ShieldCheckIcon,
  ShieldExclamationIcon,
  GlobeAltIcon,
  BoltIcon,
  MagnifyingGlassIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import proxyService from '@/services/proxyService'
import Card from '@/components/Common/Card'
import Badge from '@/components/Common/Badge'
import Button from '@/components/Common/Button'
import Modal from '@/components/Common/Modal'
import EmptyState from '@/components/Common/EmptyState'
import Spinner from '@/components/Common/Spinner'

export default function Proxies() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState({
    total: 0,
    healthy: 0,
    cooling: 0,
    banned: 0,
    inactive: 0,
    avg_latency_ms: 0,
    pool_success_rate: 0,
    proxies: [],
  })
  const [domainMetrics, setDomainMetrics] = useState([])
  
  // Filters
  const [statusFilter, setStatusFilter] = useState('all')
  const [protocolFilter, setProtocolFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [testTargetUrl, setTestTargetUrl] = useState('https://httpbin.org/ip')

  // Modals & Action States
  const [showImportModal, setShowImportModal] = useState(false)
  const [importText, setImportText] = useState('')
  const [defaultProtocol, setDefaultProtocol] = useState('http')
  const [importCountry, setImportCountry] = useState('')
  const [importing, setImporting] = useState(false)
  
  const [testingAll, setTestingAll] = useState(false)
  const [testingId, setTestingId] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const [poolRes, domainRes] = await Promise.all([
        proxyService.getProxies({
          status: statusFilter,
          protocol: protocolFilter || undefined,
          search: searchQuery || undefined,
        }),
        proxyService.getDomainMetrics().catch(() => []),
      ])
      setData(poolRes)
      setDomainMetrics(domainRes || [])
    } catch (err) {
      console.error('Failed to load proxy pool data:', err)
      toast.error('Failed to fetch proxy pool metrics')
    } finally {
      setLoading(false)
    }
  }, [statusFilter, protocolFilter, searchQuery])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleTestSingle = async (proxyId) => {
    try {
      setTestingId(proxyId)
      const res = await proxyService.testProxy(proxyId, testTargetUrl)
      if (res.success) {
        toast.success(`Proxy verified! Latency: ${res.latency_ms}ms (IP: ${res.exit_ip || 'Verified'})`)
      } else {
        toast.error(`Proxy check failed: ${res.error || `HTTP ${res.status_code}`}`)
      }
      fetchData()
    } catch (err) {
      toast.error('Network error testing proxy')
    } finally {
      setTestingId(null)
    }
  }

  const handleTestAll = async () => {
    try {
      setTestingAll(true)
      toast.loading(`Testing all active proxies against ${testTargetUrl}...`, { id: 'test-all' })
      const res = await proxyService.testAllProxies(testTargetUrl)
      toast.dismiss('test-all')
      toast.success(`Completed! ${res.successful} healthy, ${res.failed} failed out of ${res.total}`)
      fetchData()
    } catch (err) {
      toast.dismiss('test-all')
      toast.error('Failed to execute bulk proxy test')
    } finally {
      setTestingAll(false)
    }
  }

  const handleToggleBlacklist = async (proxy) => {
    const nextBanned = !proxy.is_banned
    try {
      await proxyService.toggleBlacklist(
        proxy.id,
        nextBanned,
        nextBanned ? 'Manual user ban' : null
      )
      toast.success(nextBanned ? 'Proxy blacklisted' : 'Proxy unbanned & restored')
      fetchData()
    } catch (err) {
      toast.error('Failed to update proxy blacklist status')
    }
  }

  const handleToggleActive = async (proxy) => {
    try {
      await proxyService.updateProxy(proxy.id, { is_active: !proxy.is_active })
      toast.success(!proxy.is_active ? 'Proxy enabled' : 'Proxy disabled')
      fetchData()
    } catch (err) {
      toast.error('Failed to update proxy status')
    }
  }

  const handleDelete = async (proxyId) => {
    if (!window.confirm('Are you sure you want to remove this proxy from the rotation pool?')) return
    try {
      await proxyService.deleteProxy(proxyId)
      toast.success('Proxy deleted successfully')
      fetchData()
    } catch (err) {
      toast.error('Failed to delete proxy')
    }
  }

  const handleResetMetrics = async () => {
    if (!window.confirm('Reset all success/failure telemetry and response timers for the proxy pool?')) return
    try {
      await proxyService.resetMetrics()
      toast.success('Telemetry counters reset successfully')
      fetchData()
    } catch (err) {
      toast.error('Failed to reset metrics')
    }
  }

  const handleImportSubmit = async (e) => {
    e.preventDefault()
    if (!importText.trim()) {
      toast.error('Please enter at least one proxy')
      return
    }
    try {
      setImporting(true)
      const res = await proxyService.importProxies({
        proxies: importText,
        default_protocol: defaultProtocol,
        country_code: importCountry.trim() ? importCountry.toUpperCase() : undefined,
      })
      toast.success(`Import complete: ${res.added} added, ${res.skipped} existing skipped`)
      setImportText('')
      setImportCountry('')
      setShowImportModal(false)
      fetchData()
    } catch (err) {
      toast.error('Failed to import proxies')
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ServerStackIcon className="w-8 h-8 text-primary-600 dark:text-primary-400" />
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Browser Proxy Rotation Dashboard
            </h1>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Real-time pool health, domain anti-bot detection, latency diagnostics, and automated rotation telemetry.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={handleResetMetrics}
            title="Reset telemetry"
          >
            Reset Metrics
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchData}
            disabled={loading}
          >
            <ArrowPathIcon className={`w-4 h-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleTestAll}
            disabled={testingAll || data.total === 0}
          >
            <PlayIcon className={`w-4 h-4 mr-1.5 text-emerald-600 ${testingAll ? 'animate-spin' : ''}`} />
            {testingAll ? 'Testing Pool...' : 'Test All Proxies'}
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowImportModal(true)}
          >
            <PlusIcon className="w-4 h-4 mr-1.5" />
            Import Proxies
          </Button>
        </div>
      </div>

      {/* Metric Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card className="p-4 border-l-4 border-l-primary-500">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Pool</div>
          <div className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">{data.total}</div>
          <div className="text-xs text-gray-400 mt-0.5">Configured nodes</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-500">
          <div className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">Healthy Active</div>
          <div className="mt-2 text-2xl font-bold text-emerald-600 dark:text-emerald-400">{data.healthy}</div>
          <div className="text-xs text-gray-400 mt-0.5">Ready for scraping</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-amber-500">
          <div className="text-xs font-semibold text-amber-600 uppercase tracking-wider">Cooling Down</div>
          <div className="mt-2 text-2xl font-bold text-amber-600 dark:text-amber-400">{data.cooling}</div>
          <div className="text-xs text-gray-400 mt-0.5">Temp rate-limit pause</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-rose-500">
          <div className="text-xs font-semibold text-rose-600 uppercase tracking-wider">Blacklisted</div>
          <div className="mt-2 text-2xl font-bold text-rose-600 dark:text-rose-400">{data.banned}</div>
          <div className="text-xs text-gray-400 mt-0.5">Anti-bot banned</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-sky-500">
          <div className="text-xs font-semibold text-sky-600 uppercase tracking-wider">Avg Latency</div>
          <div className="mt-2 text-2xl font-bold text-sky-600 dark:text-sky-400">
            {data.avg_latency_ms ? `${data.avg_latency_ms} ms` : '—'}
          </div>
          <div className="text-xs text-gray-400 mt-0.5">Global response speed</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-indigo-500">
          <div className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">Success Rate</div>
          <div className="mt-2 text-2xl font-bold text-indigo-600 dark:text-indigo-400">
            {data.pool_success_rate}%
          </div>
          <div className="text-xs text-gray-400 mt-0.5">{data.total_success} / {data.total_success + data.total_failures} reqs</div>
        </Card>
      </div>

      {/* Target Test Target Bar */}
      <Card className="p-4 bg-gray-50/70 dark:bg-gray-800/50">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2">
            <BoltIcon className="w-5 h-5 text-amber-500" />
            <span className="text-sm font-semibold text-gray-900 dark:text-white">Active Test Target:</span>
            <input
              type="text"
              value={testTargetUrl}
              onChange={(e) => setTestTargetUrl(e.target.value)}
              className="text-xs px-2.5 py-1.5 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 w-64 md:w-80"
              placeholder="https://httpbin.org/ip"
            />
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs text-gray-500">Quick presets:</span>
            {[
              { label: 'HTTPBin (IP)', url: 'https://httpbin.org/ip' },
              { label: 'Amazon', url: 'https://www.amazon.com' },
              { label: 'Walmart', url: 'https://www.walmart.com' },
              { label: 'eBay', url: 'https://www.ebay.com' },
            ].map((p) => (
              <button
                key={p.label}
                onClick={() => setTestTargetUrl(p.url)}
                className={`text-xs px-2 py-1 rounded transition-colors ${
                  testTargetUrl === p.url
                    ? 'bg-primary-600 text-white font-medium'
                    : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-600 hover:bg-gray-100'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Domain Anti-Bot & Success Rate Matrix */}
      {domainMetrics.length > 0 && (
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <GlobeAltIcon className="w-5 h-5 text-primary-500" />
                Domain Anti-Bot & Scrape Health Matrix
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Per-domain success rates and automated block metrics across competitor domains.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {domainMetrics.map((dm) => (
              <div
                key={dm.domain}
                className="p-3.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/80 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm text-gray-900 dark:text-white capitalize">
                    {dm.domain}
                  </span>
                  <Badge variant={dm.success_rate >= 80 ? 'success' : dm.success_rate >= 50 ? 'warning' : 'danger'}>
                    {dm.success_rate}% success
                  </Badge>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-1.5 rounded-full ${
                      dm.success_rate >= 80 ? 'bg-emerald-500' : dm.success_rate >= 50 ? 'bg-amber-500' : 'bg-rose-500'
                    }`}
                    style={{ width: `${Math.max(4, dm.success_rate)}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 pt-1">
                  <span>{dm.total_requests} requests</span>
                  <span>{dm.avg_latency_ms ? `${dm.avg_latency_ms}ms` : '—'}</span>
                  {dm.banned_proxies > 0 ? (
                    <span className="text-rose-500 font-medium">{dm.banned_proxies} banned</span>
                  ) : (
                    <span className="text-emerald-500 font-medium">All active</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1.5 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
          {[
            { id: 'all', label: 'All Proxies' },
            { id: 'healthy', label: 'Healthy' },
            { id: 'cooling', label: 'Cooling' },
            { id: 'banned', label: 'Banned' },
            { id: 'inactive', label: 'Inactive' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`text-xs px-3 py-1.5 rounded-md font-medium transition-all ${
                statusFilter === tab.id
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search & Protocol Select */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <MagnifyingGlassIcon className="w-4 h-4 absolute left-3 top-2.5 text-gray-400" />
            <input
              type="text"
              placeholder="Search host, country, IP..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="text-xs pl-9 pr-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 w-52 md:w-64"
            />
          </div>

          <select
            value={protocolFilter}
            onChange={(e) => setProtocolFilter(e.target.value)}
            className="text-xs px-2.5 py-1.5 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          >
            <option value="">All Protocols</option>
            <option value="http">HTTP</option>
            <option value="https">HTTPS</option>
            <option value="socks5">SOCKS5</option>
          </select>
        </div>
      </div>

      {/* Proxies Table */}
      <Card className="overflow-hidden">
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center">
            <Spinner size="lg" />
            <p className="text-sm text-gray-500 mt-3">Loading proxy pool telemetry...</p>
          </div>
        ) : data.proxies.length === 0 ? (
          <EmptyState
            icon={ServerStackIcon}
            title="No Proxies Found"
            description="Add proxies to enable automated headless browser rotation and anti-ban evasion."
            action={
              <Button size="sm" variant="primary" onClick={() => setShowImportModal(true)}>
                <PlusIcon className="w-4 h-4 mr-1.5" />
                Import Proxies
              </Button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/80 border-b border-gray-200 dark:border-gray-700 text-gray-500 uppercase tracking-wider">
                  <th className="py-3 px-4 font-semibold">Proxy Server</th>
                  <th className="py-3 px-3 font-semibold">Protocol</th>
                  <th className="py-3 px-3 font-semibold">Country</th>
                  <th className="py-3 px-3 font-semibold">Health State</th>
                  <th className="py-3 px-3 font-semibold">Latency</th>
                  <th className="py-3 px-3 font-semibold">Success Rate</th>
                  <th className="py-3 px-3 font-semibold">Exit IP / Last Checked</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {data.proxies.map((proxy) => {
                  const isTesting = testingId === proxy.id

                  return (
                    <tr
                      key={proxy.id}
                      className="hover:bg-gray-50/70 dark:hover:bg-gray-800/40 transition-colors"
                    >
                      {/* Server Address */}
                      <td className="py-3 px-4 font-mono font-medium text-gray-900 dark:text-gray-100">
                        <div className="flex items-center gap-1.5">
                          <span>{proxy.raw_url}</span>
                          {proxy.has_auth && (
                            <span className="text-[10px] px-1 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                              Auth
                            </span>
                          )}
                        </div>
                        {proxy.ban_reason && (
                          <div className="text-[11px] text-rose-500 font-sans mt-0.5">
                            {proxy.ban_reason}
                          </div>
                        )}
                        {proxy.cooldown_remaining_sec > 0 && (
                          <div className="text-[11px] text-amber-500 font-sans mt-0.5">
                            Cooldown: {proxy.cooldown_remaining_sec}s remaining
                          </div>
                        )}
                      </td>

                      {/* Protocol */}
                      <td className="py-3 px-3 uppercase font-semibold text-gray-600 dark:text-gray-300">
                        {proxy.protocol}
                      </td>

                      {/* Country */}
                      <td className="py-3 px-3">
                        <span className="px-1.5 py-0.5 rounded text-[11px] font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200">
                          {proxy.country_code || 'US'}
                        </span>
                      </td>

                      {/* State Badge */}
                      <td className="py-3 px-3">
                        {proxy.state === 'healthy' && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300">
                            <CheckCircleIcon className="w-3.5 h-3.5" />
                            Healthy
                          </span>
                        )}
                        {proxy.state === 'cooling' && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300">
                            <ExclamationTriangleIcon className="w-3.5 h-3.5" />
                            Cooling
                          </span>
                        )}
                        {proxy.state === 'banned' && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300">
                            <NoSymbolIcon className="w-3.5 h-3.5" />
                            Banned
                          </span>
                        )}
                        {proxy.state === 'inactive' && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                            Inactive
                          </span>
                        )}
                      </td>

                      {/* Latency */}
                      <td className="py-3 px-3 font-medium">
                        {proxy.latency_ms ? (
                          <span
                            className={
                              proxy.latency_ms < 300
                                ? 'text-emerald-600'
                                : proxy.latency_ms < 800
                                ? 'text-amber-600'
                                : 'text-rose-600'
                            }
                          >
                            {proxy.latency_ms} ms
                          </span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>

                      {/* Success Rate */}
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-gray-900 dark:text-white">
                            {proxy.success_rate}%
                          </span>
                          <span className="text-gray-400 text-[10px]">
                            ({proxy.success_count}/{proxy.success_count + proxy.failure_count})
                          </span>
                        </div>
                      </td>

                      {/* Exit IP / Last Checked */}
                      <td className="py-3 px-3 text-gray-500 dark:text-gray-400">
                        <div className="font-mono text-gray-700 dark:text-gray-200">
                          {proxy.last_exit_ip || '—'}
                        </div>
                        <div className="text-[10px] mt-0.5">
                          {proxy.last_checked_at
                            ? new Date(proxy.last_checked_at).toLocaleTimeString()
                            : 'Never checked'}
                        </div>
                      </td>

                      {/* Action Buttons */}
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Test Ping */}
                          <button
                            onClick={() => handleTestSingle(proxy.id)}
                            disabled={isTesting}
                            className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 transition-colors"
                            title="Ping proxy"
                          >
                            <PlayIcon className={`w-4 h-4 ${isTesting ? 'animate-spin text-primary-500' : ''}`} />
                          </button>

                          {/* Blacklist / Unban Toggle */}
                          <button
                            onClick={() => handleToggleBlacklist(proxy)}
                            className={`p-1 rounded transition-colors ${
                              proxy.is_banned
                                ? 'text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/40'
                                : 'text-gray-400 hover:text-rose-500 hover:bg-gray-200 dark:hover:bg-gray-700'
                            }`}
                            title={proxy.is_banned ? 'Unban proxy' : 'Blacklist proxy'}
                          >
                            {proxy.is_banned ? (
                              <ShieldExclamationIcon className="w-4 h-4" />
                            ) : (
                              <ShieldCheckIcon className="w-4 h-4" />
                            )}
                          </button>

                          {/* Enable / Disable */}
                          <button
                            onClick={() => handleToggleActive(proxy)}
                            className={`text-[11px] px-1.5 py-0.5 rounded font-medium transition-colors ${
                              proxy.is_active
                                ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100'
                                : 'bg-gray-100 dark:bg-gray-800 text-gray-500 hover:bg-gray-200'
                            }`}
                          >
                            {proxy.is_active ? 'ON' : 'OFF'}
                          </button>

                          {/* Delete */}
                          <button
                            onClick={() => handleDelete(proxy.id)}
                            className="p-1 rounded text-gray-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
                            title="Delete proxy"
                          >
                            <TrashIcon className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Bulk Import Modal */}
      <Modal
        isOpen={showImportModal}
        onClose={() => setShowImportModal(false)}
        title="Import Proxies into Rotation Pool"
      >
        <form onSubmit={handleImportSubmit} className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Paste one proxy per line or separated by commas. Supported formats:
          </p>

          <div className="bg-gray-100 dark:bg-gray-800 p-2.5 rounded text-xs font-mono text-gray-700 dark:text-gray-300 space-y-1">
            <div>http://user:password@192.168.1.1:8080</div>
            <div>socks5://10.0.0.1:1080</div>
            <div>192.168.1.1:8080:username:password</div>
            <div>192.168.1.1:8080</div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Proxy List:
            </label>
            <textarea
              rows={6}
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              placeholder="http://proxy1.example.com:8080&#10;http://user:pass@proxy2.example.com:8080"
              className="w-full text-xs font-mono p-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Default Protocol:
              </label>
              <select
                value={defaultProtocol}
                onChange={(e) => setDefaultProtocol(e.target.value)}
                className="w-full text-xs p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              >
                <option value="http">HTTP</option>
                <option value="https">HTTPS</option>
                <option value="socks5">SOCKS5</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Country Code (Optional):
              </label>
              <input
                type="text"
                maxLength={3}
                placeholder="US, DE, GB..."
                value={importCountry}
                onChange={(e) => setImportCountry(e.target.value)}
                className="w-full text-xs p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowImportModal(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={importing}
            >
              {importing ? 'Importing...' : 'Add Proxies'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
