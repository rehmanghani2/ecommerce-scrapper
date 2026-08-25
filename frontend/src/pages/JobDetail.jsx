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
  const [productsCount, setProductsCount] = useState(null)

  // Fetch job data
  const { data: job, isLoading, error } = useJob(jobId)
  
  // Real-time updates for running jobs
  const { data: realTimeData, isConnected } = useJobWebSocket(
    job?.status === 'running' ? jobId : null
  )

  // Dynamically fetch actual product count for menu tab
  React.useEffect(() => {
    if (!job?.job_id) return
    import('../services/jobService').then(({ default: svc }) => {
      svc.getJobProducts(job.job_id, { page: 1, page_size: 1 })
        .then(data => {
          if (data && data.total !== undefined) {
            setProductsCount(data.total)
          }
        })
        .catch(() => {})
    })
  }, [job?.job_id, job?.status, job?.total_products])

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

  const displayProductsCount = productsCount !== null ? productsCount : (job.total_products || 0)

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
      count: displayProductsCount,
      content: <JobProducts jobId={job.job_id} onTotalFetched={setProductsCount} />,
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
            <ExportButton jobId={job.job_id} />
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

function JobProducts({ jobId, onTotalFetched }) {
  const [page, setPage] = useState(1)
  const [products, setProducts] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  React.useEffect(() => {
    if (!jobId) return
    setLoading(true)
    import('../services/jobService').then(({ default: svc }) => {
      svc.getJobProducts(jobId, { page, page_size: 50 })
        .then(data => {
          const tot = data.total || 0
          setProducts(data.products || [])
          setTotal(tot)
          if (onTotalFetched) {
            onTotalFetched(tot)
          }
        })
        .catch(() => {})
        .finally(() => setLoading(false))
    })
  }, [jobId, page, onTotalFetched])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500 dark:text-gray-400">Loading products...</p>
      </div>
    )
  }

  if (products.length === 0) {
    return (
      <EmptyState
        icon={CubeIcon}
        title="No products extracted yet"
        description="Start or retry the job to extract products from this site."
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {total} product{total !== 1 ? 's' : ''} extracted
        </p>
        <ExportButton jobId={jobId} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {products.map((product, idx) => (
          <div
            key={product.id || idx}
            className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-lg transition-shadow duration-200"
          >
            {product.image_url && (
              <div className="aspect-square bg-gray-50 dark:bg-gray-900 overflow-hidden">
                <img
                  src={product.image_url}
                  alt={product.name}
                  className="w-full h-full object-contain p-2"
                  onError={(e) => { e.target.style.display = 'none' }}
                />
              </div>
            )}
            <div className="p-3 space-y-1">
              <p className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2 leading-snug">
                {product.name}
              </p>
              {product.price_text && (
                <p className="text-base font-bold text-primary-600 dark:text-primary-400">
                  {product.price_text}
                </p>
              )}
              {product.url && (
                <a
                  href={product.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-gray-400 hover:text-primary-500 truncate block mt-1"
                >
                  View product ↗
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {total > 50 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Previous
          </button>
          <span className="text-sm text-gray-500">
            Page {page} of {Math.ceil(total / 50)}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page >= Math.ceil(total / 50)}
            className="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}