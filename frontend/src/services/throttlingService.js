import api from './api'

export const throttlingService = {
  getDomains: async () => {
    const res = await api.get('/throttling/domains')
    return res.data
  },

  getDomainDetail: async (domain) => {
    const res = await api.get(`/throttling/domains/${domain}`)
    return res.data
  },

  upsertDomain: async (payload) => {
    const res = await api.post('/throttling/domains', payload)
    return res.data
  },

  resetDomain: async (domain) => {
    const res = await api.post(`/throttling/domains/${domain}/reset`)
    return res.data
  },

  deleteDomain: async (domain) => {
    const res = await api.delete(`/throttling/domains/${domain}`)
    return res.data
  },

  simulateBackoff: async (payload) => {
    const res = await api.post('/throttling/simulate', payload)
    return res.data
  },
}

export default throttlingService
