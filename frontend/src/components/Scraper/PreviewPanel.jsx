import React from 'react'
import {
  EyeIcon,
  CubeIcon,
  CurrencyPoundIcon,
  PhotoIcon,
  TagIcon,
} from '@heroicons/react/24/outline'
import { cn, formatPrice } from '@/utils/helpers'
import { Card, CardHeader, CardTitle, Badge, Spinner, EmptyState } from '@/components/Common'

export function PreviewPanel({
  data,
  loading = false,
  error,
}) {
  if (loading) {
    return (
      <Card>
        <div className="flex flex-col items-center justify-center py-12">
          <Spinner size="lg" className="text-primary-600" />
          <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
            Analyzing website...
          </p>
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <EmptyState
          title="Analysis Failed"
          description={error}
        />
      </Card>
    )
  }

  if (!data) {
    return (
      <Card>
        <EmptyState
          icon={EyeIcon}
          title="No Preview"
          description="Enter a URL and click Analyze to preview the scraping results."
        />
      </Card>
    )
  }

  const { platform, confidence = 0, selectors, sample_products = [], discovery } = data

  return (
    <div className="space-y-4">
      {/* Detection Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <EyeIcon className="w-5 h-5" />
            Detection Results
          </CardTitle>
        </CardHeader>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Platform</p>
            <p className="font-medium text-gray-900 dark:text-white capitalize">
              {platform || 'Unknown'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Confidence</p>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full',
                    confidence >= 0.7 ? 'bg-success-500' :
                    confidence >= 0.4 ? 'bg-warning-500' : 'bg-danger-500'
                  )}
                  style={{ width: `${confidence * 100}%` }}
                />
              </div>
              <span className="text-sm font-medium">
                {Math.round(confidence * 100)}%
              </span>
            </div>
          </div>
        </div>
        
        {selectors && Object.keys(selectors).length > 0 && (
          <div className="mt-4 pt-4 border-t dark:border-gray-700">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Detected Selectors
            </p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(selectors).map(([key, value]) => (
                value && (
                  <Badge key={key} variant="secondary" size="sm">
                    {key.replace(/_/g, ' ')}
                  </Badge>
                )
              ))}
            </div>
          </div>
        )}
      </Card>


      {discovery && (
        <Card>
          <CardHeader>
            <CardTitle>Website discovery</CardTitle>
          </CardHeader>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
              <p className="text-gray-500 dark:text-gray-400">Categories found</p>
              <p className="mt-1 text-xl font-semibold text-gray-900 dark:text-white">{discovery.category_count ?? discovery.categories?.length ?? 0}</p>
            </div>
            <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
              <p className="text-gray-500 dark:text-gray-400">Product URL samples</p>
              <p className="mt-1 text-xl font-semibold text-gray-900 dark:text-white">{discovery.product_url_count_estimate ?? discovery.product_url_samples?.length ?? 0}</p>
            </div>
            <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
              <p className="text-gray-500 dark:text-gray-400">Sitemap</p>
              <p className="mt-1 font-medium capitalize text-gray-900 dark:text-white">{discovery.sitemap_status || 'Not found'}</p>
            </div>
            <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
              <p className="text-gray-500 dark:text-gray-400">Products on landing page</p>
              <p className="mt-1 text-xl font-semibold text-gray-900 dark:text-white">{discovery.product_dom_nodes_on_landing_page ?? 0}</p>
            </div>
          </div>
          {discovery.categories?.length > 0 ? (
            <div className="mt-4">
              <p className="mb-2 text-sm font-semibold text-gray-800 dark:text-gray-200">Detected categories</p>
              <div className="max-h-72 space-y-2 overflow-y-auto">
                {discovery.categories.map((category, index) => (
                  <div key={category.url || index} className="flex items-center justify-between gap-3 rounded-lg border border-gray-100 dark:border-gray-700 px-3 py-2">
                    <span className="min-w-0 truncate text-sm text-gray-800 dark:text-gray-200">{category.name}</span>
                    <a href={category.url} target="_blank" rel="noopener noreferrer" className="shrink-0 text-xs text-primary-600 hover:underline">Open</a>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">No category links were confidently identified on the landing page or sitemap.</p>
          )}
          {discovery.product_url_samples?.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-sm font-semibold text-gray-800 dark:text-gray-200">Product URL samples</p>
              <ul className="max-h-40 space-y-1 overflow-y-auto text-xs text-gray-500 dark:text-gray-400">
                {discovery.product_url_samples.slice(0, 10).map((productUrl) => <li key={productUrl} className="truncate">{productUrl}</li>)}
              </ul>
            </div>
          )}
          {discovery.truncated && <p className="mt-3 text-xs text-amber-600">Discovery was capped at the configured link limit.</p>}
          {data.limitations?.length > 0 && <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">{data.limitations[0]}</p>}
        </Card>
      )}
\n      {/* Sample Products */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CubeIcon className="w-5 h-5" />
            Sample Products ({sample_products.length})
          </CardTitle>
        </CardHeader>
        
        {sample_products.length === 0 ? (
          <EmptyState
            title="No Products Found"
            description="Could not extract any products. Try adjusting the selectors."
          />
        ) : (
          <div className="space-y-3">
            {sample_products.map((product, index) => (
              <ProductPreviewCard key={index} product={product} />
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}

function ProductPreviewCard({ product }) {
  return (
    <div className="flex gap-4 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
      {/* Image */}
      <div className="flex-shrink-0 w-16 h-16 bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden">
        {product.image ? (
          <img
            src={product.image}
            alt={product.name}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.target.style.display = 'none'
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <PhotoIcon className="w-6 h-6 text-gray-400" />
          </div>
        )}
      </div>
      
      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 dark:text-white truncate">
          {product.name || 'Unknown Product'}
        </p>
        
        <div className="flex items-center gap-4 mt-1">
          {product.price && (
            <span className="flex items-center gap-1 text-sm text-success-600 dark:text-success-400">
              <CurrencyPoundIcon className="w-4 h-4" />
              {product.price}
            </span>
          )}
          
          {product.url && (
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 truncate"
            >
              View →
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

export default PreviewPanel