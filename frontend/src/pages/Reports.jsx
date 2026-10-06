import React, { useState, useEffect } from 'react'
import {
  DocumentChartBarIcon,
  DocumentArrowDownIcon,
  EnvelopeIcon,
  PlayIcon,
  PlusIcon,
  TrashIcon,
  ClockIcon,
  ArrowPathIcon,
  EyeIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  PaperAirplaneIcon,
  CalendarDaysIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import reportService from '@/services/reportService'
import Card from '@/components/Common/Card'
import Button from '@/components/Common/Button'
import Badge from '@/components/Common/Badge'
import Modal from '@/components/Common/Modal'
import EmptyState from '@/components/Common/EmptyState'
import Spinner from '@/components/Common/Spinner'

export default function Reports() {
  const [loading, setLoading] = useState(true)
  const [schedules, setSchedules] = useState([])

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [showTestModal, setShowTestModal] = useState(false)
  
  const [previewHtml, setPreviewHtml] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewDomain, setPreviewDomain] = useState('')
  const [previewDays, setPreviewDays] = useState(7)

  // Creation form states
  const [name, setName] = useState('')
  const [recipientEmails, setRecipientEmails] = useState('')
  const [frequency, setFrequency] = useState('weekly')
  const [format, setFormat] = useState('both')
  const [domainFilter, setDomainFilter] = useState('')
  const [creating, setCreating] = useState(false)

  // Test email state
  const [testEmail, setTestEmail] = useState('')
  const [sendingTest, setSendingTest] = useState(false)
  const [triggeringId, setTriggeringId] = useState(null)

  const fetchSchedules = async () => {
    try {
      setLoading(true)
      const data = await reportService.getSchedules()
      setSchedules(data || [])
    } catch (err) {
      toast.error('Failed to load report schedules')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSchedules()
  }, [])

  const handleDownloadPdf = (domain = '') => {
    toast.success('Generating and downloading PDF report...')
    const url = reportService.getDownloadPdfUrl(domain || undefined, 7)
    window.open(url, '_blank')
  }

  const handleOpenPreview = async () => {
    setShowPreviewModal(true)
    setPreviewLoading(true)
    try {
      const url = reportService.getPreviewHtmlUrl(previewDomain || undefined, previewDays)
      const res = await fetch(url)
      const html = await res.text()
      setPreviewHtml(html)
    } catch (err) {
      toast.error('Failed to load report preview')
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleTriggerNow = async (schedId) => {
    try {
      setTriggeringId(schedId)
      toast.loading('Compiling digest and sending email...', { id: 'trigger-report' })
      const res = await reportService.triggerScheduleReport(schedId)
      toast.dismiss('trigger-report')
      toast.success(`Report dispatched! Recipients: ${res.recipients.join(', ')}`)
      fetchSchedules()
    } catch (err) {
      toast.dismiss('trigger-report')
      toast.error('Failed to dispatch scheduled report')
    } finally {
      setTriggeringId(null)
    }
  }

  const handleDelete = async (schedId) => {
    if (!window.confirm('Delete this report schedule?')) return
    try {
      await reportService.deleteSchedule(schedId)
      toast.success('Schedule deleted')
      fetchSchedules()
    } catch (err) {
      toast.error('Failed to delete schedule')
    }
  }

  const handleCreateSubmit = async (e) => {
    e.preventDefault()
    const emails = recipientEmails
      .split(/[\n,]/)
      .map((e) => e.trim())
      .filter(Boolean)

    if (emails.length === 0) {
      toast.error('Please enter at least one recipient email')
      return
    }

    let cron = '0 9 * * 1'
    let label = 'Every Monday at 09:00 AM'
    if (frequency === 'daily') {
      cron = '0 9 * * *'
      label = 'Daily at 09:00 AM'
    } else if (frequency === 'monthly') {
      cron = '0 9 1 * *'
      label = 'Monthly on 1st at 09:00 AM'
    }

    try {
      setCreating(true)
      await reportService.createSchedule({
        name,
        recipient_emails: emails,
        frequency,
        cron_expression: cron,
        frequency_label: label,
        format,
        domain_filter: domainFilter.trim() || undefined,
      })
      toast.success('Competitor digest schedule created!')
      setShowCreateModal(false)
      setName('')
      setRecipientEmails('')
      setDomainFilter('')
      fetchSchedules()
    } catch (err) {
      toast.error('Failed to create report schedule')
    } finally {
      setCreating(false)
    }
  }

  const handleSendTestSubmit = async (e) => {
    e.preventDefault()
    if (!testEmail.trim()) {
      toast.error('Please provide an email address')
      return
    }
    try {
      setSendingTest(true)
      const res = await reportService.sendTestReport({
        recipient_email: testEmail.trim(),
        domain_filter: domainFilter || undefined,
        format: 'both',
      })
      toast.success(res.message || 'Test report dispatched!')
      setShowTestModal(false)
      setTestEmail('')
    } catch (err) {
      toast.error('Failed to send test report')
    } finally {
      setSendingTest(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <DocumentChartBarIcon className="w-8 h-8 text-primary-600 dark:text-primary-400" />
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Competitor Intelligence Reports
            </h1>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Automated periodic executive briefings compiling price drops, catalog changes, stockouts, and sentiment flaws.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleDownloadPdf()}
          >
            <DocumentArrowDownIcon className="w-4 h-4 mr-1.5 text-primary-600" />
            Download PDF Digest
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleOpenPreview}
          >
            <EyeIcon className="w-4 h-4 mr-1.5 text-indigo-600" />
            Preview HTML Digest
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowTestModal(true)}
          >
            <PaperAirplaneIcon className="w-4 h-4 mr-1.5 text-emerald-600" />
            Send Test Email
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowCreateModal(true)}
          >
            <PlusIcon className="w-4 h-4 mr-1.5" />
            Schedule New Digest
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 border-l-4 border-l-primary-500">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Active Schedules</div>
          <div className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
            {schedules.filter((s) => s.is_active).length}
          </div>
          <div className="text-xs text-gray-400 mt-0.5">Recurring pipelines</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-500">
          <div className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">Digests Dispatched</div>
          <div className="mt-2 text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {schedules.reduce((acc, s) => acc + (s.total_sent || 0), 0)}
          </div>
          <div className="text-xs text-gray-400 mt-0.5">Lifetime delivered</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-indigo-500">
          <div className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">Supported Formats</div>
          <div className="mt-2 text-2xl font-bold text-indigo-600 dark:text-indigo-400">PDF & HTML</div>
          <div className="text-xs text-gray-400 mt-0.5">ReportLab & Email MIME</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-amber-500">
          <div className="text-xs font-semibold text-amber-600 uppercase tracking-wider">Next Scheduled Delivery</div>
          <div className="mt-2 text-lg font-bold text-amber-600 dark:text-amber-400 truncate">
            {schedules.length > 0 && schedules[0].next_run_at
              ? new Date(schedules[0].next_run_at).toLocaleDateString()
              : 'None pending'}
          </div>
          <div className="text-xs text-gray-400 mt-0.5">Automated queue</div>
        </Card>
      </div>

      {/* Schedules Table */}
      <Card className="overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <CalendarDaysIcon className="w-5 h-5 text-primary-500" />
            Scheduled Competitor Digest Pipelines
          </h2>
          <Button variant="outline" size="sm" onClick={fetchSchedules} disabled={loading}>
            <ArrowPathIcon className={`w-4 h-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center">
            <Spinner size="lg" />
            <p className="text-sm text-gray-500 mt-3">Loading report schedules...</p>
          </div>
        ) : schedules.length === 0 ? (
          <EmptyState
            icon={DocumentChartBarIcon}
            title="No Report Schedules Configured"
            description="Create an automated schedule to receive executive competitor intelligence briefs via email or PDF."
            action={
              <Button size="sm" variant="primary" onClick={() => setShowCreateModal(true)}>
                <PlusIcon className="w-4 h-4 mr-1.5" />
                Schedule New Digest
              </Button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/80 border-b border-gray-200 dark:border-gray-700 text-gray-500 uppercase tracking-wider">
                  <th className="py-3 px-4 font-semibold">Report Title</th>
                  <th className="py-3 px-3 font-semibold">Frequency</th>
                  <th className="py-3 px-3 font-semibold">Format</th>
                  <th className="py-3 px-3 font-semibold">Recipients</th>
                  <th className="py-3 px-3 font-semibold">Scope</th>
                  <th className="py-3 px-3 font-semibold">Last Status</th>
                  <th className="py-3 px-3 font-semibold">Next Delivery</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {schedules.map((sched) => {
                  const isTriggering = triggeringId === sched.id

                  return (
                    <tr key={sched.id} className="hover:bg-gray-50/70 dark:hover:bg-gray-800/40 transition-colors">
                      <td className="py-3 px-4 font-medium text-gray-900 dark:text-gray-100">
                        {sched.name}
                      </td>

                      <td className="py-3 px-3">
                        <span className="inline-flex items-center gap-1 font-medium text-gray-700 dark:text-gray-300">
                          <ClockIcon className="w-3.5 h-3.5 text-gray-400" />
                          {sched.frequency_label || sched.frequency}
                        </span>
                      </td>

                      <td className="py-3 px-3 uppercase font-semibold text-gray-600 dark:text-gray-300">
                        {sched.format}
                      </td>

                      <td className="py-3 px-3 text-gray-600 dark:text-gray-300">
                        <div className="max-w-xs truncate" title={sched.recipient_emails?.join(', ')}>
                          {sched.recipient_emails?.join(', ') || 'No emails'}
                        </div>
                      </td>

                      <td className="py-3 px-3 capitalize">
                        {sched.domain_filter || 'All Competitors'}
                      </td>

                      <td className="py-3 px-3">
                        {sched.last_status === 'success' ? (
                          <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                            <CheckCircleIcon className="w-3.5 h-3.5" />
                            Sent ({sched.total_sent})
                          </span>
                        ) : sched.last_status === 'failed' ? (
                          <span className="inline-flex items-center gap-1 text-rose-600 font-medium" title={sched.last_error}>
                            <ExclamationCircleIcon className="w-3.5 h-3.5" />
                            Failed
                          </span>
                        ) : (
                          <span className="text-gray-400">Pending</span>
                        )}
                      </td>

                      <td className="py-3 px-3 text-gray-500">
                        {sched.next_run_at
                          ? new Date(sched.next_run_at).toLocaleString()
                          : 'Not scheduled'}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleTriggerNow(sched.id)}
                            disabled={isTriggering}
                            className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 transition-colors"
                            title="Run and dispatch now"
                          >
                            <PlayIcon className={`w-4 h-4 ${isTriggering ? 'animate-spin text-primary-500' : ''}`} />
                          </button>

                          <button
                            onClick={() => handleDownloadPdf(sched.domain_filter)}
                            className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-primary-600 transition-colors"
                            title="Download PDF"
                          >
                            <DocumentArrowDownIcon className="w-4 h-4" />
                          </button>

                          <button
                            onClick={() => handleDelete(sched.id)}
                            className="p-1 rounded text-gray-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
                            title="Delete schedule"
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

      {/* Schedule Builder Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create Automated Competitor Intelligence Schedule"
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Report Title:
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Weekly Executive Market Briefing"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full text-xs p-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Recipient Email Addresses (one per line or comma-separated):
            </label>
            <textarea
              rows={3}
              required
              placeholder="exec@store.com&#10;analyst@store.com"
              value={recipientEmails}
              onChange={(e) => setRecipientEmails(e.target.value)}
              className="w-full text-xs font-mono p-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Frequency:
              </label>
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value)}
                className="w-full text-xs p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              >
                <option value="daily">Daily at 09:00 AM</option>
                <option value="weekly">Weekly (Every Monday at 09:00 AM)</option>
                <option value="monthly">Monthly (1st of Month at 09:00 AM)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Delivery Format:
              </label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value)}
                className="w-full text-xs p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              >
                <option value="both">Both (HTML Email + PDF Attachment)</option>
                <option value="pdf">PDF Attachment Only</option>
                <option value="email_html">HTML Email Only</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Target Competitor Domain Filter (Optional):
            </label>
            <input
              type="text"
              placeholder="e.g. amazon.com (Leave blank for all competitors)"
              value={domainFilter}
              onChange={(e) => setDomainFilter(e.target.value)}
              className="w-full text-xs p-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
            <Button type="button" variant="outline" size="sm" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" disabled={creating}>
              {creating ? 'Creating Schedule...' : 'Create Schedule'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* HTML Digest Preview Modal */}
      <Modal
        isOpen={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        title="Executive HTML Email Digest Preview"
        size="xl"
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3 pb-2 border-b border-gray-200 dark:border-gray-700">
            <span className="text-xs text-gray-500">Live rendering of the responsive email digest template:</span>
            <Button size="sm" variant="outline" onClick={() => handleDownloadPdf(previewDomain)}>
              <DocumentArrowDownIcon className="w-4 h-4 mr-1 text-primary-600" />
              Download as PDF
            </Button>
          </div>

          {previewLoading ? (
            <div className="py-20 flex flex-col items-center justify-center">
              <Spinner size="lg" />
              <p className="text-xs text-gray-500 mt-2">Compiling intelligence preview...</p>
            </div>
          ) : (
            <div className="border border-gray-300 dark:border-gray-700 rounded-lg overflow-hidden max-h-[650px] overflow-y-auto bg-gray-100 p-4">
              <iframe
                title="Digest Preview"
                srcDoc={previewHtml}
                className="w-full h-[600px] bg-white rounded shadow-sm border-0"
              />
            </div>
          )}

          <div className="flex justify-end pt-2 border-t border-gray-200 dark:border-gray-700">
            <Button variant="outline" size="sm" onClick={() => setShowPreviewModal(false)}>
              Close Preview
            </Button>
          </div>
        </div>
      </Modal>

      {/* Send Test Email Modal */}
      <Modal
        isOpen={showTestModal}
        onClose={() => setShowTestModal(false)}
        title="Send Instant Test Digest"
      >
        <form onSubmit={handleSendTestSubmit} className="space-y-4">
          <p className="text-xs text-gray-500">
            Generate and dispatch an instant test digest with PDF attachment to your inbox.
          </p>

          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Your Email Address:
            </label>
            <input
              type="email"
              required
              placeholder="you@company.com"
              value={testEmail}
              onChange={(e) => setTestEmail(e.target.value)}
              className="w-full text-xs p-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
            <Button type="button" variant="outline" size="sm" onClick={() => setShowTestModal(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" disabled={sendingTest}>
              {sendingTest ? 'Sending...' : 'Send Test Digest'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
