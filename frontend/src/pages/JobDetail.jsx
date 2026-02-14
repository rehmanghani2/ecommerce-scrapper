import React, { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeftIcon,
  ArrowTopRightOnSquareIcon,
  ClockIcon,
  CubeIcon,
  DocumentTextIcon,
  ArrowDownTrayIcon,
} from '@heroicons/react/24/outline'
import { cn, formatDate, formatDuration, formatNumber, extractDomain } from '@/utils/helpers'
import { useJob, useJobActions } from '@/hooks/useJobs'
import { useJobWebSocket } from '@/hooks/useWebSocket'
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  Badge,
  StatusBadge,
  PageLoader,
  EmptyState,
  Alert,
  UnderlineTabs,
} from '@/components/Common'
import { JobProgress, JobLogs, JobActions } from '@/components/Jobs'
import { ProductCard, ExportButton } from '@/components/DataViewer'

export default function JobDetail() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState(0)

  // Fetch job data
  const { data: job, isLoading, error } = useJob(jobId)
  
  // Real-time updates for running jobs
  const { data: realTimeData, isConnected } = useJobWebSocket(
    job?.status === 'running' ? jobId : null
  )

  const { deleteJob } = useJobActions()

  const handleDelete = () => {
    deleteJob.mutate(jobId, {
      onSuccess: () => navigate('/jobs'),
    })
  }

  if (isLoading) {
    return <PageLoader message="Loading job details..." />
  }

  if (error || !job) {
    return (
      <EmptyState
        title="Job not found"
        description="The job you're looking for doesn't exist or has been deleted."
        action={
          <Link to="/jobs">
            <Button icon={ArrowLeftIcon}>Back to Jobs</Button>
          </Link>
        }
      />
    )
  }

  const isRunning = job.status === 'running'
  const isCompleted = job.status === 'completed'
  const isFailed = job.status === 'failed'

  const tabs = [
    {
      key: 'overview',
      label: 'Overview',
      content: (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Progress */}
          <div className="lg:col-span-1">
            <JobProgress job={job} realTimeData={realTimeData} />
          </div>
          
          {/* Details */}
          <div className="lg:col-span-2 space-y-6">
            {/* Job Info */}
            <Card>
              <CardHeader>
                <CardTitle>Job Details</CardTitle>
              </CardHeader>
              
              <div className="grid grid-cols-2 gap-4">
                <DetailItem label="Job ID" value={job.job_id} mono />
                <DetailItem label="Status" value={<StatusBadge status={job.status} />} />
                <DetailItem label="Domain" value={job.domain} />
                <DetailItem label="Job Type" value={job.job_type} />
                <DetailItem label="Created" value={formatDate(job.created_at, 'PPp')} />
                <DetailItem 
                  label="Started" 
                  value={job.started_at ? formatDate(job.started_at, 'PPp') : '—'} 
                />
                <DetailItem 
                  label="Completed" 
                  value={job.completed_at ? formatDate(job.completed_at, 'PPp') : '—'} 
                />
                <DetailItem 
                  label="Duration" 
                  value={job.duration ? formatDuration(job.duration) : '—'} 
                />
              </div>
              
              {/* URL */}
              <div className="mt-4 pt-4 border-t dark:border-gray-700">
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">Target URL</p>
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:text-primary-700 dark:text-primary-400 flex items-center gap-1 break-all"
                >
                  {job.url}
                  <ArrowTopRightOnSquareIcon className="w-4 h-4 flex-shrink-0" />
                </a>
              </div>
            </Card>

            {/* Error Message */}
            {isFailed && job.error_message && (
              <Alert variant="danger" title="Job Failed">
                {job.error_message}
              </Alert>
            )}

            {/* Configuration */}
            {job.config && Object.keys(job.config).length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Configuration</CardTitle>
                </CardHeader>
                
                <pre className="text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded-lg p-4 overflow-auto">
                  {JSON.stringify(job.config, null, 2)}
                </pre>
              </Card>
            )}
          </div>
        </div>
      ),
    },
    {
      key: 'products',
      label: 'Products',
      count: job.total_products,
      content: <JobProducts jobId={job.id} />,
    },
    {
      key: 'logs',
      label: 'Logs',
      content: <JobLogs jobId={jobId} />,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Link
              to="/jobs"
              className="p-2 -ml-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <ArrowLeftIcon className="w-5 h-5" />
            </Link>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {job.name}
            </h1>
            <StatusBadge status={job.status} />
            {isRunning && isConnected && (
              <Badge variant="success" size="sm" dot>
                Live
              </Badge>
            )}
          </div>
          
          <p className="text-gray-500 dark:text-gray-400">
            {extractDomain(job.url)} • Created {formatDate(job.created_at)}
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {isCompleted && (
            <ExportButton jobId={job.id} />
          )}
          <JobActions job={job} onAction={() => {}} />
        </div>
      </div>

      {/* Tabs */}
      <UnderlineTabs
        tabs={tabs}
        selectedIndex={activeTab}
        onChange={setActiveTab}
      />
    </div>
  )
}

function DetailItem({ label, value, mono = false }) {
  return (
    <div>
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className={cn(
        'font-medium text-gray-900 dark:text-white mt-0.5',
        mono && 'font-mono text-sm'
      )}>
        {value}
      </p>
    </div>
  )
}

function JobProducts({ jobId }) {
  const [page, setPage] = useState(1)
  
  // This would use a hook to fetch products for the job
  // For now, showing a placeholder
  
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Showing products scraped in this job
        </p>
        <ExportButton jobId={jobId} />
      </div>
      
      <EmptyState
        icon={CubeIcon}
        title="Products will appear here"
        description="Products extracted during this job will be displayed here."
      />
    </div>
  )
}