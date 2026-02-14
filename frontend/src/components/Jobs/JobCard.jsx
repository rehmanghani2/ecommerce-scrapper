import React from 'react'
import { Link } from 'react-router-dom'
import {
  ClockIcon,
  CubeIcon,
  DocumentTextIcon,
  ArrowTopRightOnSquareIcon,
} from '@heroicons/react/24/outline'
import { cn, formatRelativeTime, formatNumber, formatDuration, extractDomain } from '@/utils/helpers'
import { Card, Badge, StatusBadge, Progress } from '@/components/Common'
import JobActions from './JobActions'

export function JobCard({ job, onAction }) {
  const isRunning = job.status === 'running'
  
  return (
    <Card hover className="relative">
      {/* Status indicator for running jobs */}
      {isRunning && (
        <div className="absolute top-0 left-0 right-0 h-1 bg-primary-200 dark:bg-primary-900/30 rounded-t-xl overflow-hidden">
          <div
            className="h-full bg-primary-600 transition-all duration-500"
            style={{ width: `${job.progress || 0}%` }}
          />
        </div>
      )}
      
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Link
              to={`/jobs/${job.job_id}`}
              className="font-semibold text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-primary-400 truncate"
            >
              {job.name}
            </Link>
            <StatusBadge status={job.status} />
          </div>
          
          <div className="flex items-center gap-2 mt-1">
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 flex items-center gap-1 truncate"
            >
              {extractDomain(job.url)}
              <ArrowTopRightOnSquareIcon className="w-3 h-3" />
            </a>
          </div>
        </div>
        
        <JobActions job={job} onAction={onAction} />
      </div>
      
      {/* Progress for running jobs */}
      {isRunning && (
        <div className="mt-4">
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-gray-500 dark:text-gray-400">Progress</span>
            <span className="font-medium text-gray-900 dark:text-white">
              {Math.round(job.progress || 0)}%
            </span>
          </div>
          <Progress value={job.progress || 0} variant="primary" size="sm" />
        </div>
      )}
      
      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t dark:border-gray-700">
        <div className="flex items-center gap-2">
          <CubeIcon className="w-4 h-4 text-gray-400" />
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Products</p>
            <p className="font-medium text-gray-900 dark:text-white">
              {formatNumber(job.total_products)}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <DocumentTextIcon className="w-4 h-4 text-gray-400" />
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Pages</p>
            <p className="font-medium text-gray-900 dark:text-white">
              {formatNumber(job.scraped_pages)}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <ClockIcon className="w-4 h-4 text-gray-400" />
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Duration</p>
            <p className="font-medium text-gray-900 dark:text-white">
              {job.duration ? formatDuration(job.duration) : '—'}
            </p>
          </div>
        </div>
      </div>
      
      {/* Timestamp */}
      <p className="mt-3 text-xs text-gray-400 dark:text-gray-500">
        Created {formatRelativeTime(job.created_at)}
      </p>
    </Card>
  )
}

// Compact version for lists
export function JobCardCompact({ job, onAction }) {
  return (
    <div className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
      <div className="flex items-center gap-4 min-w-0">
        <StatusBadge status={job.status} />
        
        <div className="min-w-0">
          <Link
            to={`/jobs/${job.job_id}`}
            className="font-medium text-gray-900 dark:text-white hover:text-primary-600 truncate block"
          >
            {job.name}
          </Link>
          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
            {extractDomain(job.url)} • {formatNumber(job.total_products)} products
          </p>
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-500 dark:text-gray-400 hidden sm:block">
          {formatRelativeTime(job.created_at)}
        </span>
        <JobActions job={job} onAction={onAction} compact />
      </div>
    </div>
  )
}

export default JobCard