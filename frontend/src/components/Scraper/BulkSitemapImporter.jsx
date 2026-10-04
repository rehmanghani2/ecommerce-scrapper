import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import {
  DocumentArrowUpIcon,
  GlobeAltIcon,
  PlayIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  TrashIcon,
  ListBulletIcon,
  SparklesIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline'
import {
  Card,
  CardHeader,
  CardTitle,
  Button,
  Input,
  Select,
  Badge,
  Alert,
} from '@/components/Common'
import scraperService from '@/services/scraperService'
import toast from 'react-hot-toast'

export function BulkSitemapImporter() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)

  // Sub-tabs: 'sitemap' | 'file' | 'manual'
  const [activeMode, setActiveMode] = useState('sitemap')

  // Sitemap state
  const [sitemapUrl, setSitemapUrl] = useState('')
  const [filterProductsOnly, setFilterProductsOnly] = useState(true)

  // File state
  const [selectedFile, setSelectedFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)

  // Manual list state
  const [rawUrlText, setRawUrlText] = useState('')

  // Discovered URLs table
  const [discoveredUrls, setDiscoveredUrls] = useState([])
  const [previewItems, setPreviewItems] = useState([])
  const [jobName, setJobName] = useState('')
  const [concurrency, setConcurrency] = useState(10)
  const [requestDelay, setRequestDelay] = useState(0.5)

  // 1. Parse Sitemap Mutation
  const sitemapMutation = useMutation({
    mutationFn: () => scraperService.parseSitemap(sitemapUrl, filterProductsOnly),
    onSuccess: (data) => {
      if (data.urls && data.urls.length > 0) {
        setDiscoveredUrls(data.urls)
        setPreviewItems(data.sample_entries || [])
        setJobName(`Sitemap: ${new URL(sitemapUrl).hostname} (${data.urls.length} URLs)`)
        toast.success(`Discovered ${data.urls.length.toLocaleString()} URLs across ${data.sitemaps_inspected} sitemaps!`)
      } else {
        toast.error('No URLs found in this sitemap. Try unchecking "Filter to product URLs only".')
      }
    },
    onError: (err) => {
      toast.error(err.message || 'Failed to fetch or parse sitemap XML.')
    },
  })

  // 2. Parse CSV/File Mutation
  const fileMutation = useMutation({
    mutationFn: ({ content, name }) => scraperService.parseBulkFile(content, name),
    onSuccess: (data) => {
      if (data.urls && data.urls.length > 0) {
        setDiscoveredUrls(data.urls)
        setPreviewItems(data.items || [])
        setJobName(`Bulk Import: ${selectedFile?.name || 'File'} (${data.urls.length} URLs)`)
        toast.success(`Parsed ${data.urls.length.toLocaleString()} valid URLs from ${data.total_rows || data.total_found} rows!`)
      } else {
        toast.error('Could not find any valid HTTP/HTTPS URLs in the uploaded file.')
      }
    },
    onError: (err) => {
      toast.error(err.message || 'Failed to parse file content.')
    },
  })

  // 3. Start Bulk Scraping Mutation
  const startBulkMutation = useMutation({
    mutationFn: () =>
      scraperService.startBulkScraping({
        urls: discoveredUrls,
        name: jobName,
        concurrency: Number(concurrency),
        requestDelay: Number(requestDelay),
      }),
    onSuccess: (data) => {
      toast.success(data.message || 'Parallel bulk scraping started!')
      navigate('/jobs')
    },
    onError: (err) => {
      toast.error(err.message || 'Failed to start bulk scrape job.')
    },
  })

  // File Upload Handlers
  const handleFileChosen = (file) => {
    if (!file) return
    setSelectedFile(file)
    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target.result
      fileMutation.mutate({ content, name: file.name })
    }
    reader.readAsText(file)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChosen(e.dataTransfer.files[0])
    }
  }

  // Parse Manual Textarea
  const handleParseManualText = () => {
    if (!rawUrlText.trim()) {
      toast.error('Please paste at least one URL.')
      return
    }
    fileMutation.mutate({ content: rawUrlText, name: 'manual_list.txt' })
  }

  const handleClear = () => {
    setDiscoveredUrls([])
    setPreviewItems([])
    setSelectedFile(null)
    setRawUrlText('')
  }

  return (
    <div className="space-y-6">
      {/* Sub-mode selector buttons */}
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveMode('sitemap')}
          className={`pb-3 px-4 font-medium text-sm flex items-center gap-2 border-b-2 transition-colors ${
            activeMode === 'sitemap'
              ? 'border-primary-600 text-primary-600 dark:text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <GlobeAltIcon className="w-5 h-5" />
          Sitemap XML / .GZ URL
        </button>

        <button
          onClick={() => setActiveMode('file')}
          className={`pb-3 px-4 font-medium text-sm flex items-center gap-2 border-b-2 transition-colors ${
            activeMode === 'file'
              ? 'border-primary-600 text-primary-600 dark:text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <DocumentArrowUpIcon className="w-5 h-5" />
          Upload CSV / TSV / TXT
        </button>

        <button
          onClick={() => setActiveMode('manual')}
          className={`pb-3 px-4 font-medium text-sm flex items-center gap-2 border-b-2 transition-colors ${
            activeMode === 'manual'
              ? 'border-primary-600 text-primary-600 dark:text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <ListBulletIcon className="w-5 h-5" />
          Paste URL List
        </button>
      </div>

      {/* Mode 1: Sitemap XML */}
      {activeMode === 'sitemap' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <GlobeAltIcon className="w-5 h-5 text-primary-600" />
              Sitemap.xml Crawler
            </CardTitle>
          </CardHeader>
          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Provide an e-commerce XML sitemap (e.g. <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded">https://store.com/sitemap.xml</code> or <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded">sitemap_products_1.xml.gz</code>). 
              Our crawler automatically unpacks gzip compression, resolves nested sitemap indexes, and extracts up to 10,000+ catalog links.
            </p>

            <div className="flex flex-col sm:flex-row gap-3">
              <Input
                placeholder="https://example.com/sitemap.xml"
                value={sitemapUrl}
                onChange={(e) => setSitemapUrl(e.target.value)}
                className="flex-1"
              />
              <Button
                variant="primary"
                onClick={() => sitemapMutation.mutate()}
                isLoading={sitemapMutation.isPending}
                disabled={!sitemapUrl.trim()}
              >
                Inspect & Fetch URLs
              </Button>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="filterProducts"
                checked={filterProductsOnly}
                onChange={(e) => setFilterProductsOnly(e.target.checked)}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <label htmlFor="filterProducts" className="text-xs text-gray-600 dark:text-gray-400 cursor-pointer">
                Automatically prioritize product URLs (ignores /collections/, /blogs/, /pages/, and /cart)
              </label>
            </div>
          </div>
        </Card>
      )}

      {/* Mode 2: CSV File Upload */}
      {activeMode === 'file' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <DocumentArrowUpIcon className="w-5 h-5 text-primary-600" />
              Upload Product URL Spreadsheet
            </CardTitle>
          </CardHeader>
          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Upload a CSV, TSV, or text file containing product links. Column headers like <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded">url</code>, <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded">product_url</code>, and <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded">link</code> are auto-detected.
            </p>

            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                dragOver
                  ? 'border-primary-500 bg-primary-50/50 dark:bg-primary-950/20'
                  : 'border-gray-300 dark:border-gray-700 hover:border-primary-400'
              }`}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={(e) => e.target.files?.[0] && handleFileChosen(e.target.files[0])}
                accept=".csv,.tsv,.txt"
                className="hidden"
              />
              <DocumentArrowUpIcon className="w-12 h-12 mx-auto text-gray-400 dark:text-gray-500 mb-2" />
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {selectedFile ? selectedFile.name : 'Click to upload or drag and drop CSV / TSV'}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                CSV, TSV, or TXT up to 10MB (handles 10,000+ rows)
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Mode 3: Manual Textarea */}
      {activeMode === 'manual' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <ListBulletIcon className="w-5 h-5 text-primary-600" />
              Paste Product URLs
            </CardTitle>
          </CardHeader>
          <div className="space-y-4">
            <textarea
              rows={6}
              value={rawUrlText}
              onChange={(e) => setRawUrlText(e.target.value)}
              placeholder="https://example.com/products/item-1&#10;https://example.com/products/item-2&#10;https://example.com/products/item-3"
              className="w-full rounded-lg border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm font-mono p-3 text-gray-900 dark:text-white focus:ring-primary-500 focus:border-primary-500"
            />
            <Button
              variant="primary"
              onClick={handleParseManualText}
              isLoading={fileMutation.isPending}
              disabled={!rawUrlText.trim()}
            >
              Extract & Validate URLs
            </Button>
          </div>
        </Card>
      )}

      {/* Discovered URLs Review and Parallel Execution Panel */}
      {discoveredUrls.length > 0 && (
        <Card className="border-primary-200 dark:border-primary-800 bg-primary-50/20 dark:bg-primary-950/10">
          <CardHeader>
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2 text-primary-900 dark:text-primary-100">
                  <CheckCircleIcon className="w-6 h-6 text-success-600" />
                  Ready to Crawl: {discoveredUrls.length.toLocaleString()} Products
                </CardTitle>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  Configure parallel concurrency settings and start extraction.
                </p>
              </div>

              <Button variant="outline" size="sm" onClick={handleClear} className="text-xs">
                <TrashIcon className="w-4 h-4 mr-1 text-red-500" />
                Clear List
              </Button>
            </div>
          </CardHeader>

          <div className="space-y-5">
            {/* Job Settings Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700">
              <div className="md:col-span-1">
                <Input
                  label="Job Name"
                  value={jobName}
                  onChange={(e) => setJobName(e.target.value)}
                  placeholder="Bulk Crawl Campaign"
                />
              </div>

              <div>
                <Input
                  label="Parallel Concurrency (Workers)"
                  type="number"
                  min="1"
                  max="50"
                  value={concurrency}
                  onChange={(e) => setConcurrency(e.target.value)}
                  hint="Simultaneous worker pool size (1 - 50)"
                />
              </div>

              <div>
                <Input
                  label="Polite Delay per Worker (sec)"
                  type="number"
                  step="0.1"
                  min="0.0"
                  value={requestDelay}
                  onChange={(e) => setRequestDelay(e.target.value)}
                  hint="Delay between worker requests to prevent rate limiting"
                />
              </div>
            </div>

            {/* URL Sample Table */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>URL Preview (showing first {Math.min(10, discoveredUrls.length)} of {discoveredUrls.length.toLocaleString()})</span>
                <span className="font-mono text-primary-600 dark:text-primary-400">Total: {discoveredUrls.length} links</span>
              </div>

              <div className="max-h-56 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 font-mono text-xs divide-y divide-gray-100 dark:divide-gray-800">
                {discoveredUrls.slice(0, 10).map((u, i) => (
                  <div key={i} className="p-2.5 flex items-center justify-between gap-4 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <span className="truncate text-gray-700 dark:text-gray-300">
                      <span className="text-gray-400 mr-2">#{i + 1}</span>
                      {u}
                    </span>
                    <a
                      href={u}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:underline flex-shrink-0"
                    >
                      Visit ↗
                    </a>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Bar */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="primary"
                size="lg"
                onClick={() => startBulkMutation.mutate()}
                isLoading={startBulkMutation.isPending}
                className="w-full sm:w-auto px-8"
              >
                <PlayIcon className="w-5 h-5 mr-2" />
                Launch Parallel Crawl ({discoveredUrls.length.toLocaleString()} URLs)
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}

export default BulkSitemapImporter
