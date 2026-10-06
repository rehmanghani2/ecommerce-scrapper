import api from './api'

export const repricingService = {
  getRules: async () => {
    const res = await api.get('/repricing/rules')
    return res.data
  },

  createRule: async (data) => {
    const res = await api.post('/repricing/rules', data)
    return res.data
  },

  updateRule: async (id, data) => {
    const res = await api.put(`/repricing/rules/${id}`, data)
    return res.data
  },

  deleteRule: async (id) => {
    const res = await api.delete(`/repricing/rules/${id}`)
    return res.data
  },

  simulate: async (data) => {
    const res = await api.post('/repricing/simulate', data)
    return res.data
  },

  getLogs: async (limit = 50) => {
    const res = await api.get(`/repricing/logs?limit=${limit}`)
    return res.data
  },
}

export default repricingService
