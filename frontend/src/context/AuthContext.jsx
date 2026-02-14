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
        if (authService.isAuthenticated()) {
          // Try to get current user
          const currentUser = await authService.getCurrentUser()
          setUser(currentUser)
          setIsAuthenticated(true)
        }
      } catch (error) {
        // Token might be expired
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
      print(loggedInUser)
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