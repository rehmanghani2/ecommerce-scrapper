import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import {
  PlayIcon,
  Cog6ToothIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'
import {
  Card,
  CardHeader,
  CardTitle,
  Button,
  Input,
  Select,
  Alert,
} from '@/components/Common'
import scraperService from '@/services/scraperService'
import toast from 'react-hot-toast'

import UrlInput from './UrlInput'
import SelectorBuilder from './SelectorBuilder'
import PreviewPanel from './PreviewPanel'

const PLATFORM_OPTIONS = [
  { value: 'auto', label: 'Auto Detect' },
  { value: 'shopify', label: 'Shopify' },
  { value: 'woocommerce', label: 'WooCommerce' },
  { value: 'magento', label: 'Magento' },
  { value: 'generic', label: 'Generic' },
]

export function ScraperForm() {
  const navigate = useNavigate()
  
  // Form state
  const [url, setUrl] = useState('')
  const [jobName, setJobName] = useState('')
  const [platform, setPlatform] = useState('auto')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [customSelectors, setCustomSelectors] = useState({})
  
  // Config options
  const [config, setConfig] = useState({
    max_pages: 100,
    max_products: 10000,
    include_images: true,
    include_variants: true,
    follow_product_links: true,
    request_delay: 1000,
  })
  
  // Preview state
  const [previewData, setPreviewData] = useState(null)
  const [testResults, setTestResults] = useState({})

  // Mutations
  const analyzeMutation = useMutation({
    mutationFn: () => scraperService.previewScraping(url),
    onSuccess: (data) => {
      setPreviewData(data)
      if (data.selectors) {
        setCustomSelectors(data.selectors)
      }
      toast.success('Analysis complete!')
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to analyze URL')
    },
  })

  const testSelectorsMutation = useMutation({
    mutationFn: () => scraperService.testSelectors(url, customSelectors),
    onSuccess: (data) => {
      setTestResults(data.matched_elements || {})
      toast.success('Selectors tested!')
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to test selectors')
    },
  })

  const startScrapingMutation = useMutation({
    mutationFn: () => scraperService.startScraping(url, jobName, {
      ...config,
      platform: platform !== 'auto' ? platform : undefined,
      selectors: Object.keys(customSelectors).length > 0 ? customSelectors : undefined,
    }),
    onSuccess: (data) => {
      toast.success('Scraping job started!')
      navigate(`/jobs/${data.job_id}`)
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to start scraping')
    },
  })

  const handleConfigChange = (key, value) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }

  const handleStartScraping = () => {
    if (!url) {
      toast.error('Please enter a URL')
      return
    }
    startScrapingMutation.mutate()
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left column - Form */}
      <div className="space-y-6">
        {/* URL Input */}
        <Card padding="lg">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Target Website
          </h2>
          
          <UrlInput
            value={url}
            onChange={setUrl}
            onAnalyze={() => analyzeMutation.mutate()}
            loading={analyzeMutation.isPending}
            error={analyzeMutation.error?.message}
          />
        </Card>

        {/* Basic Options */}
        <Card>
          <CardHeader>
            <CardTitle>Scraping Options</CardTitle>
          </CardHeader>
          
          <div className="space-y-4">
            <Input
              label="Job Name (optional)"
              value={jobName}
              onChange={(e) => setJobName(e.target.value)}
              placeholder="My scraping job"
            />
            
            <Select
              label="Platform"
              options={PLATFORM_OPTIONS}
              value={platform}
              onChange={setPlatform}
            />
            
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Max Pages"
                type="number"
                value={config.max_pages}
                onChange={(e) => handleConfigChange('max_pages', parseInt(e.target.value))}
                min={1}
                max={10000}
              />
              
              <Input
                label="Max Products"
                type="number"
                value={config.max_products}
                onChange={(e) => handleConfigChange('max_products', parseInt(e.target.value))}
                min={1}
                max={100000}
              />
            </div>
            
            {/* Checkboxes */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.include_images}
                  onChange={(e) => handleConfigChange('include_images', e.target.checked)}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Include product images
                </span>
              </label>
              
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.include_variants}
                  onChange={(e) => handleConfigChange('include_variants', e.target.checked)}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Include product variants
                </span>
              </label>
              
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.follow_product_links}
                  onChange={(e) => handleConfigChange('follow_product_links', e.target.checked)}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Follow product links for details
                </span>
              </label>
            </div>
          </div>
        </Card>

        {/* Advanced Options */}
        <Card>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full flex items-center justify-between p-4 -m-6 mb-0"
          >
            <div className="flex items-center gap-2">
              <Cog6ToothIcon className="w-5 h-5 text-gray-500" />
              <span className="font-medium text-gray-900 dark:text-white">
                Advanced Options
              </span>
            </div>
            {showAdvanced ? (
              <ChevronUpIcon className="w-5 h-5 text-gray-500" />
            ) : (
              <ChevronDownIcon className="w-5 h-5 text-gray-500" />
            )}
          </button>
          
          {showAdvanced && (
            <div className="pt-4 mt-4 border-t dark:border-gray-700">
              <div className="space-y-4">
                <Input
                  label="Request Delay (ms)"
                  type="number"
                  value={config.request_delay}
                  onChange={(e) => handleConfigChange('request_delay', parseInt(e.target.value))}
                  hint="Delay between requests to avoid rate limiting"
                  min={0}
                  max={30000}
                />
                
                <SelectorBuilder
                  selectors={customSelectors}
                  onChange={setCustomSelectors}
                  testResults={testResults}
                  onTest={() => testSelectorsMutation.mutate()}
                  loading={testSelectorsMutation.isPending}
                />
              </div>
            </div>
          )}
        </Card>

        {/* Start Button */}
        <Button
          onClick={handleStartScraping}
          loading={startScrapingMutation.isPending}
          icon={PlayIcon}
          size="lg"
          fullWidth
          className="py-4"
        >
          Start Scraping
        </Button>
      </div>

      {/* Right column - Preview */}
      <div>
        <PreviewPanel
          data={previewData}
          loading={analyzeMutation.isPending}
          error={analyzeMutation.error?.message}
        />
      </div>
    </div>
  )
}

export default ScraperForm