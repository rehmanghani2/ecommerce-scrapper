import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  ClockIcon,
  PlayIcon,
  PlusIcon,
  TrashIcon,
  PencilSquareIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  GlobeAltIcon,
  CalendarDaysIcon,
  ArrowTopRightOnSquareIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import {
  Card,
  Button,
  Badge,
  Modal,
  ModalFooter,
  EmptyState,
  PageLoader,
} from '@/components/Common'
import { scheduleService } from '@/services/scheduleService'
import { cn } from '@/utils/helpers'

const PRESET_SCHEDULES = [
  { label: 'Every 1 Hour', cron: '0 * * * *', description: 'Runs every hour at minute 0' },
  { label: 'Every 6 Hours', cron: '0 */6 * * *', description: 'Runs 4 times a day (00:00, 06:00, 12:00, 18:00)' },
  { label: 'Every 12 Hours', cron: '0 */12 * * *', description: 'Runs twice a day (00:00, 12:00)' },
  { label: 'Daily at 09:00 AM', cron: '0 9 * * *', description: 'Runs once every day at 09:00 AM UTC' },
  { label: 'Weekly on Monday', cron: '0 9 * * 1', description: 'Runs once every Monday at 09:00 AM UTC' },
  { label: 'Custom Cron Expression', cron: '', description: 'Provide custom 5-field cron expression' },
]

