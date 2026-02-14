import { format, formatDistance, parseISO, isValid } from 'date-fns'

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
 * Format date with time
 */
export function formatDateTime(date) {
  return formatDate(date, 'MMM d, yyyy HH:mm')
}

/**
 * Format date as relative time
 */
export function formatTimeAgo(date) {
  if (!date) return '—'
  
  const parsedDate = typeof date === 'string' ? parseISO(date) : date
  
  if (!isValid(parsedDate)) return '—'
  
  return formatDistance(parsedDate, new Date(), { addSuffix: true })
}

/**
 * Format percentage
 */
export function formatPercent(value, decimals = 1) {
  if (value === null || value === undefined) return '—'
  return `${value.toFixed(decimals)}%`
}

/**
 * Format success rate
 */
export function formatSuccessRate(success, total) {
  if (!total || total === 0) return '—'
  const rate = (success / total) * 100
  return formatPercent(rate)
}

/**
 * Format job progress
 */
export function formatProgress(progress) {
  if (progress === null || progress === undefined) return '0%'
  return `${Math.round(progress)}%`
}

/**
 * Format product count with label
 */
export function formatProductCount(count) {
  if (count === null || count === undefined) return '0 products'
  
  const formatted = new Intl.NumberFormat().format(count)
  return `${formatted} product${count !== 1 ? 's' : ''}`
}

/**
 * Format page count with label
 */
export function formatPageCount(count) {
  if (count === null || count === undefined) return '0 pages'
  
  const formatted = new Intl.NumberFormat().format(count)
  return `${formatted} page${count !== 1 ? 's' : ''}`
}