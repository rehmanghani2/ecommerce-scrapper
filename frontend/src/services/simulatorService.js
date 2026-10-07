import api from './api'

export const simulatorService = {
  simulate: async (payload) => {
    const res = await api.post('/simulator/simulate', payload)
    return res.data
  },

  saveScenario: async (payload) => {
    const res = await api.post('/simulator/scenarios', payload)
    return res.data
  },

  getScenarios: async (productId) => {
    const res = await api.get(`/simulator/scenarios/${productId}`)
    return res.data
  },

  deleteScenario: async (scenarioId) => {
    const res = await api.delete(`/simulator/scenarios/${scenarioId}`)
    return res.data
  },
}

export default simulatorService
