import React, { createContext, useState, useEffect, useCallback } from 'react'
import { useAuth } from '../hooks/useAuth'
import { WS_BASE_URL, API_PREFIX } from '../utils/constants'
import authService from '../services/authService'

export const NotificationContext = createContext(null)

export function NotificationProvider({ children }) {
  const { user, isAuthenticated } = useAuth()
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [socket, setSocket] = useState(null)
  const [isConnected, setIsConnected] = useState(false)

  // Connect to WebSocket when authenticated
  useEffect(() => {
    if (!isAuthenticated || !user) {
      return
    }

    const token = authService.getToken()
    const wsUrl = `${WS_BASE_URL}${API_PREFIX}/ws/${user.id}?token=${token}`

    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleNotification(data)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    setSocket(ws)

    // Ping to keep connection alive
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)

    return () => {
      clearInterval(pingInterval)
      ws.close()
    }
  }, [isAuthenticated, user])

  const handleNotification = useCallback((data) => {
    // Add to notifications list
    setNotifications((prev) => [data, ...prev].slice(0, 50))
    
    // Update unread count
    if (!data.read) {
      setUnreadCount((prev) => prev + 1)
    }

    // Show toast for certain types
    if (data.type === 'job_completed') {
      import('react-hot-toast').then(({ default: toast }) => {
        toast.success(`Job completed: ${data.data?.job_name || 'Unknown'}`)
      })
    } else if (data.type === 'job_failed') {
      import('react-hot-toast').then(({ default: toast }) => {
        toast.error(`Job failed: ${data.data?.job_name || 'Unknown'}`)
      })
    }
  }, [])

  const markAsRead = useCallback((notificationId = null) => {
    if (notificationId) {
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === notificationId ? { ...n, read: true } : n
        )
      )
      setUnreadCount((prev) => Math.max(0, prev - 1))
    } else {
      // Mark all as read
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
      setUnreadCount(0)
    }
  }, [])

  const clearNotifications = useCallback(() => {
    setNotifications([])
    setUnreadCount(0)
  }, [])

  const subscribeToJob = useCallback(
    (jobId) => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(
          JSON.stringify({
            type: 'subscribe',
            channels: [`job:${jobId}`],
          })
        )
      }
    },
    [socket]
  )

  const unsubscribeFromJob = useCallback(
    (jobId) => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(
          JSON.stringify({
            type: 'unsubscribe',
            channels: [`job:${jobId}`],
          })
        )
      }
    },
    [socket]
  )

  const value = {
    notifications,
    unreadCount,
    isConnected,
    markAsRead,
    clearNotifications,
    subscribeToJob,
    unsubscribeFromJob,
  }

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  )
}