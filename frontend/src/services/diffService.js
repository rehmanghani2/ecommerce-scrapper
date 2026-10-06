import api, { apiDownload } from './api'

export const diffService = {
  compareJobs: async (jobId1, jobId2) => {
    const res = await api.post('/diff/compare', {
      job_id_1: jobId1,
      job_id_2: jobId2,
    })
    return res.data
  },

  compareWithPrevious: async (jobId) => {
    const res = await api.get(`/diff/job/${jobId}/previous`)
    return res.data
  },

  compareDomainLatest: async (domain) => {
    const res = await api.get(`/diff/domain/${domain}`)
    return res.data
  },

  downloadDiffCsv: async (jobId1, jobId2) => {
    const filename = `catalog_diff_job_${jobId1}_vs_${jobId2}.csv`
    await apiDownload(`/diff/export/${jobId1}/${jobId2}`, filename)
  },
}

export default diffService
