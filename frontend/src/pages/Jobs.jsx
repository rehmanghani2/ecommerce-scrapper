import React, { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  BriefcaseIcon,
  PlusIcon,
  Squares2X2Icon,
  ListBulletIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'
import { useJobs, useJobActions } from '@/hooks/useJobs'
import {
  Button,
  Card,
  Pagination,
  EmptyState,
  PageLoader,
} from '@/components/Common'
import { JobCard, JobCardCompact, JobFilters } from '@/components/Jobs'

export default function Jobs() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState('grid') // 'grid' or 'list'
  
  // Parse filters from URL
  const filters = {
    search: searchParams.get('search') || '',
    status: searchParams.get('status') || '',
    domain: searchParams.get('domain') || '',
  }
  const page = parseInt(searchParams.get('page') || '1', 10)
  const pageSize = 12

  // Fetch jobs
  const { data, isLoading, error } = useJobs({
    ...filters,
    page,
    page_size: pageSize,
  })

  const jobs = data?.jobs || []
  const totalPages = data?.pages || 1

  // Update URL params
  const handleFilterChange = (newFilters) => {
    const params = new URLSearchParams()
    Object.entries(newFilters).forEach(([key, value]) => {
      if (value) params.set(key, value)
    })
    params.set('page', '1') // Reset to first page on filter change
    setSearchParams(params)
  }

  const handleClearFilters = () => {
    setSearchParams({})
  }

  const handlePageChange = (newPage) => {
    const params = new URLSearchParams(searchParams)
    params.set('page', newPage.toString())
    setSearchParams(params)
  }

  if (error) {
    return (
      <EmptyState
        title="Error loading jobs"
        description="An error occurred while loading your jobs. Please try again."
        actionLabel="Retry"
        onAction={() => window.location.reload()}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <BriefcaseIcon className="w-8 h-8 text-primary-600" />
            Scraping Jobs
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Manage and monitor your scraping jobs
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* View toggle */}
          <div className="flex items-center bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={cn(
                'p-2 rounded-md transition-colors',
                viewMode === 'grid'
                  ? 'bg-white dark:bg-gray-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              <Squares2X2Icon className="w-5 h-5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={cn(
                'p-2 rounded-md transition-colors',
                viewMode === 'list'
                  ? 'bg-white dark:bg-gray-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              <ListBulletIcon className="w-5 h-5" />
            </button>
          </div>
          
          <Link to="/scraper">
            <Button icon={PlusIcon}>
              New Job
            </Button>
          </Link>
        </div>
      </div>

      {/* Filters */}
      <JobFilters
        filters={filters}
        onChange={handleFilterChange}
        onClear={handleClearFilters}
      />

      {/* Jobs List */}
      {isLoading ? (
        <PageLoader message="Loading jobs..." />
      ) : jobs.length === 0 ? (
        <EmptyState
          icon={BriefcaseIcon}
          title="No jobs found"
          description={
            Object.values(filters).some(Boolean)
              ? "No jobs match your current filters. Try adjusting your search."
              : "You haven't created any scraping jobs yet. Start by creating your first job!"
          }
          action={
            Object.values(filters).some(Boolean) ? (
              <Button variant="secondary" onClick={handleClearFilters}>
                Clear Filters
              </Button>
            ) : (
              <Link to="/scraper">
                <Button icon={PlusIcon}>Create Your First Job</Button>
              </Link>
            )
          }
        />
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {jobs.map((job) => (
            <JobCard key={job.job_id} job={job} />
          ))}
        </div>
      ) : (
        <Card padding="none">
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {jobs.map((job) => (
              <JobCardCompact key={job.job_id} job={job} />
            ))}
          </div>
        </Card>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center">
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={handlePageChange}
          />
        </div>
      )}
    </div>
  )
}