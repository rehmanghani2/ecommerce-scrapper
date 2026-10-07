import React, { useState, useEffect } from 'react'
import {
  BellAlertIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  PlusIcon,
  TrashIcon,
  KeyIcon,
  PaperAirplaneIcon,
  CodeBracketIcon,
  EyeIcon,
  ClockIcon,
  ShieldCheckIcon,
  BuildingStorefrontIcon,
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
import alertService from '@/services/alertService'

const EVENT_OPTIONS = [
  { id: 'price_drop', label: 'Price Drops', desc: 'When competitor lowers price by >= threshold %' },
  { id: 'buybox_lost', label: 'Buy Box Lost', desc: 'When Buy Box is lost to competing seller' },
  { id: 'buybox_won', label: 'Buy Box Won', desc: 'When your store recaptures the Buy Box' },
  { id: 'out_of_stock', label: 'Out of Stock', desc: 'When competitor listing sells out' },
  { id: 'back_in_stock', label: 'Back in Stock', desc: 'When item is restocked' },
  { id: 'serp_shift', label: 'SERP Rank Shifts', desc: 'When keyword rank moves >= N positions' },
]

export default function NotificationDispatchSettings() {
  const [configs, setConfigs] = useState([])
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('dispatchers') // 'dispatchers' | 'simulator' | 'logs'

  // Filter logs
  const [logChannel, setLogChannel] = useState('')
  const [logEvent, setLogEvent] = useState('')

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState({
    channel: 'slack',
    name: '',
    is_active: true,
    webhook_url: '',
    bot_token: '',
    chat_id: '',
    hmac_secret: '',
    min_drop_percentage: 5.0,
    min_rank_shift: 3,
    store_domains: '*',
    events_subscribed: ['price_drop', 'buybox_lost', 'out_of_stock'],
  })
  const [testingModal, setTestingModal] = useState(false)

  // Webhook Simulator State
  const [simEvent, setSimEvent] = useState('price_drop')
  const [simSecret, setSimSecret] = useState('whsec_demo_secret_key_8492048')
  const [simStore, setSimStore] = useState('amazon.com')
  const [simOutput, setSimOutput] = useState(null)

  // Payload viewer modal
  const [viewingPayload, setViewingPayload] = useState(null)

  const fetchConfigs = async () => {
    try {
      setLoading(true)
      const data = await alertService.getConfigs()
      setConfigs(data || [])
    } catch (err) {
      console.error('Failed to load alert configs:', err)
      toast.error('Failed to load alert configurations')
    } finally {
      setLoading(false)
    }
  }

  const fetchLogs = async () => {
    try {
      const data = await alertService.getLogs(40, logChannel, logEvent)
      setLogs(data || [])
    } catch (err) {
      console.error('Failed to load alert logs:', err)
    }
  }

  useEffect(() => {
    fetchConfigs()
    fetchLogs()
  }, [])

  useEffect(() => {
    fetchLogs()
  }, [logChannel, logEvent])

  const handleOpenCreate = () => {
    setEditingId(null)
    setForm({
      channel: 'slack',
      name: 'Slack Deal Alerts',
      is_active: true,
      webhook_url: '',
      bot_token: '',
      chat_id: '',
      hmac_secret: '',
      min_drop_percentage: 5.0,
      min_rank_shift: 3,
      store_domains: '*',
      events_subscribed: ['price_drop', 'buybox_lost', 'out_of_stock'],
    })
    setIsModalOpen(true)
  }

  const handleOpenEdit = (cfg) => {
    setEditingId(cfg.id)
    const creds = cfg.masked_credentials || {}
    setForm({
      channel: cfg.channel || 'slack',
      name: cfg.name || '',
      is_active: cfg.is_active ?? true,
      webhook_url: creds.webhook_url || '',
      bot_token: creds.bot_token || '',
      chat_id: creds.chat_id || '',
      hmac_secret: creds.hmac_secret || '',
      min_drop_percentage: cfg.min_drop_percentage || 5.0,
      min_rank_shift: cfg.min_rank_shift || 3,
      store_domains: Array.isArray(cfg.store_domains) ? cfg.store_domains.join(', ') : (cfg.store_domains || '*'),
      events_subscribed: cfg.events_subscribed || ['price_drop'],
    })
    setIsModalOpen(true)
  }

  const handleSaveConfig = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) {
      toast.error('Dispatcher name is required')
      return
    }

    const credentials = {}
    if (form.channel === 'telegram') {
      credentials.bot_token = form.bot_token.trim()
      credentials.chat_id = form.chat_id.trim()
    } else {
      credentials.webhook_url = form.webhook_url.trim()
    }

    const storeList = form.store_domains.split(',').map((s) => s.trim()).filter(Boolean)

    try {
      await alertService.saveConfig({
        id: editingId,
        channel: form.channel,
        name: form.name.trim(),
        is_active: form.is_active,
        min_drop_percentage: parseFloat(form.min_drop_percentage),
        min_rank_shift: parseInt(form.min_rank_shift, 10),
        events_subscribed: form.events_subscribed,
        store_domains: storeList.length > 0 ? storeList : ['*'],
        hmac_secret: form.channel === 'webhook' ? form.hmac_secret.trim() : null,
        credentials,
      })
      toast.success(`${form.name} saved successfully`)
      setIsModalOpen(false)
      fetchConfigs()
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to save alert configuration')
    }
  }

  const handleDeleteConfig = async (id, name) => {
    if (!confirm(`Delete notification dispatcher "${name}"?`)) return
    try {
      await alertService.deleteConfig(id)
      toast.success('Dispatcher deleted')
      fetchConfigs()
    } catch (err) {
      toast.error('Failed to delete dispatcher')
    }
  }

  const handleTestModal = async () => {
    setTestingModal(true)
    const credentials = {}
    if (form.channel === 'telegram') {
      credentials.bot_token = form.bot_token.trim()
      credentials.chat_id = form.chat_id.trim()
    } else {
      credentials.webhook_url = form.webhook_url.trim()
    }
    try {
      const res = await alertService.testChannel(form.channel, credentials, form.hmac_secret)
      if (res.success) {
        toast.success(`Test alert delivered to ${form.channel.toUpperCase()}!`)
      } else {
        toast.error(`Test failed: ${res.message}`)
      }
    } catch (err) {
      toast.error('Test failed: ' + (err?.response?.data?.detail || err.message))
    } finally {
      setTestingModal(false)
    }
  }

  const handleGenerateSecret = () => {
    const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    let rand = 'whsec_'
    for (let i = 0; i < 32; i++) {
      rand += chars.charAt(Math.floor(Math.random() * chars.length))
    }
    setForm((prev) => ({ ...prev, hmac_secret: rand }))
  }

  const handleSimulateWebhook = async () => {
    try {
      const res = await alertService.simulateWebhook({
        event_type: simEvent,
        hmac_secret: simSecret,
        store_domain: simStore,
      })
      setSimOutput(res)
    } catch (err) {
      toast.error('Webhook simulation failed')
    }
  }

  const toggleEvent = (eventId) => {
    setForm((prev) => {
      const exists = prev.events_subscribed.includes(eventId)
      const next = exists
        ? prev.events_subscribed.filter((e) => e !== eventId)
        : [...prev.events_subscribed, eventId]
      return { ...prev, events_subscribed: next }
    })
  }

  // Summary Metrics
  const totalActive = configs.filter((c) => c.is_active).length
  const totalSent = logs.filter((l) => l.status === 'sent').length
  const totalFailed = logs.filter((l) => l.status === 'failed').length

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Card className="p-4 border-l-4 border-l-primary-500">
          <div className="text-xs font-semibold uppercase text-gray-500">Active Dispatchers</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{totalActive}</div>
          <div className="text-xs text-gray-400 mt-0.5">Channels broadcasting alerts</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-500">
          <div className="text-xs font-semibold uppercase text-emerald-600">Dispatches Delivered</div>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{totalSent}</div>
          <div className="text-xs text-gray-400 mt-0.5">Successful HTTP/API push events</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-rose-500">
          <div className="text-xs font-semibold uppercase text-rose-500">Failed Dispatches</div>
          <div className="text-2xl font-bold text-rose-600 dark:text-rose-400 mt-1">{totalFailed}</div>
          <div className="text-xs text-gray-400 mt-0.5">Webhooks / API timeouts</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-indigo-500">
          <div className="text-xs font-semibold uppercase text-indigo-500">Event Types Monitored</div>
          <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">6 Events</div>
          <div className="text-xs text-gray-400 mt-0.5">Price, Buy Box, Stock, SERP</div>
        </Card>
      </div>

      {/* Sub Tabs */}
      <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-800 pb-2">
        <div className="flex gap-4 text-sm font-medium">
          <button
            type="button"
            onClick={() => setActiveTab('dispatchers')}
            className={`pb-2 px-1 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'dispatchers'
                ? 'border-primary-600 text-primary-600 dark:text-primary-400 font-semibold'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <BellAlertIcon className="w-4 h-4" />
            Configured Dispatchers ({configs.length})
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab('simulator')
              if (!simOutput) handleSimulateWebhook()
            }}
            className={`pb-2 px-1 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'simulator'
                ? 'border-primary-600 text-primary-600 dark:text-primary-400 font-semibold'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <CodeBracketIcon className="w-4 h-4" />
            Webhook Developer & HMAC Simulator
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('logs')}
            className={`pb-2 px-1 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'logs'
                ? 'border-primary-600 text-primary-600 dark:text-primary-400 font-semibold'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <ClockIcon className="w-4 h-4" />
            Delivery Audit Log ({logs.length})
          </button>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchConfigs} disabled={loading}>
            <ArrowPathIcon className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="primary" size="sm" onClick={handleOpenCreate}>
            <PlusIcon className="w-4 h-4 mr-1" />
            New Dispatcher
          </Button>
        </div>
      </div>

      {/* TAB 1: DISPATCHERS TABLE */}
      {activeTab === 'dispatchers' && (
        <Card padding="none">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800 text-xs">
              <thead className="bg-gray-50 dark:bg-gray-800/80 text-gray-500 uppercase font-semibold">
                <tr>
                  <th className="px-4 py-3 text-left">Channel & Name</th>
                  <th className="px-4 py-3 text-left">Subscribed Events</th>
                  <th className="px-4 py-3 text-left">Store Filter</th>
                  <th className="px-4 py-3 text-left">Security</th>
                  <th className="px-4 py-3 text-left">Last Triggered</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800/60">
                {configs.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/40 transition-colors">
                    <td className="px-4 py-3 font-semibold text-gray-900 dark:text-gray-100">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] uppercase ${
                          c.channel === 'slack'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                            : c.channel === 'discord'
                            ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30'
                            : c.channel === 'telegram'
                            ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30'
                            : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                        }`}>
                          {c.channel}
                        </span>
                        <span>{c.name}</span>
                        {!c.is_active && (
                          <span className="text-[10px] bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">
                            Inactive
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {(c.events_subscribed || ['price_drop']).map((ev) => (
                          <span key={ev} className="px-1.5 py-0.2 rounded bg-gray-800 text-gray-300 text-[10px]">
                            {ev.replace('_', ' ')}
                          </span>
                        ))}
                      </div>
                    </td>

                    <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                      <div className="flex items-center gap-1">
                        <BuildingStorefrontIcon className="w-3.5 h-3.5 text-gray-500" />
                        <span>
                          {c.store_domains?.includes('*') ? 'All Stores (*)' : c.store_domains?.join(', ')}
                        </span>
                      </div>
                    </td>

                    <td className="px-4 py-3">
                      {c.has_hmac_secret ? (
                        <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-medium">
                          <ShieldCheckIcon className="w-3.5 h-3.5" />
                          HMAC-SHA256
                        </span>
                      ) : (
                        <span className="text-gray-500 text-[11px]">Standard</span>
                      )}
                    </td>

                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                      {c.last_triggered_at ? new Date(c.last_triggered_at).toLocaleString() : 'Never'}
                    </td>

                    <td className="px-4 py-3 text-right space-x-2">
                      <Button
                        variant="secondary"
                        size="xs"
                        onClick={() => handleOpenEdit(c)}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="danger"
                        size="xs"
                        onClick={() => handleDeleteConfig(c.id, c.name)}
                      >
                        <TrashIcon className="w-3.5 h-3.5" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* TAB 2: WEBHOOK SIMULATOR */}
      {activeTab === 'simulator' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <CodeBracketIcon className="w-5 h-5 text-indigo-400" />
                Developer Webhook HMAC-SHA256 Simulator
              </CardTitle>
            </CardHeader>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Simulated Event Type</label>
                <select
                  value={simEvent}
                  onChange={(e) => setSimEvent(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200"
                >
                  <option value="price_drop">price_drop</option>
                  <option value="buybox_lost">buybox_lost</option>
                  <option value="buybox_won">buybox_won</option>
                  <option value="out_of_stock">out_of_stock</option>
                  <option value="serp_shift">serp_shift</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Target Competitor Store</label>
                <input
                  type="text"
                  value={simStore}
                  onChange={(e) => setSimStore(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">HMAC Signing Secret</label>
                <input
                  type="text"
                  value={simSecret}
                  onChange={(e) => setSimSecret(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 font-mono"
                />
              </div>
            </div>

            <div className="pt-3 flex justify-end">
              <Button variant="primary" size="sm" onClick={handleSimulateWebhook}>
                Compute Headers & Payload
              </Button>
            </div>
          </Card>

          {simOutput && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Card>
                <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                  Outbound HTTP Request Headers
                </div>
                <pre className="p-3 bg-gray-900 border border-gray-800 rounded-lg text-xs font-mono text-emerald-400 overflow-x-auto">
                  {JSON.stringify(simOutput.headers, null, 2)}
                </pre>
              </Card>

              <Card>
                <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                  Signed JSON Event Body
                </div>
                <pre className="p-3 bg-gray-900 border border-gray-800 rounded-lg text-xs font-mono text-indigo-300 overflow-x-auto max-h-64">
                  {JSON.stringify(simOutput.payload, null, 2)}
                </pre>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: AUDIT LOGS */}
      {activeTab === 'logs' && (
        <Card padding="none">
          <div className="p-3 border-b border-gray-800 flex items-center justify-between flex-wrap gap-2">
            <div className="text-xs font-semibold text-gray-300">Outbound Notification Dispatch Audit</div>
            <div className="flex gap-2">
              <select
                value={logChannel}
                onChange={(e) => setLogChannel(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded text-xs px-2 py-1 text-gray-300"
              >
                <option value="">All Channels</option>
                <option value="slack">Slack</option>
                <option value="discord">Discord</option>
                <option value="telegram">Telegram</option>
                <option value="webhook">Webhook</option>
              </select>
              <select
                value={logEvent}
                onChange={(e) => setLogEvent(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded text-xs px-2 py-1 text-gray-300"
              >
                <option value="">All Events</option>
                <option value="price_drop">Price Drop</option>
                <option value="buybox_lost">Buy Box Lost</option>
                <option value="buybox_won">Buy Box Won</option>
                <option value="out_of_stock">Out of Stock</option>
                <option value="serp_shift">SERP Shift</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-800 text-xs">
              <thead className="bg-gray-900 text-gray-400 uppercase font-semibold">
                <tr>
                  <th className="px-4 py-2.5 text-left">Timestamp</th>
                  <th className="px-4 py-2.5 text-left">Event Type</th>
                  <th className="px-4 py-2.5 text-left">Channel</th>
                  <th className="px-4 py-2.5 text-left">Product / Target</th>
                  <th className="px-4 py-2.5 text-left">Store</th>
                  <th className="px-4 py-2.5 text-left">Status</th>
                  <th className="px-4 py-2.5 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 bg-gray-900/30">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-4 py-8 text-center text-gray-500">
                      No notification events dispatched yet.
                    </td>
                  </tr>
                ) : (
                  logs.map((l) => (
                    <tr key={l.id} className="hover:bg-gray-800/20">
                      <td className="px-4 py-2.5 text-gray-500 whitespace-nowrap">
                        {new Date(l.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-2.5 font-bold uppercase text-[10px] text-gray-300">
                        {l.alert_type?.replace('_', ' ')}
                      </td>
                      <td className="px-4 py-2.5 font-mono uppercase text-gray-400">
                        {l.channel}
                      </td>
                      <td className="px-4 py-2.5 font-medium text-gray-200 max-w-xs truncate">
                        {l.product_name}
                      </td>
                      <td className="px-4 py-2.5 text-gray-400">
                        {l.store_domain || '—'}
                      </td>
                      <td className="px-4 py-2.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          l.status === 'sent'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                        }`}>
                          {l.status}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        {l.payload_snapshot && (
                          <button
                            type="button"
                            onClick={() => setViewingPayload(l)}
                            className="text-indigo-400 hover:text-indigo-300 text-xs"
                          >
                            <EyeIcon className="w-4 h-4 inline" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* CREATE / EDIT DISPATCHER MODAL */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingId ? `Edit Dispatcher: ${form.name}` : 'Create Automated Notification Dispatcher'}
        size="lg"
      >
        <form onSubmit={handleSaveConfig} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Dispatcher Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. VIP Pricing Slack Channel"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Destination Channel</label>
              <select
                value={form.channel}
                onChange={(e) => setForm({ ...form, channel: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
              >
                <option value="slack">Slack (Incoming Webhook Blocks)</option>
                <option value="discord">Discord (Rich Embed Webhook)</option>
                <option value="telegram">Telegram (Bot API)</option>
                <option value="webhook">Custom Webhook (Zapier / Make / n8n)</option>
              </select>
            </div>
          </div>

          {/* Channel Credentials */}
          {form.channel === 'telegram' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 bg-gray-800/40 rounded-xl border border-gray-800">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Telegram Bot Token</label>
                <input
                  type="password"
                  value={form.bot_token}
                  onChange={(e) => setForm({ ...form, bot_token: e.target.value })}
                  placeholder="123456789:ABCDefgh..."
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Chat ID or Channel ID</label>
                <input
                  type="text"
                  value={form.chat_id}
                  onChange={(e) => setForm({ ...form, chat_id: e.target.value })}
                  placeholder="-100123456789"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-3 p-3 bg-gray-800/40 rounded-xl border border-gray-800">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Webhook Endpoint URL</label>
                <input
                  type="url"
                  value={form.webhook_url}
                  onChange={(e) => setForm({ ...form, webhook_url: e.target.value })}
                  placeholder={
                    form.channel === 'slack'
                      ? 'https://hooks.slack.com/services/...'
                      : form.channel === 'discord'
                      ? 'https://discord.com/api/webhooks/...'
                      : 'https://api.myapp.com/webhooks/ecommerce'
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
                  required
                />
              </div>

              {form.channel === 'webhook' && (
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-xs font-medium text-gray-400">HMAC-SHA256 Signing Secret (Optional)</label>
                    <button
                      type="button"
                      onClick={handleGenerateSecret}
                      className="text-xs text-indigo-400 hover:text-indigo-300"
                    >
                      Generate Secret
                    </button>
                  </div>
                  <input
                    type="text"
                    value={form.hmac_secret}
                    onChange={(e) => setForm({ ...form, hmac_secret: e.target.value })}
                    placeholder="whsec_..."
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 font-mono"
                  />
                  <span className="text-[11px] text-gray-500 mt-0.5 block">
                    Injected as X-Scraper-Signature: sha256=... in headers
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Subscribed Events Checklist */}
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-2">Subscribe to Event Types</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {EVENT_OPTIONS.map((opt) => {
                const checked = form.events_subscribed.includes(opt.id)
                return (
                  <div
                    key={opt.id}
                    onClick={() => toggleEvent(opt.id)}
                    className={`p-2.5 rounded-lg border cursor-pointer transition-colors flex items-start gap-2.5 ${
                      checked
                        ? 'bg-primary-950/40 border-primary-500/40 text-gray-100'
                        : 'bg-gray-800/40 border-gray-800 text-gray-400 hover:bg-gray-800/80'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => {}} // handled by div
                      className="mt-0.5 rounded border-gray-700 bg-gray-800 text-primary-600 focus:ring-primary-500"
                    />
                    <div>
                      <div className="font-semibold text-xs text-gray-200">{opt.label}</div>
                      <div className="text-[11px] text-gray-500">{opt.desc}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Scope Filters & Thresholds */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Store Filter</label>
              <input
                type="text"
                value={form.store_domains}
                onChange={(e) => setForm({ ...form, store_domains: e.target.value })}
                placeholder="* or amazon.com, walmart.com"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
              />
              <span className="text-[10px] text-gray-500 mt-0.5 block">Use * for all stores</span>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Min Price Drop (%)</label>
              <input
                type="number"
                step="0.5"
                min="0.1"
                max="90"
                value={form.min_drop_percentage}
                onChange={(e) => setForm({ ...form, min_drop_percentage: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Min SERP Shift (Pos)</label>
              <input
                type="number"
                min="1"
                max="50"
                value={form.min_rank_shift}
                onChange={(e) => setForm({ ...form, min_rank_shift: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
              />
            </div>
          </div>

          <div className="pt-2">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-gray-300">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                className="rounded border-gray-700 bg-gray-800 text-primary-600 focus:ring-primary-500"
              />
              <span>Enable dispatcher for live background broadcasts</span>
            </label>
          </div>

          <div className="flex justify-between items-center pt-4 border-t border-gray-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleTestModal}
              isLoading={testingModal}
            >
              <PaperAirplaneIcon className="w-3.5 h-3.5 mr-1" />
              Send Test Sample
            </Button>

            <div className="flex gap-2">
              <Button variant="outline" type="button" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit">
                Save Dispatcher
              </Button>
            </div>
          </div>
        </form>
      </Modal>

      {/* PAYLOAD INSPECTOR MODAL */}
      {viewingPayload && (
        <Modal
          isOpen={!!viewingPayload}
          onClose={() => setViewingPayload(null)}
          title={`Delivery Snapshot #${viewingPayload.id}: ${viewingPayload.product_name?.substring(0, 30)}`}
          size="md"
        >
          <div className="space-y-3">
            <div className="text-xs text-gray-400">
              Recorded at: {new Date(viewingPayload.created_at).toLocaleString()} | Channel: {viewingPayload.channel}
            </div>
            <pre className="p-3 bg-gray-900 border border-gray-800 rounded-lg text-xs font-mono text-emerald-400 overflow-x-auto max-h-80">
              {JSON.stringify(JSON.parse(viewingPayload.payload_snapshot || '{}'), null, 2)}
            </pre>
            <div className="flex justify-end">
              <Button variant="outline" onClick={() => setViewingPayload(null)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
