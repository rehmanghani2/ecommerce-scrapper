import api from './api'

export const buyboxService = {
  getProductBuyBox: async (productId) => {
    const res = await api.get(`/buybox/product/${productId}`)
    return res.data
  },

  evaluateWinProbability: async (productId, payload) => {
    const res = await api.post(`/buybox/product/${productId}/evaluate`, payload)
    return res.data
  },

  recordObservation: async (productId, payload) => {
    const res = await api.post(`/buybox/product/${productId}/observation`, payload)
    return res.data
  },

  getBuyBoxAlerts: async () => {
    const res = await api.get('/buybox/alerts')
    return res.data
  },
}

export default buyboxService
