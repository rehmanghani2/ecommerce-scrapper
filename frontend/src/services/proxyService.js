import api from './api'

export const proxyService = {
  getProxies: async (params = {}) => {
    const query = new URLSearchParams()
    if (params.status && params.status !== 'all') query.append('status', params.status)
    if (params.protocol) query.append('protocol', params.protocol)
    if (params.search) query.append('search', params.search)
    const res = await api.get(`/proxies?${query.toString()}`)
    return res.data
  },

  importProxies: async (payload) => {
    const res = await api.post('/proxies', payload)
    return res.data
  },

  getDomainMetrics: async () => {
    const res = await api.get('/proxies/domain-metrics')
    return res.data
  },

  testProxy: async (proxyId, targetUrl) => {
    const res = await api.post(`/proxies/${proxyId}/test`, {
      target_url: targetUrl || 'https://httpbin.org/ip',
    })
    return res.data
  },

  testAllProxies: async (targetUrl) => {
    const res = await api.post('/proxies/test-all', {
      target_url: targetUrl || 'https://httpbin.org/ip',
    })
    return res.data
  },

  toggleBlacklist: async (proxyId, isBanned, reason = null) => {
    const res = await api.post(`/proxies/${proxyId}/blacklist`, {
      is_banned: isBanned,
      reason,
    })
    return res.data
  },

  updateProxy: async (proxyId, updates) => {
    const res = await api.put(`/proxies/${proxyId}`, updates)
    return res.data
  },

  deleteProxy: async (proxyId) => {
    const res = await api.delete(`/proxies/${proxyId}`)
    return res.data
  },

  resetMetrics: async () => {
    const res = await api.post('/proxies/reset-metrics')
    return res.data
  },
}

export default proxyService
