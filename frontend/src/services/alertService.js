/**
 * Alert Service for Price Drop & Stock Notifications.
 * Communicates with backend endpoints to manage Telegram, Slack, Discord, and Webhook alerts.
 */

import { apiGet, apiPost, apiDelete } from './api'

export const alertService = {
  /**
   * List all configured alert channels
   */
  async getConfigs() {
    return await apiGet('/alerts/configs')
  },

  /**
   * Save or update an alert channel config
   */
  async saveConfig(data) {
    return await apiPost('/alerts/configs', data)
  },

  /**
   * Delete an alert channel config
   */
  async deleteConfig(id) {
    return await apiDelete(`/alerts/configs/${id}`)
  },

  /**
   * Send a sample test alert to verify credentials
   */
  async testChannel(channel, credentials) {
    return await apiPost('/alerts/test', { channel, credentials })
  },

  /**
   * Retrieve recent triggered alert logs
   */
  async getLogs(limit = 50) {
    return await apiGet(`/alerts/logs?limit=${limit}`)
  },
}

export default alertService
