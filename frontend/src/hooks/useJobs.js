import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import jobService from '../services/jobService'
import toast from 'react-hot-toast'

/**
 * Hook for fetching jobs list
 */
export function useJobs(params = {}) {
  return useQuery({
    queryKey: ['jobs', params],
    queryFn: () => jobService.listJobs(params),
    keepPreviousData: true,
  })
}

/**
 * Hook for fetching job statistics
 */
export function useJobStats() {
  return useQuery({
    queryKey: ['jobStats'],
    queryFn: () => jobService.getJobStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}

/**
 * Hook for fetching single job
 */
export function useJob(jobId) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobService.getJob(jobId),
    enabled: !!jobId,
    refetchInterval: (data) => {
      // Refresh more frequently if job is running
      if (data?.status === 'running') {
        return 5000 // 5 seconds
      }
      return false
    },
  })
}

/**
 * Hook for fetching job logs
 */
export function useJobLogs(jobId, limit = 500) {
  return useQuery({
    queryKey: ['jobLogs', jobId, limit],
    queryFn: () => jobService.getJobLogs(jobId, limit),
    enabled: !!jobId,
    refetchInterval: 3000, // Poll every 3 seconds for live log updates
  })
}

/**
 * Hook for job actions (pause, resume, cancel, etc.)
 */
export function useJobActions() {
  const queryClient = useQueryClient()

  const pauseJob = useMutation({
    mutationFn: (jobId) => jobService.pauseJob(jobId),
    onSuccess: (data, jobId) => {
      toast.success('Job paused')
      queryClient.invalidateQueries(['job', jobId])
      queryClient.invalidateQueries(['jobs'])
    },
    onError: () => {
      toast.error('Failed to pause job')
    },
  })

  const resumeJob = useMutation({
    mutationFn: (jobId) => jobService.resumeJob(jobId),
    onSuccess: (data, jobId) => {
      toast.success('Job resumed')
      queryClient.invalidateQueries(['job', jobId])
      queryClient.invalidateQueries(['jobs'])
    },
    onError: () => {
      toast.error('Failed to resume job')
    },
  })

  const cancelJob = useMutation({
    mutationFn: (jobId) => jobService.cancelJob(jobId),
    onSuccess: (data, jobId) => {
      toast.success('Job cancelled')
      queryClient.invalidateQueries(['job', jobId])
      queryClient.invalidateQueries(['jobs'])
    },
    onError: () => {
      toast.error('Failed to cancel job')
    },
  })

  const retryJob = useMutation({
    mutationFn: (jobId) => jobService.retryJob(jobId),
    onSuccess: (data, jobId) => {
      toast.success('Job queued for retry')
      queryClient.invalidateQueries(['job', jobId])
      queryClient.invalidateQueries(['jobs'])
    },
    onError: () => {
      toast.error('Failed to retry job')
    },
  })

  const deleteJob = useMutation({
    mutationFn: (jobId) => jobService.deleteJob(jobId),
    onSuccess: () => {
      toast.success('Job deleted')
      queryClient.invalidateQueries(['jobs'])
    },
    onError: () => {
      toast.error('Failed to delete job')
    },
  })

  return {
    pauseJob,
    resumeJob,
    cancelJob,
    retryJob,
    deleteJob,
  }
}

export default useJobs