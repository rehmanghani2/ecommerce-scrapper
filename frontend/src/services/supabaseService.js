import { apiGet, apiPost } from './api'

export const supabaseService = {
  /**
   * Get current Supabase Storage configuration status
   */
  async getStatus() {
    return await apiGet('/supabase/status')
  },

  /**
   * Test Supabase Storage bucket connectivity and permissions
   */
  async testConnection(credentials = null) {
    return await apiPost('/supabase/test', credentials)
  },

  /**
   * Download and stream single image URL directly into Supabase Storage
   */
  async uploadImage(imageUrl, bucket = null, folder = null, supabaseUrl = null, supabaseKey = null) {
    return await apiPost('/supabase/upload', {
      image_url: imageUrl,
      bucket,
      folder,
      supabase_url: supabaseUrl,
      supabase_key: supabaseKey,
    })
  },

  /**
   * Batch-archive all product images from a job into Supabase Storage
   */
  async syncJobImages(jobId) {
    return await apiPost(`/supabase/sync-job-images/${jobId}`)
  },
}

export default supabaseService