export default function Schedules() {
  const queryClient = useQueryClient()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingSchedule, setEditingSchedule] = useState(null)
  const [runningId, setRunningId] = useState(null)

  // Form state
  const [formName, setFormName] = useState('')
  const [formUrl, setFormUrl] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [selectedPreset, setSelectedPreset] = useState(PRESET_SCHEDULES[3])
  const [customCron, setCustomCron] = useState('')
  const [maxPages, setMaxPages] = useState(50)
  const [maxProducts, setMaxProducts] = useState(500)
  const [jsRendering, setJsRendering] = useState(false)

  // Fetch all schedules
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['schedules'],
    queryFn: () => scheduleService.listSchedules(),
  })

  const schedules = data?.schedules || []

  // Create Mutation
  const createMutation = useMutation({
    mutationFn: (payload) => scheduleService.createSchedule(payload),
    onSuccess: () => {
      toast.success('Schedule created successfully!')
      queryClient.invalidateQueries({ queryKey: ['schedules'] })
      closeModal()
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to create schedule')
    },
  })

  // Update Mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => scheduleService.updateSchedule(id, payload),
    onSuccess: () => {
      toast.success('Schedule updated successfully!')
      queryClient.invalidateQueries({ queryKey: ['schedules'] })
      closeModal()
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to update schedule')
    },
  })

  // Delete Mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => scheduleService.deleteSchedule(id),
    onSuccess: () => {
      toast.success('Schedule removed')
      queryClient.invalidateQueries({ queryKey: ['schedules'] })
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to delete schedule')
    },
  })

  const openCreateModal = () => {
    setEditingSchedule(null)
    setFormName('')
    setFormUrl('')
    setFormDescription('')
    setSelectedPreset(PRESET_SCHEDULES[3])
    setCustomCron('')
    setMaxPages(50)
    setMaxProducts(500)
    setJsRendering(false)
    setIsModalOpen(true)
  }

  const openEditModal = (sched) => {
    setEditingSchedule(sched)
    setFormName(sched.name)
    setFormUrl(sched.url)
    setFormDescription(sched.description || '')
    const foundPreset = PRESET_SCHEDULES.find((p) => p.cron === sched.cron_expression)
    if (foundPreset) {
      setSelectedPreset(foundPreset)
      setCustomCron('')
    } else {
      setSelectedPreset(PRESET_SCHEDULES[5])
      setCustomCron(sched.cron_expression)
    }
    setMaxPages(sched.config?.max_pages || 50)
    setMaxProducts(sched.config?.max_products || 500)
    setJsRendering(sched.config?.javascript_rendering || false)
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setEditingSchedule(null)
  }

  const handleSave = (e) => {
    e.preventDefault()
    if (!formName.trim() || !formUrl.trim()) {
      toast.error('Name and target URL are required')
      return
    }

    const cron = selectedPreset.cron ? selectedPreset.cron : customCron.trim()
    if (!cron) {
      toast.error('Cron expression is required')
      return
    }

    const payload = {
      name: formName.trim(),
      description: formDescription.trim(),
      url: formUrl.trim(),
      cron_expression: cron,
      frequency_label: selectedPreset.cron ? selectedPreset.label : 'Custom Cron',
      config: {
        max_pages: Number(maxPages),
        max_products: Number(maxProducts),
        javascript_rendering: Boolean(jsRendering),
      },
    }

    if (editingSchedule) {
      updateMutation.mutate({ id: editingSchedule.id, payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  const handleToggleActive = (sched) => {
    updateMutation.mutate({
      id: sched.id,
      payload: { is_active: !sched.is_active },
    })
  }

  const handleRunNow = async (sched) => {
    setRunningId(sched.id)
    try {
      const res = await scheduleService.runSchedule(sched.id)
      toast.success(
        <div>
          <p className="font-semibold">Crawl Job Dispatched!</p>
          <p className="text-xs">Job ID: {res.job_id}</p>
        </div>
      )
      refetch()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to trigger scheduled run')
    } finally {
      setRunningId(null)
    }
  }

  // Summary counts
  const totalCount = schedules.length
  const activeCount = schedules.filter((s) => s.is_active).length
  const totalRuns = schedules.reduce((sum, s) => sum + (s.total_runs || 0), 0)
  const uniqueDomains = new Set(schedules.map((s) => s.domain).filter(Boolean)).size

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2.5">
            <ClockIcon className="w-7 h-7 text-primary-600 dark:text-primary-400" />
            Automated Schedules & Cron Monitors
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Schedule recurring automated crawls to track price fluctuations, competitor updates, and catalog changes.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Button variant="secondary" icon={ArrowPathIcon} onClick={() => refetch()}>
            Refresh
          </Button>
          <Button variant="primary" icon={PlusIcon} onClick={openCreateModal}>
            New Schedule
          </Button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-primary-100 text-primary-700 dark:bg-primary-950/60 dark:text-primary-300">
            <ClockIcon className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Total Schedules</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-0.5">{totalCount}</p>
          </div>
        </Card>

        <Card className="flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
            <CheckCircleIcon className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Active Monitors</p>
            <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">{activeCount}</p>
          </div>
        </Card>

        <Card className="flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300">
            <ArrowPathIcon className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Automated Runs</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-0.5">{totalRuns}</p>
          </div>
        </Card>

        <Card className="flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-indigo-100 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300">
            <GlobeAltIcon className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Monitored Domains</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-0.5">{uniqueDomains}</p>
          </div>
        </Card>
      </div>

      {/* Main Schedules List */}
      {isLoading ? (
        <PageLoader message="Loading automated schedules..." />
      ) : schedules.length === 0 ? (
        <EmptyState
          icon={ClockIcon}
          title="No scheduled scraping jobs yet"
          description="Automate recurring scrapes for price tracking, inventory monitoring, or daily catalog syncs."
          action={
            <Button variant="primary" icon={PlusIcon} onClick={openCreateModal}>
              Create First Schedule
            </Button>
          }
        />
      ) : (
        <Card padding="none" className="overflow-hidden border border-gray-200 dark:border-gray-800 shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800 text-left">
              <thead className="bg-gray-50 dark:bg-gray-800/80 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3.5">Schedule Name & Target</th>
                  <th className="px-4 py-3.5">Frequency & Cron</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5">Last Run</th>
                  <th className="px-4 py-3.5">Next Run</th>
                  <th className="px-4 py-3.5">Runs</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800 text-sm">
                {schedules.map((sched) => {
                  const isRunningThis = runningId === sched.id
                  const nextRunDate = sched.next_run_at ? new Date(sched.next_run_at) : null
                  const lastRunDate = sched.last_run_at ? new Date(sched.last_run_at) : null

                  return (
                    <tr
                      key={sched.id}
                      className="hover:bg-gray-50/70 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      {/* Name & Target */}
                      <td className="px-5 py-4">
                        <div className="flex flex-col">
                          <span className="font-semibold text-gray-900 dark:text-white">
                            {sched.name}
                          </span>
                          <a
                            href={sched.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 flex items-center gap-1 mt-0.5 truncate max-w-xs"
                          >
                            <span>{sched.url}</span>
                            <ArrowTopRightOnSquareIcon className="w-3 h-3 flex-shrink-0" />
                          </a>
                          <span className="text-[11px] text-gray-400 mt-0.5">
                            Domain: <span className="font-mono">{sched.domain}</span>
                          </span>
                        </div>
                      </td>

                      {/* Frequency & Cron */}
                      <td className="px-4 py-4">
                        <div className="flex flex-col gap-1">
                          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-800 dark:text-gray-200">
                            <CalendarDaysIcon className="w-4 h-4 text-primary-500" />
                            {sched.frequency_label || 'Recurring'}
                          </span>
                          <span className="text-[11px] font-mono text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded w-max">
                            {sched.cron_expression}
                          </span>
                        </div>
                      </td>

                      {/* Status Toggle */}
                      <td className="px-4 py-4">
                        <button
                          type="button"
                          onClick={() => handleToggleActive(sched)}
                          className={cn(
                            'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold transition-all',
                            sched.is_active
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400 hover:bg-emerald-200'
                              : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200'
                          )}
                          title="Click to toggle active status"
                        >
                          <span
                            className={cn(
                              'w-2 h-2 rounded-full',
                              sched.is_active ? 'bg-emerald-500 animate-pulse' : 'bg-gray-400'
                            )}
                          />
                          {sched.is_active ? 'Active' : 'Paused'}
                        </button>
                      </td>

                      {/* Last Run */}
                      <td className="px-4 py-4 text-xs text-gray-600 dark:text-gray-400">
                        {lastRunDate ? (
                          <div>
                            <p className="font-medium text-gray-900 dark:text-gray-200">
                              {lastRunDate.toLocaleDateString()}
                            </p>
                            <p className="text-[11px] text-gray-400">
                              {lastRunDate.toLocaleTimeString()}
                            </p>
                          </div>
                        ) : (
                          <span className="text-gray-400 italic">Never</span>
                        )}
                      </td>

                      {/* Next Run */}
                      <td className="px-4 py-4 text-xs">
                        {sched.is_active && nextRunDate ? (
                          <div>
                            <p className="font-semibold text-primary-700 dark:text-primary-400">
                              {nextRunDate.toLocaleDateString()}
                            </p>
                            <p className="text-[11px] text-gray-500 dark:text-gray-400">
                              {nextRunDate.toLocaleTimeString()}
                            </p>
                          </div>
                        ) : (
                          <span className="text-gray-400 italic">—</span>
                        )}
                      </td>

                      {/* Runs Count */}
                      <td className="px-4 py-4 text-xs">
                        <span className="font-semibold text-gray-900 dark:text-white">
                          {sched.total_runs || 0}
                        </span>
                        <span className="text-gray-400 text-[11px] ml-1">runs</span>
                      </td>

                      {/* Action buttons */}
                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            size="sm"
                            variant="secondary"
                            icon={PlayIcon}
                            loading={isRunningThis}
                            onClick={() => handleRunNow(sched)}
                            title="Trigger Immediate Scrape"
                          >
                            Run Now
                          </Button>
                          <button
                            type="button"
                            onClick={() => openEditModal(sched)}
                            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                            title="Edit Schedule"
                          >
                            <PencilSquareIcon className="w-4 h-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              if (window.confirm(`Delete scheduled monitor "${sched.name}"?`)) {
                                deleteMutation.mutate(sched.id)
                              }
                            }}
                            className="p-1.5 rounded-lg text-rose-500 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
                            title="Delete Schedule"
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
        </Card>
      )}

      {/* Create / Edit Schedule Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={closeModal}
        title={editingSchedule ? 'Edit Automated Schedule' : 'Create Automated Crawl Schedule'}
        size="lg"
      >
        <form onSubmit={handleSave} className="space-y-4">
          {/* Schedule Name */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">
              Schedule Name *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Daily Amazon Electronics Price Tracker"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="w-full px-3.5 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Target URL */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">
              Target Website / Catalog URL *
            </label>
            <input
              type="url"
              required
              placeholder="https://example.com/shop or https://www.amazon.com/..."
              value={formUrl}
              onChange={(e) => setFormUrl(e.target.value)}
              className="w-full px-3.5 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">
              Description (Optional)
            </label>
            <input
              type="text"
              placeholder="Optional notes or monitoring tags"
              value={formDescription}
              onChange={(e) => setFormDescription(e.target.value)}
              className="w-full px-3.5 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            />
          </div>

          {/* Frequency Presets */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1.5">
              Frequency Schedule *
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {PRESET_SCHEDULES.map((preset, idx) => {
                const isSelected = selectedPreset.label === preset.label
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setSelectedPreset(preset)}
                    className={cn(
                      'p-2.5 rounded-lg text-left text-xs border transition-all',
                      isSelected
                        ? 'border-primary-600 bg-primary-50/80 dark:bg-primary-950/40 text-primary-900 dark:text-primary-200 font-semibold shadow-sm ring-1 ring-primary-500'
                        : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50'
                    )}
                  >
                    <p className="font-medium">{preset.label}</p>
                    <p className="text-[10px] text-gray-400 mt-0.5 truncate">{preset.cron || 'Custom'}</p>
                  </button>
                )
              })}
            </div>

            {/* Custom Cron Input */}
            {!selectedPreset.cron && (
              <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-800/80 rounded-lg border border-gray-200 dark:border-gray-700">
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Custom 5-Field Cron Expression
                </label>
                <input
                  type="text"
                  required
                  placeholder="0 9 * * * (min hour day month weekday)"
                  value={customCron}
                  onChange={(e) => setCustomCron(e.target.value)}
                  className="w-full px-3 py-1.5 text-sm font-mono rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
                <p className="text-[11px] text-gray-400 mt-1">
                  Example: <code className="text-primary-600">0 8 * * 1-5</code> runs Mon-Fri at 8:00 AM UTC.
                </p>
              </div>
            )}
          </div>

          {/* Crawl Settings */}
          <div className="grid grid-cols-2 gap-4 pt-2 border-t border-gray-200 dark:border-gray-700">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">
                Max Pages per Run
              </label>
              <input
                type="number"
                min="1"
                max="500"
                value={maxPages}
                onChange={(e) => setMaxPages(e.target.value)}
                className="w-full px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">
                Max Products
              </label>
              <input
                type="number"
                min="1"
                max="5000"
                value={maxProducts}
                onChange={(e) => setMaxProducts(e.target.value)}
                className="w-full px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>
          </div>

          {/* JS Rendering */}
          <div className="flex items-center gap-2.5 pt-1">
            <input
              type="checkbox"
              id="jsRenderingCheckbox"
              checked={jsRendering}
              onChange={(e) => setJsRendering(e.target.checked)}
              className="w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
            />
            <label htmlFor="jsRenderingCheckbox" className="text-xs text-gray-700 dark:text-gray-300 font-medium cursor-pointer">
              Enable Playwright Browser Engine (recommended for Amazon, eBay, Wix, SPAs)
            </label>
          </div>

          <ModalFooter>
            <Button variant="secondary" type="button" onClick={closeModal}>
              Cancel
            </Button>
            <Button
              variant="primary"
              type="submit"
              loading={createMutation.isPending || updateMutation.isPending}
            >
              {editingSchedule ? 'Save Changes' : 'Create Schedule'}
            </Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  )
}
