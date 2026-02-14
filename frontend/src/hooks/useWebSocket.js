import { useState, useEffect, useCallback, useRef } from 'react'
import { WS_BASE_URL, API_PREFIX } from '../utils/constants'
import authService from '../services/authService'

/**
 * Hook for WebSocket connection to a specific job
 */
export function useJobWebSocket(jobId) {
  const [data, setData] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState(null)
  const socketRef = useRef(null)

  useEffect(() => {
    if (!jobId) return

    const token = authService.getToken()
    if (!token) return

    const wsUrl = `${WS_BASE_URL}${API_PREFIX}/ws/jobs/${jobId}?token=${token}`

    const ws = new WebSocket(wsUrl)
    socketRef.current = ws

    ws.onopen = () => {
      console.log(`WebSocket connected for job ${jobId}`)
      setIsConnected(true)
      setError(null)
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        setData(message)
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    ws.onerror = (event) => {
      console.error('WebSocket error:', event)
      setError('Connection error')
    }

    ws.onclose = (event) => {
      console.log(`WebSocket closed for job ${jobId}:`, event.reason)
      setIsConnected(false)
    }

    // Ping to keep alive
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)

    return () => {
      clearInterval(pingInterval)
      ws.close()
    }
  }, [jobId])

  const sendMessage = useCallback((message) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message))
    }
  }, [])

  return {
    data,
    isConnected,
    error,
    sendMessage,
  }
}

/**
 * Hook for general WebSocket connection
 */
export function useWebSocket(userId) {
  const [messages, setMessages] = useState([])
  const [isConnected, setIsConnected] = useState(false)
  const socketRef = useRef(null)

  useEffect(() => {
    if (!userId) return

    const token = authService.getToken()
    if (!token) return

    const wsUrl = `${WS_BASE_URL}${API_PREFIX}/ws/${userId}?token=${token}`

    const ws = new WebSocket(wsUrl)
    socketRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        setMessages((prev) => [...prev, message])
      } catch (e) {
        console.error('Failed to parse message:', e)
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
    }

    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)

    return () => {
      clearInterval(pingInterval)
      ws.close()
    }
  }, [userId])

  const sendMessage = useCallback((message) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message))
    }
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return {
    messages,
    isConnected,
    sendMessage,
    clearMessages,
  }
}

export default useJobWebSocket