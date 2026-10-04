import { apiGet, apiPost, apiPut, apiDelete } from './api'

export const scheduleService = {
  /**
   * List all scheduled jobs
   */
  async listSchedules() {
    const response = await apiGet('/schedules')
    return response
  },

  /**
   * Create a new recurring schedule
   */
  async createSchedule(data) {
    const response = await apiPost('/schedules', data)
    return response
  },

  /**
   * Update schedule settings or toggle active state
   */
  async updateSchedule(id, data) {
    const response = await apiPut(`/schedules/${id}`, data)
    return response
  },

  /**
   * Delete schedule
   */
  async deleteSchedule(id) {
    const response = await apiDelete(`/schedules/${id}`)
    return response
  },

  /**
   * Trigger an immediate run of a scheduled job
   */
  async runSchedule(id) {
    const response = await apiPost(`/schedules/${id}/run`)
    return response
  },
}
