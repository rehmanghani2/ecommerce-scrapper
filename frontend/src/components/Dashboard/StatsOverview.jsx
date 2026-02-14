import React from 'react'
import {
  BriefcaseIcon,
  CubeIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
} from '@heroicons/react/24/outline'
import { cn, formatNumber, formatPercent } from '@/utils/helpers'
import { StatCard } from '@/components/Common'
import { useJobStats } from '@/hooks/useJobs'

export function StatsOverview() {
  const { data: stats, isLoading } = useJobStats()

  const statCards = [
    {
      title: 'Total Jobs',
      value: formatNumber(stats?.total_jobs || 0),
      icon: BriefcaseIcon,
      iconColor: 'primary',
      change: '+12% from last week',
      changeType: 'positive',
    },
    {
      title: 'Products Scraped',
      value: formatNumber(stats?.total_products || 0),
      icon: CubeIcon,
      iconColor: 'success',
      change: '+23% from last week',
      changeType: 'positive',
    },
    {
      title: 'Pages Processed',
      value: formatNumber(stats?.total_pages || 0),
      icon: DocumentTextIcon,
      iconColor: 'warning',
    },
    {
      title: 'Success Rate',
      value: formatPercent(stats?.success_rate || 0),
      icon: CheckCircleIcon,
      iconColor: stats?.success_rate >= 90 ? 'success' : 'warning',
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
      {statCards.map((stat) => (
        <StatCard
          key={stat.title}
          title={stat.title}
          value={stat.value}
          icon={stat.icon}
          iconColor={stat.iconColor}
          change={stat.change}
          changeType={stat.changeType}
          loading={isLoading}
        />
      ))}
    </div>
  )
}

export default StatsOverview