import React from 'react'
import {
  CubeIcon,
  DocumentTextIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'
import { cn, formatNumber, formatDuration } from '@/utils/helpers'
import { Card, Progress, CircularProgress, Badge } from '@/components/Common'

export function JobProgress({ job, realTimeData }) {
  // Merge real-time data with job data
  const data = {
    ...job,
    ...realTimeData,
  }

  const isRunning = data.status === 'running'
  const isCompleted = data.status === 'completed'
  const isFailed = data.status === 'failed'

  return (
    <Card>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Progress
        </h3>
        
        {isRunning && (
          <Badge variant="primary" dot>
            Running
          </Badge>
        )}
        {isCompleted && (
          <Badge variant="success">
            <CheckCircleIcon className="w-3 h-3 mr-1" />
            Completed
          </Badge>
        )}
        {isFailed && (
          <Badge variant="danger">
            <ExclamationTriangleIcon className="w-3 h-3 mr-1" />
            Failed
          </Badge>
        )}
      </div>

      {/* Main progress */}
      <div className="flex items-center justify-center mb-6">
        <CircularProgress
          value={data.progress || 0}
          size={140}
          strokeWidth={10}
          variant={isFailed ? 'danger' : isCompleted ? 'success' : 'primary'}
        />
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-4">
        <StatItem
          icon={CubeIcon}
          label="Products"
          value={formatNumber(data.total_products)}
          color="primary"
        />
        
        <StatItem
          icon={DocumentTextIcon}
          label="Pages"
          value={`${formatNumber(data.scraped_pages)} / ${formatNumber(data.total_pages || '—')}`}
          color="success"
        />
        
        <StatItem
          icon={ClockIcon}
          label="Duration"
          value={data.duration ? formatDuration(data.duration) : 'Calculating...'}
          color="warning"
        />
        
        <StatItem
          icon={ExclamationTriangleIcon}
          label="Failed Pages"
          value={formatNumber(data.failed_pages)}
          color={data.failed_pages > 0 ? 'danger' : 'secondary'}
        />
      </div>

      {/* Current URL for running jobs */}
      {isRunning && data.current_url && (
        <div className="mt-4 pt-4 border-t dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
            Currently scraping
          </p>
          <p className="text-sm text-gray-700 dark:text-gray-300 truncate font-mono">
            {data.current_url}
          </p>
        </div>
      )}

      {/* Error message for failed jobs */}
      {isFailed && data.error_message && (
        <div className="mt-4 p-3 bg-danger-50 dark:bg-danger-900/20 rounded-lg">
          <p className="text-sm text-danger-700 dark:text-danger-300">
            {data.error_message}
          </p>
        </div>
      )}
    </Card>
  )
}

function StatItem({ icon: Icon, label, value, color = 'primary' }) {
  const colors = {
    primary: 'text-primary-600 bg-primary-100 dark:bg-primary-900/30 dark:text-primary-400',
    success: 'text-success-600 bg-success-100 dark:bg-success-900/30 dark:text-success-400',
    warning: 'text-warning-600 bg-warning-100 dark:bg-warning-900/30 dark:text-warning-400',
    danger: 'text-danger-600 bg-danger-100 dark:bg-danger-900/30 dark:text-danger-400',
    secondary: 'text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-400',
  }

  return (
    <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
      <div className={cn('p-2 rounded-lg', colors[color])}>
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
        <p className="font-semibold text-gray-900 dark:text-white">{value}</p>
      </div>
    </div>
  )
}

export default JobProgress