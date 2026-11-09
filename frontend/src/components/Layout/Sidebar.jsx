import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  HomeIcon,
  GlobeAltIcon,
  BriefcaseIcon,
  CubeIcon,
  ClockIcon,
  ArrowDownTrayIcon,
  ServerStackIcon,
  DocumentChartBarIcon,
  MagnifyingGlassIcon,
  Cog6ToothIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/utils/helpers'

const navigationGroups = [
  {
    title: 'Workspace',
    items: [
      { name: 'Dashboard', href: '/', icon: HomeIcon },
      { name: 'New Scrape', href: '/scraper', icon: GlobeAltIcon },
      { name: 'Scraping Jobs', href: '/jobs', icon: BriefcaseIcon },
      { name: 'Product Catalog', href: '/products', icon: CubeIcon, badge: 'AI' },
    ],
  },
  {
    title: 'Analytics',
    items: [
      { name: 'Search Rankings', href: '/serp', icon: MagnifyingGlassIcon, badge: 'SERP' },
      { name: 'Reports', href: '/reports', icon: DocumentChartBarIcon },
    ],
  },
  {
    title: 'Automation',
    items: [
      { name: 'Schedules', href: '/schedules', icon: ClockIcon },
      { name: 'Proxy Management', href: '/proxies', icon: ServerStackIcon },
      { name: 'Data Exports', href: '/exports', icon: ArrowDownTrayIcon },
    ],
  },
]

export function Sidebar({ collapsed, onToggle }) {
  const location = useLocation()
  const { user } = useAuth()

  const bottomItems = [
    ...(user?.is_superuser
      ? [{ name: 'Admin Portal', href: '/admin/dashboard', icon: ShieldCheckIcon, badge: 'Root' }]
      : []),
    { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
  ]

  const NavItem = ({ item }) => {
    const isActive =
      location.pathname === item.href ||
      (item.href !== '/' && location.pathname.startsWith(item.href))

    return (
      <NavLink
        to={item.href}
        className={cn(
          'flex items-center justify-between gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200',
          isActive
            ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400 shadow-sm ring-1 ring-primary-200/70 dark:ring-primary-800/60'
            : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800/70',
          collapsed && 'justify-center px-2'
        )}
        title={collapsed ? item.name : undefined}
      >
        <div className="flex items-center gap-3 min-w-0">
          <item.icon
            className={cn(
              'w-5 h-5 flex-shrink-0',
              isActive && 'text-primary-600 dark:text-primary-400'
            )}
          />
          {!collapsed && <span className="truncate">{item.name}</span>}
        </div>
        {!collapsed && item.badge && (
          <span
            className={cn(
              'text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0',
              isActive
                ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/60 dark:text-primary-300'
                : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
            )}
          >
            {item.badge}
          </span>
        )}
      </NavLink>
    )
  }

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 h-screen bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800',
        'flex flex-col transition-all duration-300 z-40',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo */}
      <div
        className={cn(
          'h-16 flex items-center border-b border-gray-200 dark:border-gray-800',
          collapsed ? 'justify-center px-2' : 'px-4'
        )}
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-600 to-indigo-600 flex items-center justify-center shadow-sm">
            <GlobeAltIcon className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <div>
              <span className="font-bold text-gray-900 dark:text-white block leading-none">
                CommerceIntel
              </span>
              <span className="text-[10px] font-medium text-gray-400 dark:text-gray-500">
                E-commerce Data Platform
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-4">
        {navigationGroups.map((group) => (
          <div key={group.title} className="space-y-1">
            {!collapsed && (
              <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1">
                {group.title}
              </p>
            )}
            {group.items.map((item) => (
              <NavItem key={item.name} item={item} />
            ))}
          </div>
        ))}
      </nav>

      {/* Bottom Navigation */}
      <div className="p-3 border-t border-gray-200 dark:border-gray-800 space-y-1">
        {bottomItems.map((item) => (
          <NavItem key={item.name} item={item} />
        ))}

        {/* Collapse Toggle */}
        <button
          onClick={onToggle}
          className={cn(
            'flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm font-medium',
            'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800',
            'transition-all duration-200',
            collapsed && 'justify-center px-2'
          )}
        >
          {collapsed ? (
            <ChevronRightIcon className="w-5 h-5" />
          ) : (
            <>
              <ChevronLeftIcon className="w-5 h-5" />
              <span>Collapse Sidebar</span>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}

export default Sidebar