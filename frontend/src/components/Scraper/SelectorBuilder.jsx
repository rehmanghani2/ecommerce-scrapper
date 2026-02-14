import React, { useState } from 'react'
import {
  CodeBracketIcon,
  PlusIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'
import { Card, CardHeader, CardTitle, Button, Input, Badge } from '@/components/Common'

const SELECTOR_PRESETS = {
  product_card: [
    '.product',
    '.product-item',
    '.product-card',
    '[data-product]',
    '.grid-item',
  ],
  product_name: [
    '.product-title',
    '.product-name',
    'h2',
    'h3',
    '.title',
  ],
  product_price: [
    '.price',
    '.product-price',
    '[data-price]',
    '.amount',
    '.money',
  ],
  product_image: [
    '.product-image img',
    '.product-img img',
    'img.product',
    '[data-product-image]',
  ],
  pagination_next: [
    'a[rel="next"]',
    '.pagination .next',
    '.next-page',
    'a:has-text("Next")',
  ],
}

export function SelectorBuilder({
  selectors = {},
  onChange,
  testResults = {},
  onTest,
  loading = false,
}) {
  const [activeField, setActiveField] = useState(null)

  const selectorFields = [
    { key: 'product_card', label: 'Product Card', description: 'Container for each product' },
    { key: 'product_name', label: 'Product Name', description: 'Product title element' },
    { key: 'product_price', label: 'Product Price', description: 'Price display element' },
    { key: 'product_image', label: 'Product Image', description: 'Main product image' },
    { key: 'product_link', label: 'Product Link', description: 'Link to product detail page' },
    { key: 'pagination_next', label: 'Next Page', description: 'Pagination next button' },
  ]

  const handleSelectorChange = (key, value) => {
    onChange({
      ...selectors,
      [key]: value,
    })
  }

  const handlePresetSelect = (key, preset) => {
    handleSelectorChange(key, preset)
    setActiveField(null)
  }

  const getTestStatus = (key) => {
    const result = testResults[key]
    if (!result) return null
    return result.valid ? 'success' : 'error'
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CodeBracketIcon className="w-5 h-5" />
          CSS Selectors
        </CardTitle>
      </CardHeader>
      
      <div className="space-y-4">
        {selectorFields.map((field) => {
          const status = getTestStatus(field.key)
          const matchCount = testResults[field.key]?.count
          
          return (
            <div key={field.key} className="relative">
              <div className="flex items-center justify-between mb-1">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {field.label}
                </label>
                {status && (
                  <div className="flex items-center gap-1 text-sm">
                    {status === 'success' ? (
                      <>
                        <CheckCircleIcon className="w-4 h-4 text-success-500" />
                        <span className="text-success-600 dark:text-success-400">
                          {matchCount} found
                        </span>
                      </>
                    ) : (
                      <>
                        <XCircleIcon className="w-4 h-4 text-danger-500" />
                        <span className="text-danger-600 dark:text-danger-400">
                          No matches
                        </span>
                      </>
                    )}
                  </div>
                )}
              </div>
              
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Input
                    value={selectors[field.key] || ''}
                    onChange={(e) => handleSelectorChange(field.key, e.target.value)}
                    onFocus={() => setActiveField(field.key)}
                    placeholder={`e.g., ${SELECTOR_PRESETS[field.key]?.[0] || '.selector'}`}
                    className={cn(
                      'font-mono text-sm',
                      status === 'success' && 'border-success-500',
                      status === 'error' && 'border-danger-500'
                    )}
                  />
                  
                  {/* Presets dropdown */}
                  {activeField === field.key && SELECTOR_PRESETS[field.key] && (
                    <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 rounded-lg shadow-lg border dark:border-gray-700 py-1">
                      <div className="px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400">
                        Common selectors
                      </div>
                      {SELECTOR_PRESETS[field.key].map((preset) => (
                        <button
                          key={preset}
                          onClick={() => handlePresetSelect(field.key, preset)}
                          className="w-full px-3 py-2 text-left text-sm font-mono hover:bg-gray-100 dark:hover:bg-gray-700"
                        >
                          {preset}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {field.description}
              </p>
            </div>
          )
        })}
        
        <div className="pt-4 border-t dark:border-gray-700">
          <Button
            onClick={onTest}
            loading={loading}
            variant="secondary"
            fullWidth
          >
            Test Selectors
          </Button>
        </div>
      </div>
    </Card>
  )
}

export default SelectorBuilder