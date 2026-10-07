import React, { useState, useEffect, useCallback } from 'react'
import {
  CalculatorIcon,
  BoltIcon,
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  SparklesIcon,
  BookmarkSquareIcon,
  TrashIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import Modal from '@/components/Common/Modal'
import Button from '@/components/Common/Button'
import Card from '@/components/Common/Card'
import Spinner from '@/components/Common/Spinner'
import simulatorService from '@/services/simulatorService'

export default function PricingSimulatorModal({ product, isOpen, onClose }) {
  const currentPrice = Number(product?.price || product?.sale_price || 100)
  
  const [proposedPrice, setProposedPrice] = useState(currentPrice)
  const [cogs, setCogs] = useState(Math.round(currentPrice * 0.6))
  const [category, setCategory] = useState(product?.category || 'electronics')
  const [competitorPrice, setCompetitorPrice] = useState(currentPrice)

  const [simulation, setSimulation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [savedScenarios, setSavedScenarios] = useState([])
  const [scenarioName, setScenarioName] = useState('')
  const [saving, setSaving] = useState(false)

  const runSim = useCallback(async (newPrice, newCogs, newCat, newComp) => {
    if (!newPrice || newPrice <= 0) return
    try {
      setLoading(true)
      const data = await simulatorService.simulate({
        current_price: currentPrice,
        proposed_price: Number(newPrice),
        cogs: newCogs ? Number(newCogs) : undefined,
        category: newCat || 'general',
        competitor_price: newComp ? Number(newComp) : undefined,
      })
      setSimulation(data)
    } catch (err) {
      console.error('Simulation error:', err)
    } finally {
      setLoading(false)
    }
  }, [currentPrice])

  const fetchScenarios = useCallback(async () => {
    if (!product?.id) return
    try {
      const list = await simulatorService.getScenarios(product.id)
      setSavedScenarios(list || [])
    } catch (err) {
      console.error('Error fetching scenarios:', err)
    }
  }, [product?.id])

  useEffect(() => {
    if (isOpen && product) {
      const p = Number(product.price || product.sale_price || 100)
      setProposedPrice(p)
      setCogs(Math.round(p * 0.6))
      setCategory(product.category || 'electronics')
      setCompetitorPrice(p)
      runSim(p, Math.round(p * 0.6), product.category || 'electronics', p)
      fetchScenarios()
    }
  }, [isOpen, product, runSim, fetchScenarios])

  const handlePriceChange = (val) => {
    const num = Number(val)
    setProposedPrice(num)
    runSim(num, cogs, category, competitorPrice)
  }

  const handlePercentageQuickAdj = (pct) => {
    const updated = Math.round(currentPrice * (1 + pct / 100) * 100) / 100
    setProposedPrice(updated)
    runSim(updated, cogs, category, competitorPrice)
  }

  const handleSaveScenario = async (e) => {
    e.preventDefault()
    if (!product?.id) return
    try {
      setSaving(true)
      await simulatorService.saveScenario({
        product_id: product.id,
        scenario_name: scenarioName.trim() || `Proposed $${proposedPrice}`,
        current_price: currentPrice,
        proposed_price: proposedPrice,
        cogs: cogs,
        category: category,
        competitor_price: competitorPrice,
      })
      toast.success('Simulation scenario saved!')
      setScenarioName('')
      fetchScenarios()
    } catch (err) {
      toast.error('Failed to save scenario')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteScenario = async (id) => {
    try {
      await simulatorService.deleteScenario(id)
      toast.success('Scenario deleted')
      fetchScenarios()
    } catch (err) {
      toast.error('Failed to delete scenario')
    }
  }

  if (!product) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="AI Competitor Strategy & Pricing Simulator"
      size="xl"
    >
      <div className="space-y-5">
        {/* Header & Product Identity */}
        <div className="flex items-start justify-between pb-3 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white line-clamp-1">
              {product.name}
            </h3>
            <div className="text-xs text-gray-500 mt-0.5">
              Current Benchmark Price: <strong className="text-gray-900 dark:text-white">${currentPrice}</strong> • Store: <span className="capitalize">{product.source_domain || 'Competitor'}</span>
            </div>
          </div>
          {simulation?.optimal_sweet_spot_price && (
            <div className="text-right">
              <span className="text-[10px] uppercase font-semibold text-primary-600 dark:text-primary-400 block">AI Sweet Spot Price</span>
              <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
                ${simulation.optimal_sweet_spot_price}
              </span>
            </div>
          )}
        </div>

        {/* Interactive Pricing Controls */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-3.5 bg-gray-50 dark:bg-gray-800/60 rounded-xl border border-gray-200 dark:border-gray-700">
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Proposed Price ($):
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={proposedPrice}
              onChange={(e) => handlePriceChange(e.target.value)}
              className="w-full text-sm font-semibold px-2.5 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
            {/* Quick Adjustment Pills */}
            <div className="flex items-center gap-1 mt-1.5 flex-wrap">
              {[-10, -5, -2, 2, 5, 10].map((adj) => (
                <button
                  key={adj}
                  type="button"
                  onClick={() => handlePercentageQuickAdj(adj)}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100"
                >
                  {adj > 0 ? `+${adj}%` : `${adj}%`}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Unit Cost / COGS ($):
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={cogs}
              onChange={(e) => {
                const val = Number(e.target.value)
                setCogs(val)
                runSim(proposedPrice, val, category, competitorPrice)
              }}
              className="w-full text-sm font-semibold px-2.5 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            />
            <span className="text-[10px] text-gray-500 mt-1 block">
              Unit Margin: ${Math.round((proposedPrice - cogs) * 100) / 100} ({simulation?.proposed_margin_pct || 0}%)
            </span>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Category Elasticity:
            </label>
            <select
              value={category}
              onChange={(e) => {
                setCategory(e.target.value)
                runSim(proposedPrice, cogs, e.target.value, competitorPrice)
              }}
              className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            >
              <option value="electronics">Electronics (High, ε = -1.5)</option>
              <option value="apparel">Apparel & Fashion (ε = -1.2)</option>
              <option value="home">Home & Kitchen (ε = -1.1)</option>
              <option value="sports">Sports & Outdoors (ε = -1.3)</option>
              <option value="beauty">Beauty & Health (ε = -0.9)</option>
              <option value="groceries">Groceries (Inelastic, ε = -0.7)</option>
              <option value="general">General Merchandise (ε = -1.2)</option>
            </select>
            <span className="text-[10px] text-gray-500 mt-1 block">
              Demand Sensitivity: ε = {simulation?.elasticity || -1.2}
            </span>
          </div>
        </div>

        {/* Projected Simulation Metrics */}
        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center">
            <Spinner size="lg" />
            <p className="text-xs text-gray-500 mt-2">Running elasticity model & game-theory simulation...</p>
          </div>
        ) : simulation && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {/* Unit Sales Shift */}
              <Card className="p-3 border-l-4 border-l-sky-500">
                <div className="text-[11px] font-semibold text-sky-600 uppercase tracking-wider">Unit Sales Volume</div>
                <div className="mt-1 text-xl font-bold flex items-center gap-1 text-gray-900 dark:text-white">
                  {simulation.projected_unit_sales_change_pct >= 0 ? (
                    <ArrowTrendingUpIcon className="w-5 h-5 text-emerald-500" />
                  ) : (
                    <ArrowTrendingDownIcon className="w-5 h-5 text-rose-500" />
                  )}
                  {simulation.projected_unit_sales_change_pct > 0 ? '+' : ''}
                  {simulation.projected_unit_sales_change_pct}%
                </div>
                <div className="text-[10px] text-gray-400 mt-0.5">Estimated demand change</div>
              </Card>

              {/* Gross Profit Shift */}
              <Card className={`p-3 border-l-4 ${simulation.projected_profit_change_pct >= 0 ? 'border-l-emerald-500' : 'border-l-rose-500'}`}>
                <div className="text-[11px] font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">Gross Profit Shift</div>
                <div className={`mt-1 text-xl font-bold ${simulation.projected_profit_change_pct >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {simulation.projected_profit_change_pct > 0 ? '+' : ''}
                  {simulation.projected_profit_change_pct}%
                </div>
                <div className="text-[10px] text-gray-400 mt-0.5">Total dollar profit impact</div>
              </Card>

              {/* Break-Even Volume Multiplier */}
              <Card className="p-3 border-l-4 border-l-amber-500">
                <div className="text-[11px] font-semibold text-amber-600 uppercase tracking-wider">Break-Even Volume</div>
                <div className="mt-1 text-xl font-bold text-amber-600 dark:text-amber-400">
                  {simulation.break_even_volume_multiplier}x
                </div>
                <div className="text-[10px] text-gray-400 mt-0.5">
                  +{simulation.break_even_sales_increase_pct}% sales needed
                </div>
              </Card>

              {/* Competitor Price War Risk */}
              <Card className={`p-3 border-l-4 ${simulation.price_war_risk === 'high' ? 'border-l-rose-500' : simulation.price_war_risk === 'moderate' ? 'border-l-amber-500' : 'border-l-emerald-500'}`}>
                <div className="text-[11px] font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">Competitor Reaction</div>
                <div className="mt-1 text-xl font-bold text-gray-900 dark:text-white flex items-center gap-1">
                  <span>{simulation.competitor_reaction_probability}%</span>
                  <span className={`text-[11px] px-1.5 py-0.5 rounded font-semibold uppercase ${
                    simulation.price_war_risk === 'high' ? 'bg-rose-100 text-rose-700' : simulation.price_war_risk === 'moderate' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'
                  }`}>
                    {simulation.price_war_risk}
                  </span>
                </div>
                <div className="text-[10px] text-gray-400 mt-0.5">Price war trigger probability</div>
              </Card>
            </div>

            {/* Strategic AI Game-Theory Verdict */}
            <div className={`p-3.5 rounded-lg border text-xs leading-relaxed ${
              simulation.price_war_risk === 'high'
                ? 'bg-rose-50 border-rose-200 text-rose-900 dark:bg-rose-950/30 dark:border-rose-900 dark:text-rose-200'
                : simulation.projected_profit_change_pct >= 0
                ? 'bg-emerald-50 border-emerald-200 text-emerald-900 dark:bg-emerald-950/30 dark:border-emerald-900 dark:text-emerald-200'
                : 'bg-amber-50 border-amber-200 text-amber-900 dark:bg-amber-950/30 dark:border-amber-900 dark:text-amber-200'
            }`}>
              <div className="font-semibold text-sm mb-1 flex items-center gap-1.5">
                <SparklesIcon className="w-4 h-4 text-primary-600" />
                AI Game-Theory Synthesis & Recommendation
              </div>
              {simulation.strategic_verdict}
            </div>

            {/* Save Scenario Form */}
            <form onSubmit={handleSaveScenario} className="flex items-center gap-2 pt-1">
              <input
                type="text"
                placeholder="Scenario label (e.g. Black Friday 7% Under-Cut)"
                value={scenarioName}
                onChange={(e) => setScenarioName(e.target.value)}
                className="flex-1 text-xs px-2.5 py-1.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              />
              <Button type="submit" size="sm" variant="primary" disabled={saving}>
                <BookmarkSquareIcon className="w-3.5 h-3.5 mr-1" />
                {saving ? 'Saving...' : 'Save Scenario'}
              </Button>
            </form>
          </div>
        )}

        {/* Saved Scenarios History */}
        {savedScenarios.length > 0 && (
          <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300 mb-2">
              Saved Simulation Scenarios ({savedScenarios.length})
            </h4>
            <div className="space-y-1.5 max-h-36 overflow-y-auto">
              {savedScenarios.map((s) => (
                <div
                  key={s.id}
                  className="p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-900 dark:text-white">{s.scenario_name}</span>
                    <span className="text-gray-400">•</span>
                    <span className="text-gray-600 dark:text-gray-300">${s.proposed_price} ({s.price_change_percentage}%)</span>
                    <span className="text-gray-400">•</span>
                    <span className={s.projected_profit_change_pct >= 0 ? 'text-emerald-600 font-medium' : 'text-rose-600 font-medium'}>
                      Profit: {s.projected_profit_change_pct > 0 ? '+' : ''}{s.projected_profit_change_pct}%
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handlePriceChange(s.proposed_price)}
                      className="text-[10px] text-primary-600 font-medium hover:underline"
                    >
                      Load
                    </button>
                    <button
                      onClick={() => handleDeleteScenario(s.id)}
                      className="text-gray-400 hover:text-rose-600"
                    >
                      <TrashIcon className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-end pt-2 border-t border-gray-200 dark:border-gray-700">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  )
}
