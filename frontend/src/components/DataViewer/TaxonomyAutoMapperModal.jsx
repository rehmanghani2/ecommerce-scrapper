import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  TagIcon,
  SparklesIcon,
  CheckCircleIcon,
  FolderIcon,
  ArrowPathIcon,
  MagnifyingGlassIcon,
  CheckIcon,
  XMarkIcon,
  FunnelIcon,
  BookOpenIcon,
  AdjustmentsHorizontalIcon,
  BuildingStorefrontIcon,
  PlusIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { Modal, ModalFooter, Button, Badge, Card } from '@/components/Common'
import { taxonomyService } from '@/services/taxonomyService'
import { cn } from '@/utils/helpers'
import toast from 'react-hot-toast'

export default function TaxonomyAutoMapperModal({ isOpen, onClose }) {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('review') // 'review', 'batch', 'rules', 'tree'
  const [selectedTaxonomyId, setSelectedTaxonomyId] = useState(null)
  const [confidenceFilter, setConfidenceFilter] = useState('all') // 'all', 'high', 'review'
  const [filterDomain, setFilterDomain] = useState('')
  const [editingMappingId, setEditingMappingId] = useState(null)
  const [customCategoryInput, setCustomCategoryInput] = useState('')
  const [batchLimit, setBatchLimit] = useState(50)
  const [overwriteExisting, setOverwriteExisting] = useState(false)
  const [newRuleSource, setNewRuleSource] = useState('')
  const [newRuleTarget, setNewRuleTarget] = useState('')
  const [newRuleDomain, setNewRuleDomain] = useState('')
  const [isClassifyingAiId, setIsClassifyingAiId] = useState(null)

  // 1. Fetch Taxonomy Standards
  const { data: standards = [], isLoading: isLoadingStandards } = useQuery({
    queryKey: ['taxonomyStandards'],
    queryFn: taxonomyService.getStandards,
    enabled: isOpen,
    onSuccess: (data) => {
      if (data && data.length > 0 && !selectedTaxonomyId) {
        setSelectedTaxonomyId(data[0].id)
      }
    },
  })

  // Set default taxonomy standard on first load
  const activeTaxonomyId = selectedTaxonomyId || (standards[0]?.id ?? 1)
  const activeStandard = standards.find((s) => s.id === activeTaxonomyId) || standards[0]

  // 2. Fetch Coverage Summary
  const { data: summary, refetch: refetchSummary, isLoading: isLoadingSummary } = useQuery({
    queryKey: ['taxonomySummary', activeTaxonomyId],
    queryFn: () => taxonomyService.getSummary(activeTaxonomyId),
    enabled: isOpen && !!activeTaxonomyId,
  })

  // 3. Fetch Mappings for Review
  const minConfidenceParam =
    confidenceFilter === 'high' ? 0.8 : confidenceFilter === 'review' ? undefined : undefined
  const maxConfidenceParam = confidenceFilter === 'review' ? 0.79 : undefined

  const {
    data: mappingsData,
    refetch: refetchMappings,
    isLoading: isLoadingMappings,
  } = useQuery({
    queryKey: ['taxonomyMappings', activeTaxonomyId, confidenceFilter],
    queryFn: () =>
      taxonomyService.getMappings({
        taxonomy_id: activeTaxonomyId,
        min_confidence: minConfidenceParam,
        max_confidence: maxConfidenceParam,
        page_size: 50,
      }),
    enabled: isOpen && !!activeTaxonomyId,
  })

  // 4. Fetch Taxonomy Hierarchy Tree
  const { data: treeNodes = [], isLoading: isLoadingTree } = useQuery({
    queryKey: ['taxonomyTree', activeTaxonomyId],
    queryFn: () => taxonomyService.getTaxonomyTree(activeTaxonomyId),
    enabled: isOpen && activeTab === 'tree' && !!activeTaxonomyId,
  })

  // 5. Fetch Rules
  const { data: rules = [], refetch: refetchRules, isLoading: isLoadingRules } = useQuery({
    queryKey: ['taxonomyRules', activeTaxonomyId],
    queryFn: () => taxonomyService.getRules(activeTaxonomyId),
    enabled: isOpen && activeTab === 'rules' && !!activeTaxonomyId,
  })

  // Mutation: Batch Auto-Categorization
  const autoCategorizeMutation = useMutation({
    mutationFn: taxonomyService.autoCategorizeCatalog,
    onSuccess: (res) => {
      if (res.success) {
        toast.success(`Successfully mapped ${res.classified_count} products!`)
        refetchSummary()
        refetchMappings()
        queryClient.invalidateQueries({ queryKey: ['products'] })
        setActiveTab('review')
      } else {
        toast.error(res.error || 'Auto-categorization failed')
      }
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Auto-categorization request failed')
    },
  })

  // Mutation: Verify / Override Mapping
  const verifyMutation = useMutation({
    mutationFn: taxonomyService.verifyMapping,
    onSuccess: () => {
      toast.success('Category mapping verified & approved!')
      setEditingMappingId(null)
      refetchSummary()
      refetchMappings()
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Verification failed'),
  })

  // Mutation: Classify Single Product with Gemini AI
  const classifySingleMutation = useMutation({
    mutationFn: taxonomyService.classifyProduct,
    onSuccess: (res) => {
      setIsClassifyingAiId(null)
      toast.success(`AI classified: ${res.category_path} (${Math.round((res.confidence || 0) * 100)}%)`)
      refetchSummary()
      refetchMappings()
    },
    onError: (err) => {
      setIsClassifyingAiId(null)
      toast.error(err.response?.data?.detail || 'AI classification failed')
    },
  })

  // Mutation: Create Rule
  const createRuleMutation = useMutation({
    mutationFn: taxonomyService.createRule,
    onSuccess: () => {
      toast.success('Category translation rule created!')
      setNewRuleSource('')
      setNewRuleTarget('')
      setNewRuleDomain('')
      refetchRules()
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to create rule'),
  })

  // Mutation: Delete Rule
  const deleteRuleMutation = useMutation({
    mutationFn: taxonomyService.deleteRule,
    onSuccess: () => {
      toast.success('Rule deleted')
      refetchRules()
    },
  })

  const handleRunBatch = () => {
    autoCategorizeMutation.mutate({
      taxonomy_id: activeTaxonomyId,
      limit: batchLimit,
      overwrite_existing: overwriteExisting,
      source_domain: filterDomain || undefined,
    })
  }

  const handleVerify = (productId, categoryPath) => {
    verifyMutation.mutate({
      product_id: productId,
      taxonomy_id: activeTaxonomyId,
      category_path: categoryPath,
      is_verified: true,
    })
  }

  const handleAskAi = (productId) => {
    setIsClassifyingAiId(productId)
    classifySingleMutation.mutate({
      product_id: productId,
      taxonomy_id: activeTaxonomyId,
    })
  }

  const handleCreateRule = (e) => {
    e.preventDefault()
    if (!newRuleSource.trim() || !newRuleTarget.trim()) {
      toast.error('Both source and target paths are required')
      return
    }
    createRuleMutation.mutate({
      source_category_path: newRuleSource.trim(),
      target_category_path: newRuleTarget.trim(),
      target_taxonomy_id: activeTaxonomyId,
      source_domain: newRuleDomain.trim() || undefined,
      confidence: 1.0,
      match_method: 'manual',
    })
  }

  const mappingsList = mappingsData?.items || []

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
            <TagIcon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
              AI Product Catalog Categorization & Taxonomy Auto-Mapper
              <Badge variant="primary">Automated Intelligence</Badge>
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Normalize raw scraped breadcrumbs and classify catalog products into Google Shopping, Amazon, or Shopify taxonomies
            </p>
          </div>
        </div>
      }
      size="6xl"
    >
      <div className="space-y-5">
        {/* Top Controls: Standard Selector & Coverage Metrics */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 p-4 rounded-xl bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700/80">
          {/* Taxonomy Standard Picker */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
              Target Standard Taxonomy
            </label>
            <select
              value={activeTaxonomyId}
              onChange={(e) => setSelectedTaxonomyId(Number(e.target.value))}
              className="w-full text-xs font-semibold rounded-lg border-gray-300 dark:border-gray-700 dark:bg-gray-900 dark:text-white py-2 px-2.5 focus:ring-indigo-500 focus:border-indigo-500"
            >
              {standards.map((std) => (
                <option key={std.id} value={std.id}>
                  {std.display_name} ({std.node_count || 0} categories)
                </option>
              ))}
            </select>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              {activeStandard?.description || 'Standard classification tree'}
            </p>
          </div>

          {/* Metric 1: Coverage */}
          <div className="p-3 bg-white dark:bg-gray-900/80 rounded-lg border border-gray-200 dark:border-gray-800">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                Catalog Coverage
              </span>
              <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400">
                {summary?.coverage_percentage || 0}%
              </span>
            </div>
            <div className="mt-2 w-full bg-gray-100 dark:bg-gray-800 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-indigo-600 h-full rounded-full transition-all duration-500"
                style={{ width: `${summary?.coverage_percentage || 0}%` }}
              />
            </div>
            <div className="mt-1 flex justify-between text-[11px] text-gray-500">
              <span>{summary?.total_mapped || 0} Mapped</span>
              <span>{summary?.unmapped_products || 0} Unmapped</span>
            </div>
          </div>

          {/* Metric 2: Confidence Health */}
          <div className="p-3 bg-white dark:bg-gray-900/80 rounded-lg border border-gray-200 dark:border-gray-800">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                Confidence Breakdown
              </span>
              <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                {summary?.high_confidence_count || 0} High (≥80%)
              </span>
            </div>
            <div className="mt-2.5 flex items-center gap-2 text-[11px]">
              <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400">
                ● {summary?.high_confidence_count || 0} High
              </span>
              <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
                ● {summary?.needs_review_count || 0} Needs Review
              </span>
            </div>
          </div>

          {/* Metric 3: Verification Count */}
          <div className="p-3 bg-white dark:bg-gray-900/80 rounded-lg border border-gray-200 dark:border-gray-800">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                Verified & Approved
              </span>
              <CheckCircleIcon className="w-4 h-4 text-emerald-500" />
            </div>
            <div className="mt-1">
              <div className="text-xl font-bold text-gray-900 dark:text-white">
                {summary?.total_verified || 0}
              </div>
              <p className="text-[11px] text-gray-500">Human-verified overrides</p>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-gray-200 dark:border-gray-800 gap-6">
          <button
            onClick={() => setActiveTab('review')}
            className={cn(
              'pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-1.5',
              activeTab === 'review'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'
            )}
          >
            <CheckCircleIcon className="w-4 h-4" />
            Review & Verify Mappings
          </button>
          <button
            onClick={() => setActiveTab('batch')}
            className={cn(
              'pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-1.5',
              activeTab === 'batch'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'
            )}
          >
            <SparklesIcon className="w-4 h-4" />
            Run Auto-Categorizer
          </button>
          <button
            onClick={() => setActiveTab('rules')}
            className={cn(
              'pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-1.5',
              activeTab === 'rules'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'
            )}
          >
            <AdjustmentsHorizontalIcon className="w-4 h-4" />
            Mapping Rules ({rules.length})
          </button>
          <button
            onClick={() => setActiveTab('tree')}
            className={cn(
              'pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-1.5',
              activeTab === 'tree'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'
            )}
          >
            <FolderIcon className="w-4 h-4" />
            Taxonomy Tree Explorer
          </button>
        </div>

        {/* Tab 1: Review & Verify Mappings */}
        {activeTab === 'review' && (
          <div className="space-y-4">
            {/* Filter Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800/40 border border-gray-200 dark:border-gray-800">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                  Filter by Confidence:
                </span>
                <div className="flex items-center bg-white dark:bg-gray-900 rounded-lg p-0.5 border border-gray-200 dark:border-gray-700">
                  <button
                    onClick={() => setConfidenceFilter('all')}
                    className={cn(
                      'px-2.5 py-1 rounded text-xs font-medium transition-colors',
                      confidenceFilter === 'all'
                        ? 'bg-indigo-600 text-white'
                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900'
                    )}
                  >
                    All Mapped
                  </button>
                  <button
                    onClick={() => setConfidenceFilter('review')}
                    className={cn(
                      'px-2.5 py-1 rounded text-xs font-medium transition-colors',
                      confidenceFilter === 'review'
                        ? 'bg-amber-600 text-white'
                        : 'text-amber-600 dark:text-amber-400 hover:text-amber-700'
                    )}
                  >
                    Needs Review (&lt;80%)
                  </button>
                  <button
                    onClick={() => setConfidenceFilter('high')}
                    className={cn(
                      'px-2.5 py-1 rounded text-xs font-medium transition-colors',
                      confidenceFilter === 'high'
                        ? 'bg-emerald-600 text-white'
                        : 'text-emerald-600 dark:text-emerald-400 hover:text-emerald-700'
                    )}
                  >
                    High Confidence (≥80%)
                  </button>
                </div>
              </div>

              <Button
                variant="outline"
                size="sm"
                icon={ArrowPathIcon}
                onClick={() => refetchMappings()}
                isLoading={isLoadingMappings}
              >
                Refresh Mappings
              </Button>
            </div>

            {/* Mappings Table */}
            {isLoadingMappings ? (
              <div className="py-16 text-center text-gray-500">
                <ArrowPathIcon className="w-8 h-8 animate-spin mx-auto mb-2 text-indigo-500" />
                <p className="text-sm">Loading taxonomy mappings...</p>
              </div>
            ) : mappingsList.length === 0 ? (
              <div className="py-16 text-center border-2 border-dashed border-gray-200 dark:border-gray-800 rounded-xl">
                <TagIcon className="w-10 h-10 mx-auto text-gray-400 mb-2" />
                <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                  No products classified in this taxonomy yet
                </h4>
                <p className="text-xs text-gray-500 max-w-sm mx-auto mt-1 mb-4">
                  Run the batch auto-categorizer to automatically classify products into {activeStandard?.display_name}.
                </p>
                <Button variant="primary" size="sm" onClick={() => setActiveTab('batch')}>
                  Run Auto-Categorizer
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto border border-gray-200 dark:border-gray-800 rounded-xl">
                <table className="w-full text-left text-xs divide-y divide-gray-200 dark:divide-gray-800">
                  <thead className="bg-gray-50 dark:bg-gray-800/60 font-semibold text-gray-600 dark:text-gray-300">
                    <tr>
                      <th className="px-3 py-3">Product</th>
                      <th className="px-3 py-3">Original Category / Breadcrumb</th>
                      <th className="px-3 py-3">Standard Mapped Taxonomy</th>
                      <th className="px-3 py-3 text-center">Confidence</th>
                      <th className="px-3 py-3 text-center">Method</th>
                      <th className="px-3 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-800 bg-white dark:bg-gray-900">
                    {mappingsList.map((m) => {
                      const prod = m.product || {}
                      const confPct = Math.round((m.confidence || 0) * 100)
                      const isEditing = editingMappingId === m.id

                      return (
                        <tr
                          key={m.id}
                          className="hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors"
                        >
                          {/* Product info */}
                          <td className="px-3 py-3 max-w-[220px]">
                            <div className="font-semibold text-gray-900 dark:text-white truncate" title={prod.name}>
                              {prod.name}
                            </div>
                            <div className="flex items-center gap-2 text-[11px] text-gray-500 mt-0.5">
                              {prod.source_domain && <span>{prod.source_domain}</span>}
                              {prod.brand && <span className="font-medium text-gray-600 dark:text-gray-400">· {prod.brand}</span>}
                              {prod.price && <span className="text-emerald-600 font-semibold">· ${prod.price}</span>}
                            </div>
                          </td>

                          {/* Scraped Breadcrumb */}
                          <td className="px-3 py-3 text-gray-600 dark:text-gray-400 max-w-[180px]">
                            <div className="truncate text-[11px] font-mono bg-gray-50 dark:bg-gray-800 px-2 py-1 rounded" title={prod.original_category || 'None'}>
                              {prod.original_category || '—'}
                            </div>
                          </td>

                          {/* Mapped Category */}
                          <td className="px-3 py-3 max-w-[260px]">
                            {isEditing ? (
                              <div className="flex items-center gap-1.5">
                                <input
                                  type="text"
                                  value={customCategoryInput}
                                  onChange={(e) => setCustomCategoryInput(e.target.value)}
                                  className="w-full text-xs py-1 px-2 rounded border border-indigo-400 dark:bg-gray-800 dark:text-white focus:outline-none"
                                  placeholder="e.g. Electronics > Audio > Headphones"
                                />
                                <button
                                  onClick={() => handleVerify(m.product_id, customCategoryInput)}
                                  className="p-1 rounded bg-emerald-600 text-white hover:bg-emerald-700"
                                  title="Save override"
                                >
                                  <CheckIcon className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => setEditingMappingId(null)}
                                  className="p-1 rounded bg-gray-300 dark:bg-gray-700 text-gray-700 dark:text-gray-200"
                                  title="Cancel"
                                >
                                  <XMarkIcon className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            ) : (
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-indigo-700 dark:text-indigo-400 text-xs">
                                  {m.category_path}
                                </span>
                                {m.is_verified && (
                                  <Badge variant="success" size="sm" className="text-[10px] py-0 px-1">
                                    Verified
                                  </Badge>
                                )}
                              </div>
                            )}
                            {m.notes && !isEditing && (
                              <p className="text-[10px] text-gray-400 mt-0.5 truncate" title={m.notes}>
                                ℹ {m.notes}
                              </p>
                            )}
                          </td>

                          {/* Confidence */}
                          <td className="px-3 py-3 text-center">
                            <span
                              className={cn(
                                'inline-block px-2 py-0.5 rounded-full text-[11px] font-bold',
                                confPct >= 80
                                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400'
                                  : confPct >= 60
                                  ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-400'
                                  : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400'
                              )}
                            >
                              {confPct}%
                            </span>
                          </td>

                          {/* Match Method */}
                          <td className="px-3 py-3 text-center">
                            <span className="text-[11px] text-gray-500 font-mono">
                              {m.match_method}
                            </span>
                          </td>

                          {/* Actions */}
                          <td className="px-3 py-3 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              {/* Verify Button */}
                              {!m.is_verified && (
                                <button
                                  onClick={() => handleVerify(m.product_id, m.category_path)}
                                  className="px-2 py-1 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:hover:bg-emerald-900/60 dark:text-emerald-300 font-medium text-[11px] transition-colors"
                                  title="Approve Category"
                                >
                                  ✓ Approve
                                </button>
                              )}

                              {/* Manual Override Edit */}
                              <button
                                onClick={() => {
                                  setEditingMappingId(m.id)
                                  setCustomCategoryInput(m.category_path)
                                }}
                                className="px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 text-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-300 font-medium text-[11px] transition-colors"
                                title="Edit or override category"
                              >
                                Edit
                              </button>

                              {/* Ask Gemini AI */}
                              <button
                                onClick={() => handleAskAi(m.product_id)}
                                disabled={isClassifyingAiId === m.product_id}
                                className="px-2 py-1 rounded bg-indigo-50 hover:bg-indigo-100 text-indigo-700 dark:bg-indigo-950/40 dark:hover:bg-indigo-900/60 dark:text-indigo-300 font-medium text-[11px] inline-flex items-center gap-1 transition-colors"
                                title="Re-classify with Gemini AI Zero-Shot"
                              >
                                <SparklesIcon className={cn('w-3 h-3', isClassifyingAiId === m.product_id && 'animate-spin')} />
                                AI
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
          </div>
        )}

        {/* Tab 2: Run Auto-Categorizer */}
        {activeTab === 'batch' && (
          <div className="space-y-4 max-w-2xl mx-auto py-2">
            <div className="p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800">
              <div className="flex items-start gap-3">
                <SparklesIcon className="w-5 h-5 text-indigo-600 mt-0.5 shrink-0" />
                <div>
                  <h4 className="text-sm font-bold text-indigo-950 dark:text-indigo-200">
                    Automated Catalog Categorization Engine
                  </h4>
                  <p className="text-xs text-indigo-800 dark:text-indigo-300 mt-1 leading-relaxed">
                    This process maps products against <strong>{activeStandard?.display_name}</strong> using multi-tier intelligence:
                  </p>
                  <ul className="text-xs text-indigo-800 dark:text-indigo-300 list-disc list-inside mt-2 space-y-1">
                    <li>Predefined translation rules for store breadcrumbs (exact match)</li>
                    <li>Token Jaccard keyword overlap and Levenshtein title similarity</li>
                    <li>Zero-shot Google Gemini deep learning reasoning for ambiguous products</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="space-y-4 p-5 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
              {/* Batch Limit */}
              <div>
                <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                  Products to Process
                </label>
                <div className="mt-1 flex items-center gap-3">
                  {[25, 50, 100, 250].map((num) => (
                    <button
                      key={num}
                      type="button"
                      onClick={() => setBatchLimit(num)}
                      className={cn(
                        'px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all',
                        batchLimit === num
                          ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                          : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-700'
                      )}
                    >
                      {num} Products
                    </button>
                  ))}
                </div>
              </div>

              {/* Source Domain Filter */}
              <div>
                <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                  Scope by Store Domain (Optional)
                </label>
                <input
                  type="text"
                  value={filterDomain}
                  onChange={(e) => setFilterDomain(e.target.value)}
                  placeholder="e.g. walmart.com, amazon.com (Leave blank for all stores)"
                  className="mt-1 w-full text-xs rounded-lg border-gray-300 dark:border-gray-700 dark:bg-gray-900 dark:text-white py-2 px-3 focus:ring-indigo-500"
                />
              </div>

              {/* Overwrite Option */}
              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="overwriteExisting"
                  checked={overwriteExisting}
                  onChange={(e) => setOverwriteExisting(e.target.checked)}
                  className="rounded text-indigo-600 border-gray-300 focus:ring-indigo-500"
                />
                <label htmlFor="overwriteExisting" className="text-xs text-gray-700 dark:text-gray-300 cursor-pointer">
                  Re-classify products that already have a mapping (preserves human-verified overrides)
                </label>
              </div>

              <div className="pt-3">
                <Button
                  variant="primary"
                  className="w-full justify-center"
                  icon={SparklesIcon}
                  onClick={handleRunBatch}
                  isLoading={autoCategorizeMutation.isPending}
                >
                  {autoCategorizeMutation.isPending ? 'Categorizing Products...' : 'Start Auto-Categorization'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Mapping Rules */}
        {activeTab === 'rules' && (
          <div className="space-y-4">
            {/* Create Rule Form */}
            <form
              onSubmit={handleCreateRule}
              className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/40 space-y-3"
            >
              <h4 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5">
                <PlusIcon className="w-3.5 h-3.5 text-indigo-500" />
                Add Translation Mapping Rule
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-gray-600 dark:text-gray-400">
                    Source Breadcrumb / Category
                  </label>
                  <input
                    type="text"
                    value={newRuleSource}
                    onChange={(e) => setNewRuleSource(e.target.value)}
                    placeholder="e.g. Personal Audio / Over-Ear"
                    className="w-full text-xs rounded-lg border-gray-300 dark:border-gray-700 dark:bg-gray-900 dark:text-white py-1.5 px-2.5 mt-1"
                    required
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-gray-600 dark:text-gray-400">
                    Target Standard Path ({activeStandard?.display_name})
                  </label>
                  <input
                    type="text"
                    value={newRuleTarget}
                    onChange={(e) => setNewRuleTarget(e.target.value)}
                    placeholder="e.g. Electronics > Audio > Headphones"
                    className="w-full text-xs rounded-lg border-gray-300 dark:border-gray-700 dark:bg-gray-900 dark:text-white py-1.5 px-2.5 mt-1"
                    required
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-gray-600 dark:text-gray-400">
                    Domain Scoping (Optional)
                  </label>
                  <div className="flex items-center gap-2 mt-1">
                    <input
                      type="text"
                      value={newRuleDomain}
                      onChange={(e) => setNewRuleDomain(e.target.value)}
                      placeholder="e.g. target.com or global"
                      className="w-full text-xs rounded-lg border-gray-300 dark:border-gray-700 dark:bg-gray-900 dark:text-white py-1.5 px-2.5"
                    />
                    <Button
                      type="submit"
                      variant="primary"
                      size="sm"
                      isLoading={createRuleMutation.isPending}
                    >
                      Add
                    </Button>
                  </div>
                </div>
              </div>
            </form>

            {/* Rules Table */}
            <div className="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
              <table className="w-full text-left text-xs divide-y divide-gray-200 dark:divide-gray-800">
                <thead className="bg-gray-50 dark:bg-gray-800/60 font-semibold text-gray-600 dark:text-gray-300">
                  <tr>
                    <th className="px-3 py-3">Source Store</th>
                    <th className="px-3 py-3">Source Breadcrumb Pattern</th>
                    <th className="px-3 py-3">Target Standard Category</th>
                    <th className="px-3 py-3 text-center">Confidence</th>
                    <th className="px-3 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800 bg-white dark:bg-gray-900">
                  {rules.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-gray-400">
                        No custom mapping rules defined for this standard yet.
                      </td>
                    </tr>
                  ) : (
                    rules.map((r) => (
                      <tr key={r.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/40">
                        <td className="px-3 py-2.5 font-mono text-[11px] text-gray-500">
                          {r.source_domain || 'Global (All Stores)'}
                        </td>
                        <td className="px-3 py-2.5 font-medium text-gray-900 dark:text-white">
                          {r.source_category_path}
                        </td>
                        <td className="px-3 py-2.5 text-indigo-600 dark:text-indigo-400 font-semibold">
                          {r.target_category_path}
                        </td>
                        <td className="px-3 py-2.5 text-center">
                          <span className="font-bold text-emerald-600">
                            {Math.round((r.confidence || 1) * 100)}%
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          <button
                            onClick={() => deleteRuleMutation.mutate(r.id)}
                            className="p-1 rounded text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
                            title="Delete rule"
                          >
                            <TrashIcon className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 4: Taxonomy Tree Explorer */}
        {activeTab === 'tree' && (
          <div className="space-y-3">
            <p className="text-xs text-gray-500">
              Browsing category tree for <strong>{activeStandard?.display_name}</strong> ({treeNodes.length} nodes)
            </p>
            <div className="max-h-96 overflow-y-auto border border-gray-200 dark:border-gray-800 rounded-xl divide-y divide-gray-100 dark:divide-gray-800 bg-white dark:bg-gray-900 p-2">
              {treeNodes.map((n) => (
                <div
                  key={n.id}
                  className="py-1.5 px-3 hover:bg-gray-50 dark:hover:bg-gray-800/60 rounded flex items-center justify-between text-xs"
                  style={{ paddingLeft: `${(n.level || 1) * 16}px` }}
                >
                  <span className="font-medium text-gray-800 dark:text-gray-200">
                    {n.level > 1 && <span className="text-gray-400 mr-1.5">↳</span>}
                    {n.name}
                  </span>
                  <div className="flex items-center gap-2">
                    {n.code && (
                      <span className="text-[10px] font-mono text-gray-400 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">
                        #{n.code}
                      </span>
                    )}
                    <span className="text-[11px] text-gray-400 truncate max-w-[200px]" title={n.full_path}>
                      {n.full_path}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <ModalFooter>
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </ModalFooter>
    </Modal>
  )
}
