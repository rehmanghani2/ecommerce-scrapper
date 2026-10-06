import api from './api'

export const matchingService = {
  compare: async (productA, productB, options = {}) => {
    const res = await api.post('/matching/compare', {
      product_a: productA,
      product_b: productB,
      threshold: options.threshold ?? 0.75,
      use_ai: options.use_ai ?? true,
      api_key: options.api_key || undefined,
    })
    return res.data
  },

  clusterJob: async (jobId, options = {}) => {
    const res = await api.post(`/matching/cluster-job/${jobId}`, {
      threshold: options.threshold ?? 0.75,
      use_ai: options.use_ai ?? false,
      api_key: options.api_key || undefined,
    })
    return res.data
  },

  clusterAll: async (options = {}) => {
    const res = await api.post('/matching/cluster-all', {
      threshold: options.threshold ?? 0.75,
      use_ai: options.use_ai ?? false,
      api_key: options.api_key || undefined,
    })
    return res.data
  },

  getClusters: async (params = {}) => {
    const query = new URLSearchParams()
    if (params.limit) query.append('limit', params.limit)
    if (params.offset) query.append('offset', params.offset)
    if (params.search) query.append('search', params.search)
    const res = await api.get(`/matching/clusters?${query.toString()}`)
    return res.data
  },

  getCluster: async (clusterId) => {
    const res = await api.get(`/matching/clusters/${clusterId}`)
    return res.data
  },

  uncluster: async (clusterId) => {
    const res = await api.delete(`/matching/clusters/${clusterId}`)
    return res.data
  },
}

export default matchingService
