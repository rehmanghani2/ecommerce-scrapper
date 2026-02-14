import { apiGet, apiPost, apiDelete, apiDownload } from './api'

export const exportService = {
  /**
   * Create export for a job
   */
  async createExport(jobId, format = 'csv') {
    const response = await apiPost(`/exports/${jobId}`, null, {
      params: { format },
    })
    return response
  },

  /**
   * Download export file
   */
  async downloadExport(filename) {
    await apiDownload(`/exports/download/${filename}`, filename)
  },

  /**
   * List all exports
   */
  async listExports() {
    const response = await apiGet('/exports/list')
    return response.exports
  },

  /**
   * Delete an export
   */
  async deleteExport(filename) {
    const response = await apiDelete(`/exports/${filename}`)
    return response
  },
}

export default exportService