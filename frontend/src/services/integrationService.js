import api from './api'

export const integrationService = {
  // Configs
  getConfigs: async () => {
    const response = await api.get('/integrations/configs')
    return response.data
  },

  saveConfig: async (configData) => {
    const response = await api.post('/integrations/configs', configData)
    return response.data
  },

  deleteConfig: async (configId) => {
    const response = await api.delete(`/integrations/configs/${configId}`)
    return response.data
  },

  // Test connection
  testConnection: async (platform, credentials) => {
    const response = await api.post('/integrations/test', {
      platform,
      credentials,
    })
    return response.data
  },

  // 1-Click Sync
  syncProducts: async ({ platform, productIds, jobId, publishStatus = 'draft', configOverride = null }) => {
    const response = await api.post('/integrations/sync', {
      platform,
      product_ids: productIds,
      job_id: jobId,
      publish_status: publishStatus,
      config_override: configOverride,
    })
    return response.data
  },

  // Audit Logs
  getSyncLogs: async (limit = 20) => {
    const response = await api.get('/integrations/logs', {
      params: { limit },
    })
    return response.data
  },

  // Download Store CSV
  downloadStoreCsv: async (platform, { jobId, productIds } = {}) => {
    const params = new URLSearchParams({ platform })
    if (jobId) params.append('job_id', jobId)
    if (productIds && productIds.length > 0) params.append('product_ids', productIds.join(','))

    const response = await api.get(`/integrations/export-csv?${params.toString()}`, {
      responseType: 'blob',
    })

    const blob = new Blob([response.data], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${platform}_products_${Date.now()}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}

export default integrationService
