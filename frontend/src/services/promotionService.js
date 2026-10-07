import api from './api'

export const promotionService = {
  getActivePromotions: async (params = {}) => {
    const res = await api.get('/promotions/active', { params })
    return res.data
  },

  getProductPromotions: async (productId, activeOnly = false) => {
    const res = await api.get(`/promotions/product/${productId}`, {
      params: { active_only: activeOnly },
    })
    return res.data
  },

  createPromotion: async (productId, payload) => {
    const res = await api.post(`/promotions/product/${productId}`, payload)
    return res.data
  },

  detectPromotions: async (payload) => {
    const res = await api.post('/promotions/detect', payload)
    return res.data
  },

  togglePromotion: async (promotionId) => {
    const res = await api.post(`/promotions/${promotionId}/toggle`)
    return res.data
  },

  deletePromotion: async (promotionId) => {
    const res = await api.delete(`/promotions/${promotionId}`)
    return res.data
  },

  getPromotionInsights: async (domain = null) => {
    const params = domain ? { domain } : {}
    const res = await api.get('/promotions/insights', { params })
    return res.data
  },
}

export default promotionService
