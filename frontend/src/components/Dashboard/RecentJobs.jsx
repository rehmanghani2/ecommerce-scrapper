import React from 'react'
import { Link } from 'react-router-dom'
import { ArrowRightIcon, PlusIcon } from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'
import { Card, CardHeader, CardTitle, Button, EmptyState } from '@/components/Common'
import { JobCardCompact } from '@/components/Jobs'
import { useJobs } from '@/hooks/useJobs'

export function RecentJobs() {
  const { data, isLoading } = useJobs({ page: 1, page_size: 5 })

  const jobs = data?.jobs || []

  return (
    <Card padding="none">
      <div className="flex items-center justify-between px-6 py-4 border-b dark:border-gray-700">
        <CardTitle>Recent Jobs</CardTitle>
        <Link
          to="/jobs"
          className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 flex items-center gap-1"
        >
          View all
          <ArrowRightIcon className="w-4 h-4" />
        </Link>
      </div>

      {isLoading ? (
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="p-4 animate-pulse">
              <div className="flex items-center gap-4">
                <div className="w-16 h-5 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="flex-1">
                  <div className="w-48 h-4 bg-gray-200 dark:bg-gray-700 rounded mb-2" />
                  <div className="w-32 h-3 bg-gray-200 dark:bg-gray-700 rounded" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <EmptyState
          title="No jobs yet"
          description="Start scraping to see your jobs here."
          action={
            <Link to="/scraper">
              <Button icon={PlusIcon}>Start Scraping</Button>
            </Link>
          }
        />
      ) : (
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {jobs.map((job) => (
            <JobCardCompact key={job.job_id} job={job} />
          ))}
        </div>
      )}
    </Card>
  )
}

export default RecentJobs