import React, { useState } from 'react'
import {
  GlobeAltIcon,
  LightBulbIcon,
  CheckCircleIcon,
  DocumentArrowUpIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline'
import { Card, Alert } from '@/components/Common'
import { ScraperForm, BulkSitemapImporter } from '@/components/Scraper'

const QUICK_TIPS = [
  'Auto-detection works best with standard e-commerce platforms',
  'For complex sites, you can customize CSS selectors',
  'Start with a category page for better product discovery',
  'Use the preview feature to verify selectors before starting',
]

const SUPPORTED_FEATURES = [
  'Product names, prices, and descriptions',
  'Images and image galleries',
  'Product variants (size, color, etc.)',
  'Stock availability status',
  'Categories and breadcrumbs',
  'Specifications and attributes',
]

export default function Scraper() {
  const [activeTab, setActiveTab] = useState('single') // 'single' | 'bulk'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
          <GlobeAltIcon className="w-8 h-8 text-primary-600" />
          Web Scraper
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Extract product data from any e-commerce website or crawl 10,000+ products via Sitemap XML / CSV
        </p>
      </div>

      {/* Main Mode Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-2 rounded-xl shadow-sm">
        <button
          onClick={() => setActiveTab('single')}
          className={`flex-1 py-3 px-4 font-semibold text-sm rounded-lg flex items-center justify-center gap-2 transition-all ${
            activeTab === 'single'
              ? 'bg-primary-50 dark:bg-primary-950/40 text-primary-700 dark:text-primary-300 shadow-sm border border-primary-200 dark:border-primary-800'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
          }`}
        >
          <MagnifyingGlassIcon className="w-5 h-5 text-primary-600" />
          Single URL / Store Crawler
        </button>

        <button
          onClick={() => setActiveTab('bulk')}
          className={`flex-1 py-3 px-4 font-semibold text-sm rounded-lg flex items-center justify-center gap-2 transition-all ${
            activeTab === 'bulk'
              ? 'bg-primary-50 dark:bg-primary-950/40 text-primary-700 dark:text-primary-300 shadow-sm border border-primary-200 dark:border-primary-800'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
          }`}
        >
          <DocumentArrowUpIcon className="w-5 h-5 text-primary-600" />
          Bulk URL & Sitemap.xml Importer (10,000+ Parallel)
        </button>
      </div>

      {/* Content based on Active Tab */}
      {activeTab === 'single' ? (
        <>
          {/* Info Alert */}
          <Alert variant="info" title="How it works">
            Enter a URL from an e-commerce website, and our scraper will automatically 
            detect product listings and extract all available data. You can customize 
            the extraction settings or let the auto-detection handle everything.
          </Alert>

          {/* Main Form */}
          <ScraperForm />
        </>
      ) : (
        <>
          <Alert variant="success" title="High-Throughput Parallel Scraping">
            Upload a spreadsheet (CSV/TSV), paste a list of links, or provide a sitemap XML URL. 
            The system handles nested sitemap indexes and crawls up to 10,000+ products concurrently 
            using an asyncio worker pool with rotating proxy support.
          </Alert>

          <BulkSitemapImporter />
        </>
      )}

      {/* Help Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
        {/* Quick Tips */}
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <LightBulbIcon className="w-5 h-5 text-warning-500" />
            <h3 className="font-semibold text-gray-900 dark:text-white">
              Quick Tips
            </h3>
          </div>
          
          <ul className="space-y-2">
            {QUICK_TIPS.map((tip, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                <span className="text-primary-600 dark:text-primary-400 mt-0.5">•</span>
                {tip}
              </li>
            ))}
          </ul>
        </Card>

        {/* Supported Features */}
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <CheckCircleIcon className="w-5 h-5 text-success-500" />
            <h3 className="font-semibold text-gray-900 dark:text-white">
              What We Extract
            </h3>
          </div>
          
          <ul className="space-y-2">
            {SUPPORTED_FEATURES.map((feature, index) => (
              <li key={index} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <CheckCircleIcon className="w-4 h-4 text-success-500 flex-shrink-0" />
                {feature}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {/* Supported Platforms */}
      <Card>
        <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
          Optimized for Popular Platforms
        </h3>
        
        <div className="flex flex-wrap gap-3">
          {['Shopify', 'WooCommerce', 'Magento', 'BigCommerce', 'PrestaShop', 'OpenCart', 'Custom Sites'].map((platform) => (
            <span
              key={platform}
              className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              {platform}
            </span>
          ))}
        </div>
      </Card>
    </div>
  )
}