import React, { useState, useEffect } from 'react'
import {
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  PlusIcon,
  PlayIcon,
  TrashIcon,
  AdjustmentsHorizontalIcon,
  ClockIcon,
  CheckCircleIcon,
  BoltIcon,
  ArrowTrendingUpIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  Input,
  Select,
  Badge,
  Modal,
} from '@/components/Common'
import throttlingService from '@/services/throttlingService'

export default function DomainThrottlingSettings() {
  const [domains, setDomains] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeSubTab, setActiveSubTab] = useState('domains') // 'domains' | 'simulator'

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingDomain, setEditingDomain] = useState(null)
  const [form, setForm] = useState({
    domain: '',
    requests_per_second: 2.0,
    burst_capacity: 5,
    max_concurrency: 2,
    min_delay_seconds: 0.5,
    max_delay_seconds: 30.0,
    backoff_multiplier: 2.0,
    jitter_type: 'full',
    is_adaptive: true,
  })

  // Simulator State
  const [simForm, setSimForm] = useState({
    min_delay_seconds: 0.5,
    max_delay_seconds: 30.0,
    backoff_multiplier: 2.0,
    consecutive_errors: 5,
    jitter_type: 'full',
  })
  const [simResults, setSimResults] = useState([])
  const [simulating, setSimulating] = useState(false)

  const fetchDomains = async () => {
    try {
      setLoading(true)
      const data = await throttlingService.getDomains()
      setDomains(data || [])
    } catch (err) {
      console.error('Failed to load domain rate limits:', err)
      toast.error('Failed to load rate limiting policies')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDomains()
  }, [])

  const handleOpenCreate = () => {
    setEditingDomain(null)
    setForm({
      domain: '',
      requests_per_second: 2.0,
      burst_capacity: 5,
      max_concurrency: 2,
      min_delay_seconds: 0.5,
      max_delay_seconds: 30.0,
      backoff_multiplier: 2.0,
      jitter_type: 'full',
      is_adaptive: true,
    })
    setIsModalOpen(true)
  }

  const handleOpenEdit = (p) => {
    setEditingDomain(p.domain)
    setForm({
      domain: p.domain,
      requests_per_second: p.requests_per_second || 2.0,
      burst_capacity: p.burst_capacity || 5,
      max_concurrency: p.max_concurrency || 2,
      min_delay_seconds: p.min_delay_seconds || 0.5,
      max_delay_seconds: p.max_delay_seconds || 30.0,
      backoff_multiplier: p.backoff_multiplier || 2.0,
      jitter_type: p.jitter_type || 'full',
      is_adaptive: p.is_adaptive ?? true,
    })
    setIsModalOpen(true)
  }

  const handleSavePolicy = async (e) => {
    e.preventDefault()
    if (!form.domain.trim()) {
      toast.error('Domain is required')
      return
    }
    try {
      await throttlingService.upsertDomain({
        ...form,
        domain: form.domain.trim().toLowerCase(),
        requests_per_second: parseFloat(form.requests_per_second),
        burst_capacity: parseInt(form.burst_capacity, 10),
        max_concurrency: parseInt(form.max_concurrency, 10),
        min_delay_seconds: parseFloat(form.min_delay_seconds),
        max_delay_seconds: parseFloat(form.max_delay_seconds),
        backoff_multiplier: parseFloat(form.backoff_multiplier),
      })
      toast.success(`Rate limit policy for ${form.domain} saved`)
      setIsModalOpen(false)
      fetchDomains()
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to save policy')
    }
  }

  const handleResetBackoff = async (domain) => {
    try {
      await throttlingService.resetDomain(domain)
      toast.success(`Reset backoff for ${domain}. Restored to healthy status.`)
      fetchDomains()
    } catch (err) {
      toast.error('Failed to reset domain backoff')
    }
  }

  const handleDeletePolicy = async (domain) => {
    if (!confirm(`Revert ${domain} policy back to default settings?`)) return
    try {
      await throttlingService.deleteDomain(domain)
      toast.success(`Reverted ${domain} to default settings`)
      fetchDomains()
    } catch (err) {
      toast.error('Failed to delete policy')
    }
  }

  const handleRunSimulation = async (e) => {
    e?.preventDefault()
    try {
      setSimulating(true)
      const data = await throttlingService.simulateBackoff({
        min_delay_seconds: parseFloat(simForm.min_delay_seconds),
        max_delay_seconds: parseFloat(simForm.max_delay_seconds),
        backoff_multiplier: parseFloat(simForm.backoff_multiplier),
        consecutive_errors: parseInt(simForm.consecutive_errors, 10),
        jitter_type: simForm.jitter_type,
      })
      setSimResults(data || [])
    } catch (err) {
      toast.error('Simulation failed')
    } finally {
      setSimulating(false)
    }
  }

  // Quick preset helper
  const handleSelectPreset = (dom, rps, conc, minD, maxD) => {
    setForm((prev) => ({
      ...prev,
      domain: dom,
      requests_per_second: rps,
      max_concurrency: conc,
      min_delay_seconds: minD,
      max_delay_seconds: maxD,
    }))
  }

  // Summary Metrics
  const totalMonitored = domains.length
  const totalThrottled = domains.filter((d) => d.runtime_status === 'throttled' || d.runtime_status === 'cooldown').length
  const total429s = domains.reduce((acc, curr) => acc + (curr.total_throttled_429 || 0), 0)

  return (
    <div className="space-y-6">
      {/* Top Banner & Quick Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-4 border-l-4 border-l-primary-500">
          <div className="text-xs font-semibold uppercase text-gray-500">Configured Domains</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{totalMonitored}</div>
          <div className="text-xs text-gray-400 mt-0.5">Active token-bucket controllers</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-500">
          <div className="text-xs font-semibold uppercase text-emerald-600">Throttled / Cooldown</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white mt-1 flex items-center gap-2">
            <span>{totalThrottled}</span>
            {totalThrottled > 0 && (
              <span className="text-xs px-2 py-0.5 bg-amber-500/20 text-amber-500 rounded font-bold">
                Adaptive backoff active
              </span>
            )}
          </div>
          <div className="text-xs text-gray-400 mt-0.5">Domains backing off from 429/503</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-indigo-500">
          <div className="text-xs font-semibold uppercase text-indigo-500">Total 429 Blocks Absorbed</div>
          <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">{total429s}</div>
          <div className="text-xs text-gray-400 mt-0.5">Rate limit errors safely mitigated</div>
        </Card>
      </div>

      {/* Sub Tabs */}
      <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-800 pb-2">
        <div className="flex gap-4 text-sm font-medium">
          <button
            type="button"
            onClick={() => setActiveSubTab('domains')}
            className={`pb-2 px-1 border-b-2 flex items-center gap-2 transition-colors ${
              activeSubTab === 'domains'
                ? 'border-primary-600 text-primary-600 dark:text-primary-400 font-semibold'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <ShieldCheckIcon className="w-4 h-4" />
            Domain Rate Limit Policies
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveSubTab('simulator')
              if (simResults.length === 0) handleRunSimulation()
            }}
            className={`pb-2 px-1 border-b-2 flex items-center gap-2 transition-colors ${
              activeSubTab === 'simulator'
                ? 'border-primary-600 text-primary-600 dark:text-primary-400 font-semibold'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <AdjustmentsHorizontalIcon className="w-4 h-4" />
            Backoff & Jitter Simulator
          </button>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchDomains} disabled={loading}>
            <ArrowPathIcon className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="primary" size="sm" onClick={handleOpenCreate}>
            <PlusIcon className="w-4 h-4 mr-1" />
            Add Domain Policy
          </Button>
        </div>
      </div>

      {/* TAB 1: DOMAIN POLICIES TABLE */}
      {activeSubTab === 'domains' && (
        <Card padding="none">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800 text-xs">
              <thead className="bg-gray-50 dark:bg-gray-800/80 text-gray-500 uppercase font-semibold">
                <tr>
                  <th className="px-4 py-3 text-left">Target Domain</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Flow Rate</th>
                  <th className="px-4 py-3 text-left">Current Delay</th>
                  <th className="px-4 py-3 text-left">Jitter Strategy</th>
                  <th className="px-4 py-3 text-left">429 / 503 Count</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800/60">
                {domains.map((d) => (
                  <tr key={d.domain} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/40 transition-colors">
                    <td className="px-4 py-3 font-semibold text-gray-900 dark:text-gray-100">
                      <div className="flex items-center gap-2">
                        <span>{d.domain}</span>
                        {d.domain === 'default' && (
                          <span className="text-[10px] bg-gray-700 text-gray-300 px-1.5 py-0.2 rounded font-normal">
                            Global Fallback
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase ${
                        d.runtime_status === 'healthy'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                          : d.runtime_status === 'cooldown'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                          : d.runtime_status === 'throttled'
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                          : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30'
                      }`}>
                        {d.runtime_status || 'healthy'}
                      </span>
                    </td>

                    <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                      <div className="font-medium">
                        {d.requests_per_second} req/s <span className="text-gray-400">({d.max_concurrency} slots)</span>
                      </div>
                      <div className="text-[10px] text-gray-400">Burst: {d.burst_capacity} tokens</div>
                    </td>

                    <td className="px-4 py-3">
                      <div className="font-semibold text-gray-900 dark:text-gray-200">
                        {d.current_delay ? `${d.current_delay}s` : `${d.min_delay_seconds}s`}
                      </div>
                      {d.consecutive_throttles > 0 && (
                        <div className="text-[10px] text-rose-400 font-medium">
                          {d.consecutive_throttles}x backoff multiplier
                        </div>
                      )}
                    </td>

                    <td className="px-4 py-3 uppercase text-gray-500 font-mono text-[11px]">
                      {d.jitter_type || 'full'}
                    </td>

                    <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                      <div>
                        <span className="font-bold text-amber-500">{d.total_throttled_429 || 0}</span> 429s
                      </div>
                      <div className="text-[10px] text-gray-400">
                        {d.total_requests || 0} total requests
                      </div>
                    </td>

                    <td className="px-4 py-3 text-right space-x-2">
                      <Button
                        variant="outline"
                        size="xs"
                        onClick={() => handleResetBackoff(d.domain)}
                        title="Clear cooldown & reset backoff"
                      >
                        Reset Backoff
                      </Button>
                      <Button
                        variant="secondary"
                        size="xs"
                        onClick={() => handleOpenEdit(d)}
                      >
                        Edit
                      </Button>
                      {d.domain !== 'default' && (
                        <Button
                          variant="danger"
                          size="xs"
                          onClick={() => handleDeletePolicy(d.domain)}
                          title="Revert to defaults"
                        >
                          <TrashIcon className="w-3.5 h-3.5" />
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* TAB 2: BACKOFF & JITTER SIMULATOR */}
      {activeSubTab === 'simulator' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <AdjustmentsHorizontalIcon className="w-5 h-5 text-indigo-500" />
                Exponential Backoff & Full Jitter Simulator
              </CardTitle>
            </CardHeader>

            <form onSubmit={handleRunSimulation} className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Base Min Delay (s)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={simForm.min_delay_seconds}
                  onChange={(e) => setSimForm({ ...simForm, min_delay_seconds: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-200"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Max Delay Ceiling (s)</label>
                <input
                  type="number"
                  step="1"
                  min="1"
                  value={simForm.max_delay_seconds}
                  onChange={(e) => setSimForm({ ...simForm, max_delay_seconds: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-200"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Backoff Multiplier</label>
                <input
                  type="number"
                  step="0.1"
                  min="1.1"
                  value={simForm.backoff_multiplier}
                  onChange={(e) => setSimForm({ ...simForm, backoff_multiplier: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-200"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Jitter Strategy</label>
                <select
                  value={simForm.jitter_type}
                  onChange={(e) => setSimForm({ ...simForm, jitter_type: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-200"
                >
                  <option value="full">Full Jitter (AWS Recommended)</option>
                  <option value="decorrelated">Decorrelated Jitter</option>
                  <option value="equal">Equal Half Jitter</option>
                  <option value="none">No Jitter (Deterministic)</option>
                </select>
              </div>

              <div className="flex items-end">
                <Button type="submit" variant="primary" size="sm" className="w-full justify-center" isLoading={simulating}>
                  Simulate Curve
                </Button>
              </div>
            </form>
          </Card>

          {/* Results Table */}
          {simResults.length > 0 && (
            <Card padding="none">
              <div className="p-4 border-b border-gray-800 font-semibold text-xs text-gray-300 flex justify-between items-center">
                <span>Simulation Output Across Consecutive HTTP 429 Errors</span>
                <span className="text-xs text-gray-500">Decorrelates request bursts to prevent thundering herds</span>
              </div>
              <table className="min-w-full divide-y divide-gray-800 text-xs">
                <thead className="bg-gray-900 text-gray-400 uppercase font-semibold">
                  <tr>
                    <th className="px-4 py-2.5 text-left">Error Sequence</th>
                    <th className="px-4 py-2.5 text-left">Raw Exponential Base</th>
                    <th className="px-4 py-2.5 text-left">Effective Jittered Delay</th>
                    <th className="px-4 py-2.5 text-left">Visual Delay Scale</th>
                    <th className="px-4 py-2.5 text-left">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 bg-gray-900/30">
                  {simResults.map((r) => (
                    <tr key={r.step} className="hover:bg-gray-800/20">
                      <td className="px-4 py-2.5 font-bold text-gray-200">
                        429 Attempt #{r.consecutive_errors}
                      </td>
                      <td className="px-4 py-2.5 text-gray-400 font-mono">
                        {r.raw_backoff_seconds}s
                      </td>
                      <td className="px-4 py-2.5 font-bold text-amber-400 font-mono">
                        {r.effective_jitter_delay_seconds}s
                      </td>
                      <td className="px-4 py-2.5 w-1/3">
                        <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-amber-500 h-full rounded-full transition-all duration-300"
                            style={{
                              width: `${Math.min(100, (r.effective_jitter_delay_seconds / simForm.max_delay_seconds) * 100)}%`,
                            }}
                          />
                        </div>
                      </td>
                      <td className="px-4 py-2.5">
                        <Badge variant={r.status_preview === 'throttled' ? 'danger' : 'warning'}>
                          {r.status_preview}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </div>
      )}

      {/* CREATE / EDIT POLICY MODAL */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingDomain ? `Edit Policy: ${editingDomain}` : 'Configure New Domain Rate Limit'}
        size="md"
      >
        <form onSubmit={handleSavePolicy} className="space-y-4">
          {!editingDomain && (
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Target Host / Domain</label>
              <input
                type="text"
                value={form.domain}
                onChange={(e) => setForm({ ...form, domain: e.target.value })}
                placeholder="e.g. amazon.com, walmart.com, or default"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
                required
              />

              {/* Quick Preset Buttons */}
              <div className="flex gap-1.5 mt-2 flex-wrap text-xs">
                <span className="text-gray-500 self-center text-[11px]">Quick presets:</span>
                <button
                  type="button"
                  onClick={() => handleSelectPreset('amazon.com', 1.0, 2, 1.5, 60.0)}
                  className="px-2 py-0.5 rounded bg-gray-800 text-gray-300 hover:bg-gray-700 text-[11px]"
                >
                  Amazon (Strict)
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectPreset('walmart.com', 1.5, 2, 1.0, 45.0)}
                  className="px-2 py-0.5 rounded bg-gray-800 text-gray-300 hover:bg-gray-700 text-[11px]"
                >
                  Walmart
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectPreset('ebay.com', 3.0, 3, 0.5, 30.0)}
                  className="px-2 py-0.5 rounded bg-gray-800 text-gray-300 hover:bg-gray-700 text-[11px]"
                >
                  eBay (Moderate)
                </button>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Max Requests/Sec (RPS)</label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="50"
                value={form.requests_per_second}
                onChange={(e) => setForm({ ...form, requests_per_second: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Burst Capacity (Tokens)</label>
              <input
                type="number"
                min="1"
                max="100"
                value={form.burst_capacity}
                onChange={(e) => setForm({ ...form, burst_capacity: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Max Parallel Concurrency</label>
              <input
                type="number"
                min="1"
                max="20"
                value={form.max_concurrency}
                onChange={(e) => setForm({ ...form, max_concurrency: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Baseline Min Delay (s)</label>
              <input
                type="number"
                step="0.1"
                min="0.0"
                value={form.min_delay_seconds}
                onChange={(e) => setForm({ ...form, min_delay_seconds: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Max Backoff Delay (s)</label>
              <input
                type="number"
                step="1"
                min="1"
                value={form.max_delay_seconds}
                onChange={(e) => setForm({ ...form, max_delay_seconds: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Jitter Strategy</label>
              <select
                value={form.jitter_type}
                onChange={(e) => setForm({ ...form, jitter_type: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
              >
                <option value="full">Full Jitter (Random [0, raw])</option>
                <option value="decorrelated">Decorrelated (Stateful)</option>
                <option value="equal">Equal (Half static, half jitter)</option>
                <option value="none">None (Exact exponential)</option>
              </select>
            </div>
          </div>

          <div className="pt-2">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-gray-300">
              <input
                type="checkbox"
                checked={form.is_adaptive}
                onChange={(e) => setForm({ ...form, is_adaptive: e.target.checked })}
                className="rounded border-gray-700 bg-gray-800 text-primary-600 focus:ring-primary-500"
              />
              <span>Enable Adaptive Auto-Throttling (Automate 429 backoff & 200 recovery)</span>
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-gray-800">
            <Button variant="outline" type="button" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              Save Policy
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
