import axios from 'axios'
import toast from 'react-hot-toast'
import { API_BASE_URL, API_PREFIX, STORAGE_KEYS } from '../utils/constants'

// Create axios instance
const api = axios.create({
  baseURL: `${API_BASE_URL}${API_PREFIX}`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    const { response } = error

    if (response) {
      switch (response.status) {
        case 401:
          // Unauthorized - clear auth and redirect
          localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN)
          localStorage.removeItem(STORAGE_KEYS.USER)
          
          // Only redirect if not already on login page
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login'
          }
          break

        case 403:
          toast.error('You do not have permission to perform this action')
          break

        case 404:
          // Don't show toast for 404, let the component handle it
          break

        case 422:
          // Validation error
          const validationErrors = response.data?.detail
          if (Array.isArray(validationErrors)) {
            validationErrors.forEach((err) => {
              toast.error(err.msg || 'Validation error')
            })
          } else if (typeof validationErrors === 'string') {
            toast.error(validationErrors)
          }
          break

        case 429:
          toast.error('Too many requests. Please slow down.')
          break

        case 500:
        case 502:
        case 503:
          toast.error('Server error. Please try again later.')
          break

        default:
          const message = response.data?.message || response.data?.detail || 'An error occurred'
          toast.error(message)
      }
    } else if (error.request) {
      // Request was made but no response
      toast.error('Unable to connect to server. Please check your connection.')
    } else {
      // Error setting up request
      toast.error('An unexpected error occurred')
    }

    return Promise.reject(error)
  }
)

// API methods
export const apiGet = async (url, params = {}) => {
  const response = await api.get(url, { params })
  return response.data
}

export const apiPost = async (url, data = {}) => {
  const response = await api.post(url, data)
  return response.data
}

export const apiPut = async (url, data = {}) => {
  const response = await api.put(url, data)
  return response.data
}

export const apiPatch = async (url, data = {}) => {
  const response = await api.patch(url, data)
  return response.data
}

export const apiDelete = async (url) => {
  const response = await api.delete(url)
  return response.data
}

// File download
export const apiDownload = async (url, filename) => {
  const response = await api.get(url, {
    responseType: 'blob',
  })
  
  const blob = new Blob([response.data])
  const downloadUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(downloadUrl)
  
  return response
}

export default api