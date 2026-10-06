import api from './api'

export const reportService = {
  getSchedules: async () => {
    const res = await api.get('/reports/schedules')
    return res.data
  },

  createSchedule: async (payload) => {
    const res = await api.post('/reports/schedules', payload)
    return res.data
  },

  deleteSchedule: async (scheduleId) => {
    const res = await api.delete(`/reports/schedules/${scheduleId}`)
    return res.data
  },

  triggerSchedule: async (scheduleId) => {
    const res = await api.post(`/reports/schedules/${scheduleId}/trigger`)
    return res.data
  },

  getPreviewHtmlUrl: (domain, days = 7) => {
    const base = api.defaults.baseURL || '/api/v1'
    const query = new URLSearchParams()
    if (domain) query.append('domain', domain)
    if (days) query.append('days', days)
    return `${base}/reports/preview?${query.toString()}`
  },

  getDownloadPdfUrl: (domain, days = 7) => {
    const base = api.defaults.baseURL || '/api/v1'
    const query = new URLSearchParams()
    if (domain) query.append('domain', domain)
    if (days) query.append('days', days)
    return `${base}/reports/download-pdf?${query.toString()}`
  },

  sendTestReport: async (payload) => {
    const res = await api.post('/reports/send-test', payload)
    return res.data
  },
}

export default reportService
