import { apiGet, apiPost } from './api'

export const s3Service = {
  /**
   * Get current AWS S3 / Cloud Storage configuration status
   */
  async getStatus() {
    return await apiGet('/s3/status')
  },

  /**
   * Test S3 bucket connectivity and access permissions
   */
  async testConnection(credentials = null) {
    return await apiPost('/s3/test', credentials)
  },

  /**
   * Download and stream single image URL directly into S3 bucket
   */
  async uploadImage(imageUrl, bucket = null, prefix = null) {
    return await apiPost('/s3/upload', {
      image_url: imageUrl,
      bucket,
      prefix,
    })
  },

  /**
   * Batch-archive all product images from a job into AWS S3
   */
  async syncJobImages(jobId) {
    return await apiPost(`/s3/sync-job-images/${jobId}`)
  },
}

export default s3Service
