import { clsx } from 'clsx'
import { format, formatDistance, parseISO, isValid } from 'date-fns'
/**
 * Merge class names with clsx
 */
export function cn(...classes) {
  return clsx(...classes)
}

/**
 * Format a number with commas
 */
export function formatNumber(num) {
  if (num === null || num === undefined) return '—'
  return new Intl.NumberFormat().format(num)
}

/**
 * Format percentage
 */
export function formatPercent(value, decimals = 1) {
  if (value === null || value === undefined) return '—'
  return `${value.toFixed(decimals)}%`
}

/**
 * Format date with specified format
 */
export function formatDate(date, formatStr = 'MMM d, yyyy') {
  if (!date) return '—'
  
  const parsedDate = typeof date === 'string' ? parseISO(date) : date
  
  if (!isValid(parsedDate)) return '—'
  
  return format(parsedDate, formatStr)
}

/**
 * Format price with currency
 */
export function formatPrice(price, currency = 'GBP') {
  if (price === null || price === undefined) return '—'
  
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: currency,
  }).format(price)
}

/**
 * Format file size
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * Format duration in seconds to human readable
 */
export function formatDuration(seconds) {
  if (!seconds || seconds < 0) return '—'
  
  if (seconds < 60) {
    return `${Math.round(seconds)}s`
  }
  
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds % 60)
  
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`
  }
  
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  
  return `${hours}h ${remainingMinutes}m`
}

/**
 * Format relative time
 */
export function formatRelativeTime(date) {
  if (!date) return '—'
  
  const now = new Date()
  const then = new Date(date)
  const diffInSeconds = Math.floor((now - then) / 1000)
  
  if (diffInSeconds < 60) {
    return 'just now'
  }
  
  if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60)
    return `${minutes} minute${minutes > 1 ? 's' : ''} ago`
  }
  
  if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600)
    return `${hours} hour${hours > 1 ? 's' : ''} ago`
  }
  
  const days = Math.floor(diffInSeconds / 86400)
  if (days < 7) {
    return `${days} day${days > 1 ? 's' : ''} ago`
  }
  
  return then.toLocaleDateString()
}

/**
 * Truncate text with ellipsis
 */
export function truncate(str, maxLength = 50) {
  if (!str) return ''
  if (str.length <= maxLength) return str
  return str.slice(0, maxLength) + '...'
}

/**
 * Extract domain from URL
 */
export function extractDomain(url) {
  try {
    const urlObj = new URL(url)
    return urlObj.hostname.replace('www.', '')
  } catch {
    return url
  }
}

/**
 * Validate URL
 */
export function isValidUrl(string) {
  try {
    const url = new URL(string)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

/**
 * Generate a random ID
 */
export function generateId(length = 8) {
  return Math.random().toString(36).substring(2, 2 + length)
}

/**
 * Debounce function
 */
export function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

/**
 * Deep clone object
 */
export function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj))
}

/**
 * Check if object is empty
 */
export function isEmpty(obj) {
  if (!obj) return true
  if (Array.isArray(obj)) return obj.length === 0
  if (typeof obj === 'object') return Object.keys(obj).length === 0
  return false
}

/**
 * Get initials from name
 */
export function getInitials(name) {
  if (!name) return ''
  
  const words = name.trim().split(' ')
  if (words.length === 1) {
    return words[0].charAt(0).toUpperCase()
  }
  
  return (words[0].charAt(0) + words[words.length - 1].charAt(0)).toUpperCase()
}

/**
 * Copy text to clipboard
 */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // Fallback for older browsers
    const textArea = document.createElement('textarea')
    textArea.value = text
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
    return true
  }
}

/**
 * Download file from blob
 */
export function downloadFile(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * Get status badge class
 */
export function getStatusColor(status) {
  const colors = {
    pending: 'gray',
    queued: 'blue',
    running: 'primary',
    paused: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'gray',
  }
  return colors[status] || 'gray'
}