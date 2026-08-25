import React, { createContext, useState, useEffect, useCallback } from 'react'
import authService from '../services/authService'

export const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = authService.getToken ? authService.getToken() : localStorage.getItem('auth_token')
        if (!token) {
          // No token at all — skip network call
          setIsLoading(false)
          return
        }
        // Quick sanity check: JWT has 3 dot-separated parts
        if (token.split('.').length !== 3) {
          authService.logout()
          setIsLoading(false)
          return
        }
        // Race the network call against a 5-second timeout
        const timeoutPromise = new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Auth check timed out')), 5000)
        )
        const currentUser = await Promise.race([
          authService.getCurrentUser(),
          timeoutPromise,
        ])
        setUser(currentUser)
        setIsAuthenticated(true)
      } catch (error) {
        // Token expired, invalid, or backend unreachable
        authService.logout()
        setUser(null)
        setIsAuthenticated(false)
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()
  }, [])

  const login = useCallback(async (username, password) => {
    setIsLoading(true)
    try {
      const { user: loggedInUser } = await authService.login(username, password)
      console.log("LoggedInUser ", loggedInUser)
      setUser(loggedInUser)
      setIsAuthenticated(true)
      return loggedInUser
    } finally {
      setIsLoading(false)
    }
  }, [])

  const register = useCallback(async (email, username, password, fullName) => {
    setIsLoading(true)
    try {
      await authService.register(email, username, password, fullName)
      // Auto-login after registration
      return await login(username, password)
    } finally {
      setIsLoading(false)
    }
  }, [login])

  const logout = useCallback(() => {
    authService.logout()
    setUser(null)
    setIsAuthenticated(false)
  }, [])

  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await authService.getCurrentUser()
      setUser(currentUser)
      return currentUser
    } catch (error) {
      logout()
      throw error
    }
  }, [logout])

  const value = {
    user,
    isLoading,
    isAuthenticated,
    login,
    register,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}