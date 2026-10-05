import api from './api'

export const currencyService = {
  getRates: async () => {
    const res = await api.get('/currency/rates')
    return res.data
  },

  getSupportedCurrencies: async () => {
    const res = await api.get('/currency/supported')
    return res.data
  },

  convertPrice: async (data) => {
    const res = await api.post('/currency/convert', data)
    return res.data
  },

  normalizeJobProducts: async (jobId, targetCurrency) => {
    const res = await api.post(`/currency/normalize-job/${jobId}`, {
      target_currency: targetCurrency,
    })
    return res.data
  },
}

export default currencyService
