import api from './api'

export const inventoryService = {
  recordStockObservation: async (productId, payload) => {
    const res = await api.post(`/products/${productId}/stock`, payload)
    return res.data
  },

  getInventoryForecast: async (productId) => {
    const res = await api.get(`/products/${productId}/inventory-forecast`)
    return res.data
  },

  getStockHistory: async (productId, limit = 50) => {
    const res = await api.get(`/products/${productId}/stock-history?limit=${limit}`)
    return res.data
  },

  getStockoutOpportunities: async (params = {}) => {
    const query = new URLSearchParams()
    if (params.domain) query.append('domain', params.domain)
    if (params.risk_level) query.append('risk_level', params.risk_level)
    const res = await api.get(`/inventory/opportunities?${query.toString()}`)
    return res.data
  },
}

export default inventoryService
