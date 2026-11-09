import { apiGet, apiPost } from './api'

export const scraperService = {
  /**
   * Start a new scraping job
   */
  async startScraping(url, name = '', config = {}) {
    const response = await apiPost('/scraper/start', {
      url,
      name,
      config,
    })
    return response
  },

  /**
   * Discover categories and product URL samples using Playwright.
   */
  async discoverWebsite(url) {
    return await apiPost('/scraper/discover', { url })
  },

  /**
   * Preview scraping for a URL
   */
  async previewScraping(url, selectors = null) {
    const response = await apiPost('/scraper/preview', {
      url,
      selectors,
      sample_size: 5,
    })
    return response
  },

  /**
   * Detect platform for a URL
   */
  async detectPlatform(url) {
    const response = await apiPost('/scraper/detect-platform', null, {
      params: { url },
    })
    return response
  },

  /**
   * Test custom selectors
   */
  async testSelectors(url, selectors) {
    const response = await apiPost('/scraper/test-selectors', {
      url,
      selectors,
    })
    return response
  },

  /**
   * Test visual picker selectors and get sample data
   */
  async testVisualSelectors(url, selectors) {
    const response = await apiPost('/scraper/visual-picker/test', {
      url,
      selectors,
    })
    return response
  },

  /**
   * Get direct render proxy URL for iframe
   */
  getVisualPickerRenderUrl(url) {
    return `/api/scraper/visual-picker/render?url=${encodeURIComponent(url)}`
  },

  /**
   * Presets CRUD
   */
  async getPresets(domain = '') {
    const params = domain ? { domain } : {}
    const response = await apiGet('/scraper/presets', params)
    return response
  },

  async savePreset(data) {
    const response = await apiPost('/scraper/presets', data)
    return response
  },

  async deletePreset(presetId) {
    const { apiDelete } = await import('./api')
    return await apiDelete(`/scraper/presets/${presetId}`)
  },

  /**
   * AI-Powered Product Extraction (Google Gemini Zero-Shot)
   */
  async aiExtractProducts({ url, html = null, apiKey = null, model = null }) {
    const response = await apiPost('/scraper/ai-extract', {
      url,
      html,
      api_key: apiKey,
      model,
    })
    return response
  },

  /**
   * AI-Powered CSS Selector Reverse-Engineering (Google Gemini)
   */
  async aiSuggestSelectors({ url, html = null, apiKey = null }) {
    const response = await apiPost('/scraper/ai-suggest-selectors', {
      url,
      html,
      api_key: apiKey,
    })
    return response
  },

  /**
   * Get supported platforms
   */
  async getSupportedPlatforms() {
    const response = await apiGet('/scraper/supported-platforms')
    return response.platforms
  },

  /**
   * Get proxy pool health and rotation status
   */
  async getProxyStatus() {
    return await apiGet('/scraper/proxies/status')
  },

  /**
   * Parse remote/local sitemap XML or .gz (traverses nested sitemap indexes)
   */
  async parseSitemap(sitemapUrl, filterProductsOnly = false) {
    return await apiPost('/scraper/sitemap/parse', {
      sitemap_url: sitemapUrl,
      filter_products_only: filterProductsOnly,
    })
  },

  /**
   * Parse uploaded CSV, TSV, or TXT file content
   */
  async parseBulkFile(content, fileName = '') {
    return await apiPost('/scraper/bulk/parse-file', {
      content,
      file_name: fileName,
    })
  },

  /**
   * Start parallel bulk crawling across up to 10,000+ URLs
   */
  async startBulkScraping({ urls, name = '', concurrency = 10, requestDelay = 0.5, selectors = null }) {
    return await apiPost('/scraper/bulk/start', {
      urls,
      name,
      concurrency,
      request_delay: requestDelay,
      selectors,
    })
  },
}

export default scraperService