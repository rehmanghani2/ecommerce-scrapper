import React from 'react'
import { Link } from 'react-router-dom'
import {
  PlusIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
  BoltIcon,
  SparklesIcon,
  GlobeAltIcon,
  CubeIcon,
  MagnifyingGlassIcon,
  DocumentChartBarIcon,
  ServerStackIcon,
  ScaleIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '@/hooks/useAuth'
import { useJobStats, useJobs } from '@/hooks/useJobs'
import { cn, formatRelativeTime } from '@/utils/helpers'
import { Button, Card, CardHeader, CardTitle } from '@/components/Common'
import { StatsOverview, RecentJobs, ActivityChart, JobsStatusChart } from '@/components/Dashboard'

const INTELLIGENCE_CAPABILITIES = [
  {
    title: 'Dual-Engine & Sitemap Crawler',
    desc: 'Playwright stealth browser, AI selector picker & 10,000+ URL parallel sitemap importer.',
    href: '/scraper',
    badge: 'Core Engine',
    icon: GlobeAltIcon,
    color: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/50',
  },
  {
    title: 'Product Intelligence Suite',
    desc: 'AI pricing simulator, stockout forecasting, review sentiment, Buy Box & competitor clusters.',
    href: '/products',
    badge: '8 AI Tools',
    icon: CubeIcon,
    color: 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/50',
  },
  {
    title: 'SERP & Keyword Visibility',
    desc: 'Track organic vs. sponsored rankings, share-of-voice & price positioning by keyword.',
    href: '/serp',
    badge: 'Rankings',
    icon: MagnifyingGlassIcon,
    color: 'text-cyan-600 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-950/50',
  },
  {
    title: 'Executive Market Reports',
    desc: 'Generate comprehensive competitive intelligence digests in PDF and multi-tab Excel.',
    href: '/reports',
    badge: 'PDF / XLSX',
    icon: DocumentChartBarIcon,
    color: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50',
  },
  {
    title: 'Proxy Pool & Anti-Bot Health',
    desc: 'Real-time proxy latency benchmarks, 403/429 auto-failover & domain health telemetry.',
    href: '/proxies',
    badge: 'Stealth',
    icon: ServerStackIcon,
    color: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/50',
  },
  {
    title: 'Auto-Repricing & Webhooks',
    desc: 'Dynamic competitor undercut rules, multi-currency FX, Shopify/Woo sync & Slack/Telegram alerts.',
    href: '/settings?tab=repricing',
    badge: 'Automation',
    icon: ScaleIcon,
    color: 'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/50',
  },
]

export default function Dashboard() {
  const { user } = useAuth()
  const { data: stats } = useJobStats()
  const { data: latestJobsData } = useJobs({ page_size: 4 })

  const activeJobsCount = stats?.running_jobs || 0
  const latestJobs = latestJobsData?.jobs || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Welcome back, {user?.full_name || user?.username || 'User'}!
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1 text-sm">
            Real-time overview of your e-commerce scraping pipelines and competitive intelligence suite.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link to="/products">
            <Button variant="secondary" icon={SparklesIcon}>
              Explore Catalog AI
            </Button>
          </Link>
          <Link to="/scraper">
            <Button icon={PlusIcon}>New Scraping Job</Button>
          </Link>
        </div>
      </div>

      {/* Active Jobs Alert */}
      {activeJobsCount > 0 && (
        <div className="bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
                <BoltIcon className="w-5 h-5 text-primary-600 dark:text-primary-400 animate-pulse" />
              </div>
              <div>
                <p className="font-medium text-primary-900 dark:text-primary-100">
                  {activeJobsCount} job{activeJobsCount > 1 ? 's' : ''} currently running
                </p>
                <p className="text-sm text-primary-700 dark:text-primary-300">
                  Monitor live progress, processed pages, and extracted products.
                </p>
              </div>
            </div>
            <Link to="/jobs?status=running">
              <Button variant="outline" size="sm">
                Monitor Live
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* Stats Overview */}
      <StatsOverview />

      {/* Platform Intelligence & Capabilities Hub */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-2">
            <SparklesIcon className="w-4 h-4 text-primary-500" />
            Platform Capabilities & Intelligence Suite
          </h2>
          <Link
            to="/settings"
            className="text-xs font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400 flex items-center gap-1"
          >
            Configure Integrations <ArrowRightIcon className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {INTELLIGENCE_CAPABILITIES.map((cap) => (
            <Link
              key={cap.title}
              to={cap.href}
              className="group bg-white dark:bg-gray-800/90 rounded-xl border border-gray-200/80 dark:border-gray-700/80 p-4 hover:border-primary-400 dark:hover:border-primary-500 hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <div className={cn('p-2.5 rounded-xl transition-transform group-hover:scale-105', cap.color)}>
                    <cap.icon className="w-5 h-5" />
                  </div>
                  <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700/70 dark:text-gray-300">
                    {cap.badge}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors text-sm">
                  {cap.title}
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">
                  {cap.desc}
                </p>
              </div>
              <div className="mt-3 pt-2.5 border-t border-gray-100 dark:border-gray-700/50 flex items-center justify-between text-xs font-medium text-primary-600 dark:text-primary-400">
                <span>Launch Module</span>
                <ArrowRightIcon className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Charts and Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ActivityChart />
        </div>
        <div>
          <JobsStatusChart />
        </div>
      </div>

      {/* Recent Jobs and Quick Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RecentJobs />
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ArrowTrendingUpIcon className="w-5 h-5 text-primary-500" />
                Performance Metrics
              </CardTitle>
            </CardHeader>

            <div className="space-y-3.5">
              <QuickStat label="Completed Jobs" value={stats?.completed_jobs ?? 0} />
              <QuickStat label="Failed Jobs" value={stats?.failed_jobs ?? 0} />
              <QuickStat label="Running Jobs" value={stats?.running_jobs ?? 0} />
              <QuickStat
                label="Average Duration"
                value={stats?.average_duration
                  ? `${Math.max(1, Math.round(stats.average_duration / 60))} min`
                  : '—'}
              />
            </div>
          </Card>

          {/* Dynamic Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ClockIcon className="w-5 h-5 text-primary-500" />
                Live Pipeline Feed
              </CardTitle>
            </CardHeader>

            {latestJobs.length > 0 ? (
              <div className="space-y-3">
                {latestJobs.map((job) => (
                  <Link
                    key={job.job_id}
                    to={`/jobs/${job.job_id}`}
                    className="flex items-start gap-3 p-1.5 -mx-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors"
                  >
                    <div
                      className={cn(
                        'w-2 h-2 rounded-full mt-2 shrink-0',
                        job.status === 'completed' && 'bg-emerald-500',
                        job.status === 'running' && 'bg-blue-500 animate-ping',
                        job.status === 'failed' && 'bg-rose-500',
                        job.status === 'pending' && 'bg-amber-500'
                      )}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {job.name || job.domain}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {job.status === 'completed'
                          ? `Extracted ${job.total_products || 0} products`
                          : `Status: ${job.status}`}
                      </p>
                    </div>
                    <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
                      {job.created_at ? formatRelativeTime(job.created_at) : ''}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-500 dark:text-gray-400 py-2">
                No recent jobs recorded yet. Launch a scrape to see live pipeline activity.
              </p>
            )}
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