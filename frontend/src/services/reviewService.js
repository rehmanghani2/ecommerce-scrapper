import api from './api'

export const reviewService = {
  getProductReviews: async (productId, params = {}) => {
    const query = new URLSearchParams()
    if (params.sentiment) query.append('sentiment', params.sentiment)
    if (params.limit) query.append('limit', params.limit)
    if (params.offset) query.append('offset', params.offset)
    const res = await api.get(`/products/${productId}/reviews?${query.toString()}`)
    return res.data
  },

  ingestReviews: async (productId, payload) => {
    const res = await api.post(`/products/${productId}/reviews`, payload)
    return res.data
  },

  analyzeSentiment: async (productId, options = {}) => {
    const res = await api.post(`/products/${productId}/sentiment/analyze`, {
      use_ai: options.use_ai ?? true,
      api_key: options.api_key || undefined,
    })
    return res.data
  },

  getProductSentiment: async (productId) => {
    const res = await api.get(`/products/${productId}/sentiment`)
    return res.data
  },

  getDomainWeaknesses: async (domain) => {
    const res = await api.get(`/reviews/domain/${domain}/weaknesses`)
    return res.data
  },
}

export default reviewService
