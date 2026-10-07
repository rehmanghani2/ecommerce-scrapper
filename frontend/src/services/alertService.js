/**
 * Alert Service for Multi-Store Webhook & Slack/Discord Notification Dispatcher.
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
  async testChannel(channel, credentials, hmac_secret = null) {
    return await apiPost('/alerts/test', { channel, credentials, hmac_secret })
  },

  /**
   * Simulate outbound webhook payload with HMAC signature
   */
  async simulateWebhook(payload) {
    return await apiPost('/alerts/simulate-webhook', payload)
  },

  /**
   * Retrieve recent triggered alert logs with optional filtering
   */
  async getLogs(limit = 50, channel = '', event_type = '') {
    const params = new URLSearchParams({ limit: String(limit) })
    if (channel) params.append('channel', channel)
    if (event_type) params.append('event_type', event_type)
    return await apiGet(`/alerts/logs?${params.toString()}`)
  },
}

export default alertService
