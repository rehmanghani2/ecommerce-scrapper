import React, { useState } from 'react'
import { GlobeAltIcon, MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { cn, isValidUrl, extractDomain } from '@/utils/helpers'
import { Button, Spinner } from '@/components/Common'

export function UrlInput({
  value,
  onChange,
  onAnalyze,
  loading = false,
  error,
  placeholder = 'Enter e-commerce website URL...',
  className,
}) {
  const [isFocused, setIsFocused] = useState(false)

  const handleClear = () => {
    onChange('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && value && isValidUrl(value)) {
      onAnalyze?.()
    }
  }

  const domain = value && isValidUrl(value) ? extractDomain(value) : null

  return (
    <div className={className}>
      <div
        className={cn(
          'relative flex items-center rounded-xl border-2 bg-white dark:bg-gray-800 transition-all duration-200',
          isFocused
            ? 'border-primary-500 ring-4 ring-primary-500/20'
            : 'border-gray-200 dark:border-gray-700',
          error && 'border-danger-500'
        )}
      >
        <div className="pl-4">
          <GlobeAltIcon className="w-5 h-5 text-gray-400" />
        </div>
        
        <input
          type="url"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={cn(
            'flex-1 px-4 py-4 text-lg bg-transparent border-0 outline-none',
            'placeholder-gray-400 text-gray-900 dark:text-white'
          )}
        />
        
        {value && (
          <button
            onClick={handleClear}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        )}
        
        <div className="pr-2">
          <Button
            onClick={onAnalyze}
            disabled={!value || !isValidUrl(value) || loading}
            loading={loading}
            icon={MagnifyingGlassIcon}
            className="px-6"
          >
            Analyze
          </Button>
        </div>
      </div>
      
      {error && (
        <p className="mt-2 text-sm text-danger-600 dark:text-danger-400">{error}</p>
      )}
      
      {domain && !error && (
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          Target: <span className="font-medium text-gray-700 dark:text-gray-300">{domain}</span>
        </p>
      )}
    </div>
  )
}

export default UrlInput