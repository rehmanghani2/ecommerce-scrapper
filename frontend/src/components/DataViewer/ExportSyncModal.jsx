import React, { useState, useEffect } from 'react'
import {
  ArrowDownTrayIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  CloudArrowUpIcon,
  DocumentArrowDownIcon,
  TableCellsIcon,
  ArrowTopRightOnSquareIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import { Modal, Button, Input, Select, Alert, Badge, Spinner } from '@/components/Common'
import integrationService from '@/services/integrationService'
import exportService from '@/services/exportService'
import toast from 'react-hot-toast'

export function ExportSyncModal({
  isOpen,
  onClose,
  productIds = [],
  jobId = null,
  totalProductsCount = 0,
}) {
  const [activeTab, setActiveTab] = useState('shopify')
  const [configs, setConfigs] = useState([])
  const [loadingConfigs, setLoadingConfigs] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [syncResult, setSyncResult] = useState(null)

  // One-off credentials override state if not configured
  const [shopifyCreds, setShopifyCreds] = useState({ shop_url: '', access_token: '' })
  const [wcCreds, setWcCreds] = useState({ store_url: '', consumer_key: '', consumer_secret: '' })
  const [sheetsCreds, setSheetsCreds] = useState({ webhook_url: '' })
  const [publishStatus, setPublishStatus] = useState('draft')

  const effectiveCount = productIds.length > 0 ? productIds.length : (totalProductsCount || 'all')

  useEffect(() => {
    if (isOpen) {
      loadConfigs()
      setSyncResult(null)
    }
  }, [isOpen])

  const loadConfigs = async () => {
    try {
      setLoadingConfigs(true)
      const data = await integrationService.getConfigs()
      setConfigs(data || [])
    } catch (err) {
      console.error('Failed to load integration configs:', err)
    } finally {
      setLoadingConfigs(false)
    }
  }

  const getConfigForPlatform = (platform) => {
    return configs.find((c) => c.platform === platform && c.is_active)
  }

  // 1-Click Sync Handler
  const handleSync = async (platform) => {
    try {
      setSyncing(true)
      setSyncResult(null)

      let override = null
      if (platform === 'shopify' && (!getConfigForPlatform('shopify') || shopifyCreds.shop_url)) {
        if (shopifyCreds.shop_url && shopifyCreds.access_token) {
          override = shopifyCreds
        }
      } else if (platform === 'woocommerce' && (!getConfigForPlatform('woocommerce') || wcCreds.store_url)) {
        if (wcCreds.store_url && wcCreds.consumer_key && wcCreds.consumer_secret) {
          override = wcCreds
        }
      } else if (platform === 'google_sheets' && (!getConfigForPlatform('google_sheets') || sheetsCreds.webhook_url)) {
        if (sheetsCreds.webhook_url) {
          override = sheetsCreds
        }
      }

      const res = await integrationService.syncProducts({
        platform,
        productIds: productIds.length > 0 ? productIds : null,
        jobId: productIds.length === 0 ? jobId : null,
        publishStatus,
        configOverride: override,
      })

      setSyncResult(res)
      if (res.synced > 0) {
        toast.success(`Successfully pushed ${res.synced} products to ${platform}!`)
      } else {
        toast.error(`Sync finished with failures. Check results below.`)
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Sync failed'
      toast.error(msg)
      setSyncResult({
        success: false,
        platform,
        synced: 0,
        failed: productIds.length || 1,
        message: msg,
        items: [],
      })
    } finally {
      setSyncing(false)
    }
  }

  // Download Store CSV Template
  const handleDownloadCsv = async (platform) => {
    try {
      setDownloading(true)
      await integrationService.downloadStoreCsv(platform, {
        jobId: productIds.length === 0 ? jobId : null,
        productIds: productIds.length > 0 ? productIds : null,
      })
      toast.success(`${platform.toUpperCase()} CSV downloaded!`)
    } catch (err) {
      toast.error('Failed to download CSV: ' + err.message)
    } finally {
      setDownloading(false)
    }
  }

  // Download standard file export
  const handleStandardExport = async (format) => {
    try {
      setDownloading(true)
      if (jobId) {
        const data = await exportService.createExport(jobId, format)
        if (data.file_path) {
          const filename = data.file_path.split(/[/\\]/).pop()
          await exportService.downloadExport(filename)
        }
      } else {
        await integrationService.downloadStoreCsv('google_sheets', { productIds })
      }
      toast.success(`Export created and downloaded!`)
    } catch (err) {
      toast.error('Export failed: ' + err.message)
    } finally {
      setDownloading(false)
    }
  }

  const shopifyConfig = getConfigForPlatform('shopify')
  const wcConfig = getConfigForPlatform('woocommerce')
  const sheetsConfig = getConfigForPlatform('google_sheets')

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="1-Click Export & Store Sync"
      size="xl"
    >
      <div className="space-y-6">
        {/* Top Info Bar */}
        <div className="flex items-center justify-between bg-primary-50 dark:bg-primary-950/40 border border-primary-200 dark:border-primary-800 rounded-lg p-3">
          <div>
            <p className="text-sm font-semibold text-primary-900 dark:text-primary-200">
              Target Selection: <span className="underline">{effectiveCount} Products</span>
            </p>
            <p className="text-xs text-primary-700 dark:text-primary-300">
              Push directly to your online store catalog via live API or download store-ready templates.
            </p>
          </div>
          <Badge variant="primary">
            {productIds.length > 0 ? `${productIds.length} Selected` : 'Job Dataset'}
          </Badge>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-gray-200 dark:border-gray-700 space-x-2">
          {[
            { id: 'shopify', label: 'Shopify' },
            { id: 'woocommerce', label: 'WooCommerce' },
            { id: 'google_sheets', label: 'Google Sheets' },
            { id: 'files', label: 'Standard Files' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id)
                setSyncResult(null)
              }}
              className={`pb-2.5 px-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600 dark:text-primary-400 font-semibold'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab 1: Shopify */}
        {activeTab === 'shopify' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-gray-900 dark:text-white">Shopify Sync & Import</h4>
                <p className="text-xs text-gray-500">Add products to your Shopify store with images, variants, and pricing.</p>
              </div>
              {shopifyConfig ? (
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-green-700 bg-green-100 px-2.5 py-1 rounded-full dark:bg-green-950/60 dark:text-green-300">
                  <CheckCircleIcon className="w-3.5 h-3.5" /> Connected: {shopifyConfig.name}
                </span>
              ) : (
                <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  No default saved config
                </span>
              )}
            </div>

            {!shopifyConfig && (
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg space-y-2 border border-gray-200 dark:border-gray-700">
                <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  Quick Shopify API Credentials (or configure once in Settings):
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <Input
                    placeholder="my-store.myshopify.com"
                    value={shopifyCreds.shop_url}
                    onChange={(e) => setShopifyCreds({ ...shopifyCreds, shop_url: e.target.value })}
                  />
                  <Input
                    placeholder="Admin API Token (shpat_...)"
                    type="password"
                    value={shopifyCreds.access_token}
                    onChange={(e) => setShopifyCreds({ ...shopifyCreds, access_token: e.target.value })}
                  />
                </div>
              </div>
            )}

            <div className="flex items-center gap-4">
              <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Publish as:</label>
              <div className="flex items-center gap-3">
                <label className="inline-flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                  <input
                    type="radio"
                    name="pubStatusShopify"
                    value="draft"
                    checked={publishStatus === 'draft'}
                    onChange={() => setPublishStatus('draft')}
                  />
                  Draft (Recommended)
                </label>
                <label className="inline-flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                  <input
                    type="radio"
                    name="pubStatusShopify"
                    value="active"
                    checked={publishStatus === 'active'}
                    onChange={() => setPublishStatus('active')}
                  />
                  Active (Immediately Live)
                </label>
              </div>
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              <Button
                variant="primary"
                icon={CloudArrowUpIcon}
                disabled={syncing || (!shopifyConfig && (!shopifyCreds.shop_url || !shopifyCreds.access_token))}
                onClick={() => handleSync('shopify')}
              >
                {syncing ? 'Pushing to Shopify...' : `1-Click Push to Shopify`}
              </Button>

              <Button
                variant="secondary"
                icon={DocumentArrowDownIcon}
                disabled={downloading}
                onClick={() => handleDownloadCsv('shopify')}
              >
                Download Shopify-Ready CSV
              </Button>
            </div>
          </div>
        )}

        {/* Tab 2: WooCommerce */}
        {activeTab === 'woocommerce' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-gray-900 dark:text-white">WooCommerce Sync & Import</h4>
                <p className="text-xs text-gray-500">Publish simple products with categories, regular & sale prices directly into WooCommerce.</p>
              </div>
              {wcConfig ? (
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-green-700 bg-green-100 px-2.5 py-1 rounded-full dark:bg-green-950/60 dark:text-green-300">
                  <CheckCircleIcon className="w-3.5 h-3.5" /> Connected: {wcConfig.name}
                </span>
              ) : (
                <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  No default saved config
                </span>
              )}
            </div>

            {!wcConfig && (
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg space-y-2 border border-gray-200 dark:border-gray-700">
                <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  Quick WooCommerce REST API Credentials:
                </p>
                <Input
                  placeholder="https://example.com"
                  value={wcCreds.store_url}
                  onChange={(e) => setWcCreds({ ...wcCreds, store_url: e.target.value })}
                />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <Input
                    placeholder="Consumer Key (ck_...)"
                    value={wcCreds.consumer_key}
                    onChange={(e) => setWcCreds({ ...wcCreds, consumer_key: e.target.value })}
                  />
                  <Input
                    placeholder="Consumer Secret (cs_...)"
                    type="password"
                    value={wcCreds.consumer_secret}
                    onChange={(e) => setWcCreds({ ...wcCreds, consumer_secret: e.target.value })}
                  />
                </div>
              </div>
            )}

            <div className="flex items-center gap-4">
              <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Publish as:</label>
              <div className="flex items-center gap-3">
                <label className="inline-flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                  <input
                    type="radio"
                    name="pubStatusWC"
                    value="publish"
                    checked={publishStatus === 'publish' || publishStatus === 'active'}
                    onChange={() => setPublishStatus('publish')}
                  />
                  Published
                </label>
                <label className="inline-flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                  <input
                    type="radio"
                    name="pubStatusWC"
                    value="draft"
                    checked={publishStatus === 'draft'}
                    onChange={() => setPublishStatus('draft')}
                  />
                  Draft
                </label>
              </div>
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              <Button
                variant="primary"
                icon={CloudArrowUpIcon}
                disabled={syncing || (!wcConfig && (!wcCreds.store_url || !wcCreds.consumer_key || !wcCreds.consumer_secret))}
                onClick={() => handleSync('woocommerce')}
              >
                {syncing ? 'Pushing to WooCommerce...' : `1-Click Push to WooCommerce`}
              </Button>

              <Button
                variant="secondary"
                icon={DocumentArrowDownIcon}
                disabled={downloading}
                onClick={() => handleDownloadCsv('woocommerce')}
              >
                Download WooCommerce CSV
              </Button>
            </div>
          </div>
        )}

        {/* Tab 3: Google Sheets */}
        {activeTab === 'google_sheets' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-gray-900 dark:text-white">Google Sheets Sync</h4>
                <p className="text-xs text-gray-500">Send live rows into Google Sheets via Webhook / Apps Script or export formatted sheet data.</p>
              </div>
              {sheetsConfig ? (
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-green-700 bg-green-100 px-2.5 py-1 rounded-full dark:bg-green-950/60 dark:text-green-300">
                  <CheckCircleIcon className="w-3.5 h-3.5" /> Webhook Connected
                </span>
              ) : null}
            </div>

            {!sheetsConfig && (
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg space-y-2 border border-gray-200 dark:border-gray-700">
                <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  Google Apps Script / Webhook Endpoint URL:
                </p>
                <Input
                  placeholder="https://script.google.com/macros/s/.../exec"
                  value={sheetsCreds.webhook_url}
                  onChange={(e) => setSheetsCreds({ webhook_url: e.target.value })}
                />
              </div>
            )}

            <div className="flex flex-wrap gap-3 pt-2">
              <Button
                variant="primary"
                icon={CloudArrowUpIcon}
                disabled={syncing || (!sheetsConfig && !sheetsCreds.webhook_url)}
                onClick={() => handleSync('google_sheets')}
              >
                {syncing ? 'Syncing to Sheets...' : `Push to Google Sheets`}
              </Button>

              <Button
                variant="secondary"
                icon={DocumentArrowDownIcon}
                disabled={downloading}
                onClick={() => handleDownloadCsv('google_sheets')}
              >
                Download Clean Sheets CSV
              </Button>
            </div>
          </div>
        )}

        {/* Tab 4: Standard Files */}
        {activeTab === 'files' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-gray-900 dark:text-white">Standard Data Export</h4>
              <p className="text-xs text-gray-500">Download extracted product data in popular formats.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => handleStandardExport('csv')}
                className="flex flex-col items-center justify-center p-4 rounded-lg border-2 border-gray-200 hover:border-primary-500 dark:border-gray-700 dark:hover:border-primary-500 bg-white dark:bg-gray-800 transition-all text-center"
              >
                <DocumentArrowDownIcon className="w-8 h-8 text-green-600 mb-2" />
                <span className="font-semibold text-sm text-gray-900 dark:text-white">CSV</span>
                <span className="text-xs text-gray-500">Universal spreadsheet</span>
              </button>

              <button
                type="button"
                onClick={() => handleStandardExport('excel')}
                className="flex flex-col items-center justify-center p-4 rounded-lg border-2 border-gray-200 hover:border-primary-500 dark:border-gray-700 dark:hover:border-primary-500 bg-white dark:bg-gray-800 transition-all text-center"
              >
                <TableCellsIcon className="w-8 h-8 text-blue-600 mb-2" />
                <span className="font-semibold text-sm text-gray-900 dark:text-white">Excel (XLSX)</span>
                <span className="text-xs text-gray-500">Formatted workbook</span>
              </button>

              <button
                type="button"
                onClick={() => handleStandardExport('json')}
                className="flex flex-col items-center justify-center p-4 rounded-lg border-2 border-gray-200 hover:border-primary-500 dark:border-gray-700 dark:hover:border-primary-500 bg-white dark:bg-gray-800 transition-all text-center"
              >
                <ArrowDownTrayIcon className="w-8 h-8 text-yellow-600 mb-2" />
                <span className="font-semibold text-sm text-gray-900 dark:text-white">JSON</span>
                <span className="text-xs text-gray-500">Raw developer format</span>
              </button>
            </div>
          </div>
        )}

        {/* Sync Results Box */}
        {syncResult && (
          <div className="mt-4 border border-gray-200 dark:border-gray-700 rounded-lg p-3 bg-gray-50 dark:bg-gray-900/50 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
                Sync Execution Report:
              </span>
              <div className="flex items-center gap-2">
                <Badge variant="success">✓ {syncResult.synced} Synced</Badge>
                {syncResult.failed > 0 && <Badge variant="danger">✗ {syncResult.failed} Failed</Badge>}
              </div>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400">{syncResult.message}</p>

            {/* Item level status table if available */}
            {syncResult.items && syncResult.items.length > 0 && (
              <div className="max-h-48 overflow-y-auto divide-y divide-gray-200 dark:divide-gray-800 text-xs">
                {syncResult.items.map((item, idx) => (
                  <div key={idx} className="py-1.5 flex items-center justify-between">
                    <span className="truncate max-w-[280px] font-medium text-gray-800 dark:text-gray-200">
                      {item.name || `Product #${item.product_id}`}
                    </span>
                    <div className="flex items-center gap-2">
                      {item.status === 'success' ? (
                        <>
                          <span className="text-green-600 font-semibold">Synced</span>
                          {item.external_url && (
                            <a
                              href={item.external_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-primary-600 hover:underline flex items-center gap-0.5"
                            >
                              View <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                            </a>
                          )}
                        </>
                      ) : (
                        <span className="text-red-500 truncate max-w-[200px]" title={item.error}>
                          {item.error || 'Failed'}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t border-gray-200 dark:border-gray-700">
          <a
            href="/settings"
            className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
          >
            Manage Permanent API Keys & Integrations in Settings →
          </a>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default ExportSyncModal
