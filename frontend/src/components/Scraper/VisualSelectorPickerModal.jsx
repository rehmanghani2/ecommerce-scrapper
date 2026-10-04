import React, { useState, useEffect, useRef } from 'react'
import {
  CursorArrowRaysIcon,
  CheckCircleIcon,
  ArrowPathIcon,
  EyeIcon,
  BookmarkIcon,
  XMarkIcon,
  ArrowTopRightOnSquareIcon,
  SparklesIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { Button, Input, Badge, Spinner, Alert } from '@/components/Common'
import scraperService from '@/services/scraperService'
import toast from 'react-hot-toast'

const SELECTOR_FIELDS = [
  { key: 'product_card', label: 'Product Card (Container)', icon: '📦', hint: 'Click the card or box that wraps each individual product' },
  { key: 'product_name', label: 'Product Name', icon: '🏷️', hint: 'Click the title or name of any product' },
  { key: 'product_price', label: 'Price', icon: '💰', hint: 'Click the price element' },
  { key: 'product_image', label: 'Product Image', icon: '🖼️', hint: 'Click the product photo / thumbnail' },
  { key: 'product_link', label: 'Product Link', icon: '🔗', hint: 'Click the title link or view button' },
]

export function VisualSelectorPickerModal({
  isOpen,
  onClose,
  initialUrl = '',
  initialSelectors = {},
  onApplySelectors,
}) {
  const [url, setUrl] = useState(initialUrl || '')
  const [activeUrl, setActiveUrl] = useState(initialUrl || '')
  const [activeField, setActiveField] = useState('product_card')
  const [selectors, setSelectors] = useState(initialSelectors || {})
  const [fieldStats, setFieldStats] = useState({})
  const [iframeLoading, setIframeLoading] = useState(true)
  const [lastClickedElement, setLastClickedElement] = useState(null)
  
  // Extraction Preview Table State
  const [testing, setTesting] = useState(false)
  const [previewProducts, setPreviewProducts] = useState(null)
  const [showPreviewModal, setShowPreviewModal] = useState(false)

  // Presets State
  const [presets, setPresets] = useState([])
  const [recipeName, setRecipeName] = useState('')
  const [savingRecipe, setSavingRecipe] = useState(false)

  const iframeRef = useRef(null)

  useEffect(() => {
    if (isOpen) {
      if (initialUrl) {
        setUrl(initialUrl)
        setActiveUrl(initialUrl)
      }
      if (initialSelectors) {
        setSelectors(initialSelectors)
      }
      loadPresets()
    }
  }, [isOpen, initialUrl])

  const loadPresets = async () => {
    try {
      const data = await scraperService.getPresets()
      setPresets(data || [])
    } catch (e) {
      console.error('Failed to load presets:', e)
    }
  }

  // Listen for messages from inside the rendered sandbox iframe
  useEffect(() => {
    const handleMessage = (event) => {
      const data = event.data
      if (!data) return

      if (data.type === 'PICKER_ELEMENT_SELECTED') {
        const { selector, tagName, text, src, href, matchCount } = data
        setLastClickedElement({ selector, tagName, text, matchCount })

        // Update currently active field selector
        setSelectors((prev) => ({
          ...prev,
          [activeField]: selector,
        }))

        setFieldStats((prev) => ({
          ...prev,
          [activeField]: {
            count: matchCount,
            sample: text || src || href || selector,
          },
        }))

        toast.success(`Picked ${activeField.replace('_', ' ')} (${matchCount} elements matched)`)

        // Highlight matching elements in iframe
        if (iframeRef.current?.contentWindow) {
          iframeRef.current.contentWindow.postMessage({
            type: 'HIGHLIGHT_QUERY',
            selector: selector,
          }, '*')
        }

        // Auto-advance to next empty field
        const currentIndex = SELECTOR_FIELDS.findIndex((f) => f.key === activeField)
        if (currentIndex < SELECTOR_FIELDS.length - 1) {
          const nextField = SELECTOR_FIELDS[currentIndex + 1].key
          if (!selectors[nextField]) {
            setActiveField(nextField)
          }
        }
      } else if (data.type === 'PICKER_QUERY_COUNT') {
        setFieldStats((prev) => ({
          ...prev,
          [activeField]: {
            ...(prev[activeField] || {}),
            count: data.count,
          },
        }))
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [activeField, selectors])

  // Reload iframe with URL
  const handleLoadUrl = () => {
    if (!url) return
    let clean = url.trim()
    if (!clean.startsWith('http://') && !clean.startsWith('https://')) {
      clean = `https://${clean}`
      setUrl(clean)
    }
    setActiveUrl(clean)
    setIframeLoading(true)
  }

  // Highlight specific selector inside iframe
  const handleHighlight = (selector) => {
    if (iframeRef.current?.contentWindow && selector) {
      iframeRef.current.contentWindow.postMessage({
        type: 'HIGHLIGHT_QUERY',
        selector: selector,
      }, '*')
    }
  }

  // Clear highlights
  const handleClearHighlights = () => {
    if (iframeRef.current?.contentWindow) {
      iframeRef.current.contentWindow.postMessage({
        type: 'CLEAR_HIGHLIGHTS',
      }, '*')
    }
  }

  // Test extraction preview
  const handleTestExtraction = async () => {
    if (!activeUrl) {
      toast.error('Please enter a target URL')
      return
    }
    try {
      setTesting(true)
      const res = await scraperService.testVisualSelectors(activeUrl, selectors)
      if (res.preview_products && res.preview_products.length > 0) {
        setPreviewProducts(res.preview_products)
        setShowPreviewModal(true)
        toast.success(`Preview extracted ${res.preview_products.length} products!`)
      } else {
        toast.error('No products could be extracted with these selectors.')
      }
    } catch (e) {
      toast.error('Test extraction failed: ' + e.message)
    } finally {
      setTesting(false)
    }
  }

  // Save as recipe preset
  const handleSaveRecipe = async () => {
    if (!recipeName) {
      toast.error('Please give your recipe a name')
      return
    }
    try {
      setSavingRecipe(true)
      let domain = ''
      try {
        domain = new URL(activeUrl).hostname
      } catch (e) {}

      await scraperService.savePreset({
        name: recipeName,
        domain: domain,
        selectors: selectors,
      })
      toast.success('Custom recipe saved!')
      setRecipeName('')
      loadPresets()
    } catch (e) {
      toast.error('Failed to save recipe: ' + e.message)
    } finally {
      setSavingRecipe(false)
    }
  }

  // Apply selectors back to ScraperForm
  const handleApply = () => {
    if (onApplySelectors) {
      onApplySelectors(selectors)
    }
    toast.success('Selectors applied to scraper configuration!')
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/75 flex flex-col backdrop-blur-sm">
      {/* Top Header Bar */}
      <div className="bg-gray-900 border-b border-gray-800 px-4 py-3 flex items-center justify-between text-white">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-lg bg-primary-600 text-white">
            <CursorArrowRaysIcon className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold flex items-center gap-2">
              Visual Selector Studio
              <Badge variant="primary" size="sm">Point & Click</Badge>
            </h2>
            <p className="text-xs text-gray-400">Click any element in the web page preview to automatically bind CSS selectors</p>
          </div>
        </div>

        {/* URL Address Bar */}
        <div className="flex-1 max-w-2xl mx-6 flex items-center gap-2">
          <Input
            placeholder="https://example.com/shop"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleLoadUrl()}
            className="bg-gray-800 text-white border-gray-700 text-xs py-1.5"
          />
          <Button
            size="sm"
            variant="primary"
            icon={ArrowPathIcon}
            onClick={handleLoadUrl}
          >
            Load
          </Button>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            icon={EyeIcon}
            disabled={testing}
            onClick={handleTestExtraction}
          >
            {testing ? 'Testing...' : 'Test Extraction'}
          </Button>

          <Button
            size="sm"
            variant="primary"
            icon={CheckCircleIcon}
            onClick={handleApply}
          >
            Apply Selectors
          </Button>

          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors ml-2"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>
      </div>

      {/* Main Studio Body: Sidebar on Left, Iframe Sandbox on Right */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Control Panel */}
        <div className="w-80 sm:w-96 bg-gray-900 border-r border-gray-800 flex flex-col overflow-y-auto p-4 space-y-4 text-white">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
              Active Field Target
            </h3>
            <p className="text-xs text-gray-400">
              Select which field you want to pick, then click on the page:
            </p>
          </div>

          {/* Selector Field Cards */}
          <div className="space-y-2">
            {SELECTOR_FIELDS.map((field) => {
              const isActive = activeField === field.key
              const selValue = selectors[field.key] || ''
              const stats = fieldStats[field.key]

              return (
                <div
                  key={field.key}
                  onClick={() => {
                    setActiveField(field.key)
                    if (selValue) handleHighlight(selValue)
                  }}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    isActive
                      ? 'border-primary-500 bg-primary-950/40 shadow-sm ring-1 ring-primary-500'
                      : 'border-gray-800 bg-gray-800/60 hover:border-gray-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold flex items-center gap-1.5 text-gray-200">
                      <span>{field.icon}</span>
                      {field.label}
                    </span>
                    {isActive ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold text-primary-400 bg-primary-900/60 px-1.5 py-0.5 rounded animate-pulse">
                        🎯 Picking...
                      </span>
                    ) : selValue ? (
                      <span className="text-[10px] font-medium text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded">
                        ✓ {stats?.count ? `${stats.count} items` : 'Picked'}
                      </span>
                    ) : (
                      <span className="text-[10px] text-gray-500">Not set</span>
                    )}
                  </div>

                  <p className="text-[11px] text-gray-400 mb-1.5">{field.hint}</p>

                  {selValue ? (
                    <div className="space-y-1">
                      <div className="flex items-center gap-1 bg-gray-950/80 rounded px-2 py-1 border border-gray-800">
                        <code className="text-[11px] font-mono text-emerald-300 truncate flex-1">
                          {selValue}
                        </code>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectors((prev) => ({ ...prev, [field.key]: '' }))
                            handleClearHighlights()
                          }}
                          className="text-gray-500 hover:text-rose-400"
                        >
                          <TrashIcon className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {stats?.sample && (
                        <p className="text-[10px] text-gray-400 truncate italic">
                          Sample: "{stats.sample}"
                        </p>
                      )}
                    </div>
                  ) : null}
                </div>
              )
            })}
          </div>

          {/* Quick Presets / Recipe Storage */}
          <div className="pt-3 border-t border-gray-800 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1.5">
              <BookmarkIcon className="w-4 h-4 text-primary-400" />
              Save As Recipe
            </h4>
            <div className="flex gap-2">
              <Input
                placeholder="e.g. Zara Products"
                value={recipeName}
                onChange={(e) => setRecipeName(e.target.value)}
                className="bg-gray-800 text-white text-xs py-1"
              />
              <Button
                size="sm"
                variant="secondary"
                disabled={savingRecipe || !recipeName}
                onClick={handleSaveRecipe}
              >
                Save
              </Button>
            </div>

            {presets && presets.length > 0 && (
              <div className="space-y-1 pt-1">
                <span className="text-[11px] text-gray-400">Saved Presets:</span>
                <div className="max-h-24 overflow-y-auto space-y-1">
                  {presets.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => {
                        if (p.selectors) {
                          setSelectors(p.selectors)
                          toast.success(`Loaded recipe: ${p.name}`)
                        }
                      }}
                      className="w-full text-left text-xs px-2 py-1 rounded bg-gray-800/80 hover:bg-gray-700 text-gray-300 truncate flex items-center justify-between"
                    >
                      <span className="truncate">{p.name}</span>
                      <span className="text-[10px] text-primary-400 font-mono">{p.domain || 'All'}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Preview Sandbox (Iframe) */}
        <div className="flex-1 bg-gray-950 flex flex-col relative overflow-hidden">
          {activeUrl ? (
            <>
              {iframeLoading && (
                <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-gray-950/80 backdrop-blur-sm">
                  <Spinner size="lg" />
                  <p className="text-sm font-medium text-gray-300 mt-3">Rendering target page sandbox...</p>
                  <p className="text-xs text-gray-500 mt-1">Injecting visual inspector and styling</p>
                </div>
              )}

              <iframe
                ref={iframeRef}
                src={scraperService.getVisualPickerRenderUrl(activeUrl)}
                title="Visual Selector Picker Sandbox"
                className="w-full h-full border-none bg-white"
                sandbox="allow-same-origin allow-scripts"
                onLoad={() => setIframeLoading(false)}
              />
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <CursorArrowRaysIcon className="w-12 h-12 text-gray-600 mb-3" />
              <h3 className="text-base font-semibold text-gray-200">No Webpage Loaded Yet</h3>
              <p className="text-xs text-gray-400 max-w-md mt-1">
                Enter an e-commerce catalog or store URL in the address bar above and click "Load" to start clicking and picking selectors.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Test Extraction Preview Modal */}
      {showPreviewModal && previewProducts && (
        <div className="fixed inset-0 z-60 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl max-w-4xl w-full max-h-[85vh] flex flex-col overflow-hidden border border-gray-200 dark:border-gray-800">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  <SparklesIcon className="w-5 h-5 text-primary-600" />
                  Real-Time Extraction Preview
                </h3>
                <p className="text-xs text-gray-500">
                  Data extracted live using your visual selectors ({previewProducts.length} sample items found)
                </p>
              </div>
              <button
                onClick={() => setShowPreviewModal(false)}
                className="p-1 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800">
                <thead className="bg-gray-50 dark:bg-gray-800/60">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-bold text-gray-500 uppercase">Image</th>
                    <th className="px-3 py-2 text-left text-xs font-bold text-gray-500 uppercase">Product Name</th>
                    <th className="px-3 py-2 text-left text-xs font-bold text-gray-500 uppercase">Price</th>
                    <th className="px-3 py-2 text-left text-xs font-bold text-gray-500 uppercase">Link</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800 text-xs">
                  {previewProducts.map((p, idx) => (
                    <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800/40">
                      <td className="px-3 py-2">
                        {p.image_url ? (
                          <img src={p.image_url} alt="" className="w-10 h-10 object-cover rounded bg-gray-100" />
                        ) : (
                          <span className="text-gray-400 italic">No image</span>
                        )}
                      </td>
                      <td className="px-3 py-2 font-medium text-gray-900 dark:text-white max-w-xs truncate">
                        {p.name || <span className="text-red-400 italic">Missing name</span>}
                      </td>
                      <td className="px-3 py-2 font-semibold text-emerald-600 dark:text-emerald-400">
                        {p.price || <span className="text-gray-400 italic">—</span>}
                      </td>
                      <td className="px-3 py-2">
                        {p.url ? (
                          <a href={p.url} target="_blank" rel="noreferrer" className="text-primary-600 hover:underline flex items-center gap-1">
                            Link <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                          </a>
                        ) : (
                          <span className="text-gray-400 italic">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-800 flex justify-end gap-3 bg-gray-50 dark:bg-gray-800/30">
              <Button variant="secondary" onClick={() => setShowPreviewModal(false)}>
                Back to Studio
              </Button>
              <Button variant="primary" onClick={() => { setShowPreviewModal(false); handleApply(); }}>
                Looks Good — Apply Selectors
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default VisualSelectorPickerModal
