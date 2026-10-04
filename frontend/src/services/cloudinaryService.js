import { apiGet, apiPost } from './api'

export const cloudinaryService = {
  /**
   * Get current Cloudinary setup status and account metadata
   */
  async getStatus() {
    return await apiGet('/cloudinary/status')
  },

  /**
   * Test Cloudinary credentials and retrieve storage & bandwidth quota usage
   */
  async testConnection(credentials = null) {
    return await apiPost('/cloudinary/test', credentials)
  },

  /**
   * Upload single image URL directly to Cloudinary CDN
   */
  async uploadImage(imageUrl, folder = null) {
    return await apiPost('/cloudinary/upload', {
      image_url: imageUrl,
      folder,
    })
  },

  /**
   * Batch-sync all product images from a job to Cloudinary CDN in the background
   */
  async syncJobImages(jobId) {
    return await apiPost(`/cloudinary/sync-job-images/${jobId}`)
  },
}

export default cloudinaryService
