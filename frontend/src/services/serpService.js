import api from './api'

export const serpService = {
  getKeywords: async (params = {}) => {
    const res = await api.get('/serp/keywords', { params })
    return res.data
  },

  createKeyword: async (payload) => {
    const res = await api.post('/serp/keywords', payload)
    return res.data
  },

  getKeywordDetail: async (keywordId) => {
    const res = await api.get(`/serp/keywords/${keywordId}`)
    return res.data
  },

  recordSnapshot: async (keywordId, payload) => {
    const res = await api.post(`/serp/keywords/${keywordId}/snapshot`, payload)
    return res.data
  },

  deleteKeyword: async (keywordId) => {
    const res = await api.delete(`/serp/keywords/${keywordId}`)
    return res.data
  },

  getProductRankings: async (productId) => {
    const res = await api.get(`/serp/product/${productId}`)
    return res.data
  },

  getInsights: async () => {
    const res = await api.get('/serp/insights')
    return res.data
  },
}

export default serpService
