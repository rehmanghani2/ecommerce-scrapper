import { apiGet, apiPost, apiDelete } from './api'

export const taxonomyService = {
  // Get all standard taxonomies (Google Shopping, Amazon Browse Tree, Shopify, Custom)
  getStandards: () => apiGet('/taxonomy/standards'),

  // Get full node hierarchy for a taxonomy standard
  getTaxonomyTree: (taxonomyId) => apiGet(`/taxonomy/standards/${taxonomyId}/tree`),

  // Get catalog mapping statistics and category breakdown
  getSummary: (taxonomyId) => apiGet(`/taxonomy/summary/${taxonomyId}`),

  // Run automated catalog auto-categorization
  autoCategorizeCatalog: (payload) => apiPost('/taxonomy/auto-categorize', payload),

  // Classify a single product with Gemini AI reasoning
  classifyProduct: (payload) => apiPost('/taxonomy/classify-product', payload),

  // Approve or override a product taxonomy assignment
  verifyMapping: (payload) => apiPost('/taxonomy/verify', payload),

  // List product mappings with filtering
  getMappings: (params) => apiGet('/taxonomy/mappings', params),

  // Get category mapping rules
  getRules: (taxonomyId) => apiGet('/taxonomy/rules', taxonomyId ? { taxonomy_id: taxonomyId } : {}),

  // Create a mapping rule
  createRule: (ruleData) => apiPost('/taxonomy/rules', ruleData),

  // Delete a mapping rule
  deleteRule: (ruleId) => apiDelete(`/taxonomy/rules/${ruleId}`),
}

export default taxonomyService
