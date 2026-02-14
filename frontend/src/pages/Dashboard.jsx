import React from 'react'
import { Link } from 'react-router-dom'
import {
  PlusIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
  BoltIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '@/hooks/useAuth'
import { useJobStats, useJobs } from '@/hooks/useJobs'
import { cn, formatNumber, formatRelativeTime } from '@/utils/helpers'
import { Button, Card, CardHeader, CardTitle, Badge } from '@/components/Common'
import { StatsOverview, RecentJobs, ActivityChart, JobsStatusChart } from '@/components/Dashboard'

export default function Dashboard() {
  const { user } = useAuth()
  const { data: stats } = useJobStats()
  const { data: runningJobs } = useJobs({ status: 'running', page_size: 5 })

  const activeJobsCount = runningJobs?.jobs?.length || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Welcome back, {user?.full_name || user?.username || 'User'}!
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Here's what's happening with your scraping jobs.
          </p>
        </div>
        
        <Link to="/scraper">
          <Button icon={PlusIcon} size="lg">
            New Scraping Job
          </Button>
        </Link>
      </div>

      {/* Active Jobs Alert */}
      {activeJobsCount > 0 && (
        <div className="bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
                <BoltIcon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <p className="font-medium text-primary-900 dark:text-primary-100">
                  {activeJobsCount} job{activeJobsCount > 1 ? 's' : ''} currently running
                </p>
                <p className="text-sm text-primary-700 dark:text-primary-300">
                  {formatNumber(runningJobs?.jobs?.reduce((sum, j) => sum + (j.total_products || 0), 0) || 0)} products scraped so far
                </p>
              </div>
            </div>
            <Link to="/jobs?status=running">
              <Button variant="outline" size="sm">
                View Jobs
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* Stats Overview */}
      <StatsOverview />

      {/* Charts and Recent Jobs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Chart - Takes 2 columns */}
        <div className="lg:col-span-2">
          <ActivityChart />
        </div>
        
        {/* Jobs by Status */}
        <div>
          <JobsStatusChart />
        </div>
      </div>

      {/* Recent Jobs and Quick Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Jobs - Takes 2 columns */}
        <div className="lg:col-span-2">
          <RecentJobs />
        </div>
        
        {/* Quick Stats */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ArrowTrendingUpIcon className="w-5 h-5" />
                Quick Stats
              </CardTitle>
            </CardHeader>
            
            <div className="space-y-4">
              <QuickStat
                label="Avg. Products per Job"
                value={stats?.total_jobs > 0 
                  ? Math.round(stats?.total_products / stats?.total_jobs) 
                  : 0}
              />
              <QuickStat
                label="Avg. Job Duration"
                value={stats?.average_duration 
                  ? `${Math.round(stats.average_duration / 60)} min` 
                  : '—'}
              />
              <QuickStat
                label="Total Domains Scraped"
                value={stats?.unique_domains || 0}
              />
              <QuickStat
                label="Jobs This Week"
                value={stats?.jobs_this_week || 0}
              />
            </div>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ClockIcon className="w-5 h-5" />
                Recent Activity
              </CardTitle>
            </CardHeader>
            
            <div className="space-y-3">
              {[
                { action: 'Job completed', target: 'leelicycles.co.uk', time: '2 min ago', type: 'success' },
                { action: 'Export created', target: 'products_export.csv', time: '15 min ago', type: 'info' },
                { action: 'New job started', target: 'ballicom.co.uk', time: '1 hour ago', type: 'primary' },
              ].map((activity, index) => (
                <div key={index} className="flex items-start gap-3">
                  <div className={cn(
                    'w-2 h-2 rounded-full mt-2',
                    activity.type === 'success' && 'bg-success-500',
                    activity.type === 'info' && 'bg-blue-500',
                    activity.type === 'primary' && 'bg-primary-500'
                  )} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900 dark:text-white">
                      {activity.action}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {activity.target}
                    </p>
                  </div>
                  <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
                    {activity.time}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

function QuickStat({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
      <span className="font-semibold text-gray-900 dark:text-white">{value}</span>
    </div>
  )
}