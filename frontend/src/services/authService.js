import { apiGet, apiPost } from './api'
import { STORAGE_KEYS } from '../utils/constants'

export const authService = {
  /**
   * Login user
   */
  async login(username, password) {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    console.log("formData", formData)
    print("formData ",formData)
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/auth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    })
    console.log("Response", response)
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Login failed')
    }

    const data = await response.json()
    
    // Store token
    localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, data.access_token)
    
    // Get user info
    const user = await this.getCurrentUser()
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user))
    
    return { token: data.access_token, user }
  },

  /**
   * Register new user
   */
  async register(email, username, password, fullName = '') {
    const response = await apiPost('/auth/register', {
      email,
      username,
      password,
      full_name: fullName,
    })
    return response
  },

  /**
   * Logout user
   */
  logout() {
    localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN)
    localStorage.removeItem(STORAGE_KEYS.USER)
  },

  /**
   * Get current user info
   */
  async getCurrentUser() {
    const response = await apiGet('/auth/me')
    return response
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN)
    return !!token
  },

  /**
   * Get stored user
   */
  getStoredUser() {
    const user = localStorage.getItem(STORAGE_KEYS.USER)
    return user ? JSON.parse(user) : null
  },

  /**
   * Get auth token
   */
  getToken() {
    return localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN)
  },
}

export default authService