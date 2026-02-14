import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  HomeIcon,
  GlobeAltIcon,
  BriefcaseIcon,
  CubeIcon,
  ArrowDownTrayIcon,
  Cog6ToothIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Scraper', href: '/scraper', icon: GlobeAltIcon },
  { name: 'Jobs', href: '/jobs', icon: BriefcaseIcon },
  { name: 'Products', href: '/products', icon: CubeIcon },
  { name: 'Exports', href: '/exports', icon: ArrowDownTrayIcon },
]

const bottomNavigation = [
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
]

export function Sidebar({ collapsed, onToggle }) {
  const location = useLocation()

  const NavItem = ({ item }) => {
    const isActive = location.pathname === item.href || 
      (item.href !== '/' && location.pathname.startsWith(item.href))

    return (
      <NavLink
        to={item.href}
        className={cn(
          'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
          isActive
            ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
            : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800',
          collapsed && 'justify-center px-2'
        )}
        title={collapsed ? item.name : undefined}
      >
        <item.icon className={cn('w-5 h-5 flex-shrink-0', isActive && 'text-primary-600 dark:text-primary-400')} />
        {!collapsed && <span>{item.name}</span>}
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
      <div className={cn(
        'h-16 flex items-center border-b border-gray-200 dark:border-gray-800',
        collapsed ? 'justify-center px-2' : 'px-4'
      )}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary-600 flex items-center justify-center">
            <GlobeAltIcon className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <span className="font-bold text-gray-900 dark:text-white">
              Scraper
            </span>
          )}
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {navigation.map((item) => (
          <NavItem key={item.name} item={item} />
        ))}
      </nav>

      {/* Bottom Navigation */}
      <div className="p-3 border-t border-gray-200 dark:border-gray-800 space-y-1">
        {bottomNavigation.map((item) => (
          <NavItem key={item.name} item={item} />
        ))}
        
        {/* Collapse Toggle */}
        <button
          onClick={onToggle}
          className={cn(
            'flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium',
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
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}

export default Sidebar