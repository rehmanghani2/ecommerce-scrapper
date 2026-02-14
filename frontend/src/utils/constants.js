// API endpoints
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const API_PREFIX = '/api/v1'
export const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

// App info
export const APP_NAME = import.meta.env.VITE_APP_NAME || 'E-Commerce Scraper'

// Job statuses
export const JOB_STATUS = {
  PENDING: 'pending',
  QUEUED: 'queued',
  RUNNING: 'running',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
}

// Status colors
export const STATUS_COLORS = {
  [JOB_STATUS.PENDING]: 'gray',
  [JOB_STATUS.QUEUED]: 'blue',
  [JOB_STATUS.RUNNING]: 'primary',
  [JOB_STATUS.PAUSED]: 'warning',
  [JOB_STATUS.COMPLETED]: 'success',
  [JOB_STATUS.FAILED]: 'danger',
  [JOB_STATUS.CANCELLED]: 'gray',
}

// Export formats
export const EXPORT_FORMATS = [
  { value: 'csv', label: 'CSV', icon: 'DocumentTextIcon' },
  { value: 'excel', label: 'Excel', icon: 'TableCellsIcon' },
  { value: 'json', label: 'JSON', icon: 'CodeBracketIcon' },
]

// Pagination defaults
export const DEFAULT_PAGE_SIZE = 20
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

// Scraper platforms
export const PLATFORMS = [
  { value: 'auto', label: 'Auto Detect' },
  { value: 'shopify', label: 'Shopify' },
  { value: 'woocommerce', label: 'WooCommerce' },
  { value: 'magento', label: 'Magento' },
  { value: 'generic', label: 'Generic' },
]

// Local storage keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  USER: 'user',
  THEME: 'theme',
  SIDEBAR_COLLAPSED: 'sidebar_collapsed',
}

// Date formats
export const DATE_FORMATS = {
  SHORT: 'MMM d, yyyy',
  LONG: 'MMMM d, yyyy',
  WITH_TIME: 'MMM d, yyyy HH:mm',
  TIME_ONLY: 'HH:mm:ss',
  ISO: "yyyy-MM-dd'T'HH:mm:ss",
}