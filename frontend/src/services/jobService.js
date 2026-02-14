import { apiGet, apiPost, apiDelete } from './api'

export const jobService = {
  /**
   * List all jobs with pagination
  */

  // const params = {
  // page,
  // page_size,
  // ...(search && { search }),
  // ...(status && { status }),
  // ...(domain && { domain }),
  // },


  async listJobs(params = {page, page_size, ...(search && { search }),  ...(status && { status }),  ...(domain && { domain }),})
      {
    // const params = {
    //     page,
    //     page_size,
    //     ...(search && { search }),
    //     ...(status && { status }),
    //     ...(domain && { domain }),
    //   }
      console.log("params ", params)
    const response = await apiGet('/jobs/', params)
    return response
  },

  /**
   * Get job statistics
   */
  async getJobStats() {
    const response = await apiGet('/jobs/statistics')
    return response
  },

  /**
   * Get single job details
   */
  async getJob(jobId) {
    const response = await apiGet(`/jobs/${jobId}`)
    return response
  },

  /**
   * Get job logs
   */
  async getJobLogs(jobId, limit = 100) {
    const response = await apiGet(`/jobs/${jobId}/logs`, { limit })
    return response
  },

  /**
   * Pause a running job
   */
  async pauseJob(jobId) {
    const response = await apiPost(`/jobs/${jobId}/pause`)
    return response
  },

  /**
   * Resume a paused job
   */
  async resumeJob(jobId) {
    const response = await apiPost(`/jobs/${jobId}/resume`)
    return response
  },

  /**
   * Cancel a job
   */
  async cancelJob(jobId) {
    const response = await apiPost(`/jobs/${jobId}/cancel`)
    return response
  },

  /**
   * Retry a failed job
   */
  async retryJob(jobId) {
    const response = await apiPost(`/jobs/${jobId}/retry`)
    return response
  },

  /**
   * Delete a job
   */
  async deleteJob(jobId) {
    const response = await apiDelete(`/jobs/${jobId}`)
    return response
  },

  /**
   * Get products for a job
   */
  async getJobProducts(jobId, params = {}) {
    const response = await apiGet(`/jobs/${jobId}/products`, params)
    return response
  },
}

export default jobService