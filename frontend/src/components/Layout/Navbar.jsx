import React, { Fragment } from 'react'
import { Link } from 'react-router-dom'
import { Menu, Transition } from '@headlessui/react'
import {
  BellIcon,
  MoonIcon,
  SunIcon,
  UserCircleIcon,
  ArrowRightOnRectangleIcon,
  Cog6ToothIcon,
  Bars3Icon,
} from '@heroicons/react/24/outline'
import { cn, getInitials } from '@/utils/helpers'
import { useAuth } from '@/hooks/useAuth'
import { useNotifications } from '@/hooks/useNotifications'
import { Badge } from '@/components/Common'

export function Navbar({ onMenuClick, showMenuButton = false }) {
  const { user, logout } = useAuth()
  const { unreadCount, notifications, markAsRead } = useNotifications()
  const [darkMode, setDarkMode] = React.useState(
    document.documentElement.classList.contains('dark')
  )

  const toggleDarkMode = () => {
    document.documentElement.classList.toggle('dark')
    setDarkMode(!darkMode)
    localStorage.setItem('theme', darkMode ? 'light' : 'dark')
  }

  return (
    <header className="h-16 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between px-4 lg:px-6">
      {/* Left side */}
      <div className="flex items-center gap-4">
        {showMenuButton && (
          <button
            onClick={onMenuClick}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 lg:hidden"
          >
            <Bars3Icon className="w-6 h-6" />
          </button>
        )}
        
        {/* Breadcrumb or page title could go here */}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2">
        {/* Dark mode toggle */}
        <button
          onClick={toggleDarkMode}
          className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 transition-colors"
          title={darkMode ? 'Light mode' : 'Dark mode'}
        >
          {darkMode ? (
            <SunIcon className="w-5 h-5" />
          ) : (
            <MoonIcon className="w-5 h-5" />
          )}
        </button>

        {/* Notifications */}
        <Menu as="div" className="relative">
          <Menu.Button className="relative p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 transition-colors">
            <BellIcon className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-danger-500 text-white text-xs rounded-full flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </Menu.Button>

          <Transition
            as={Fragment}
            enter="transition ease-out duration-100"
            enterFrom="transform opacity-0 scale-95"
            enterTo="transform opacity-100 scale-100"
            leave="transition ease-in duration-75"
            leaveFrom="transform opacity-100 scale-100"
            leaveTo="transform opacity-0 scale-95"
          >
            <Menu.Items className="absolute right-0 mt-2 w-80 origin-top-right rounded-lg bg-white dark:bg-gray-800 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
              <div className="p-4 border-b dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    Notifications
                  </h3>
                  {unreadCount > 0 && (
                    <button
                      onClick={() => markAsRead()}
                      className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400"
                    >
                      Mark all read
                    </button>
                  )}
                </div>
              </div>
              
              <div className="max-h-96 overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                    No notifications
                  </div>
                ) : (
                  notifications.slice(0, 5).map((notification) => (
                    <Menu.Item key={notification.id}>
                      {({ active }) => (
                        <div
                          className={cn(
                            'px-4 py-3 cursor-pointer',
                            active && 'bg-gray-50 dark:bg-gray-700',
                            !notification.read && 'bg-primary-50/50 dark:bg-primary-900/10'
                          )}
                          onClick={() => markAsRead(notification.id)}
                        >
                          <p className="text-sm text-gray-900 dark:text-white">
                            {notification.data?.job_name || notification.type}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            {notification.created_at}
                          </p>
                        </div>
                      )}
                    </Menu.Item>
                  ))
                )}
              </div>
              
              <div className="p-2 border-t dark:border-gray-700">
                <Link
                  to="/notifications"
                  className="block w-full text-center py-2 text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400"
                >
                  View all notifications
                </Link>
              </div>
            </Menu.Items>
          </Transition>
        </Menu>

        {/* User menu */}
        <Menu as="div" className="relative">
          <Menu.Button className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            {user?.avatar ? (
              <img
                src={user.avatar}
                alt={user.full_name}
                className="w-8 h-8 rounded-full"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center text-sm font-medium text-primary-700 dark:text-primary-400">
                {getInitials(user?.full_name || user?.username || 'U')}
              </div>
            )}
            <span className="hidden md:block text-sm font-medium text-gray-700 dark:text-gray-300">
              {user?.full_name || user?.username}
            </span>
          </Menu.Button>

          <Transition
            as={Fragment}
            enter="transition ease-out duration-100"
            enterFrom="transform opacity-0 scale-95"
            enterTo="transform opacity-100 scale-100"
            leave="transition ease-in duration-75"
            leaveFrom="transform opacity-100 scale-100"
            leaveTo="transform opacity-0 scale-95"
          >
            <Menu.Items className="absolute right-0 mt-2 w-56 origin-top-right rounded-lg bg-white dark:bg-gray-800 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none py-1">
              <div className="px-4 py-3 border-b dark:border-gray-700">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {user?.full_name || user?.username}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {user?.email}
                </p>
              </div>

              <Menu.Item>
                {({ active }) => (
                  <Link
                    to="/settings"
                    className={cn(
                      'flex items-center gap-3 px-4 py-2 text-sm',
                      active ? 'bg-gray-100 dark:bg-gray-700' : '',
                      'text-gray-700 dark:text-gray-200'
                    )}
                  >
                    <Cog6ToothIcon className="w-4 h-4" />
                    Settings
                  </Link>
                )}
              </Menu.Item>

              <Menu.Item>
                {({ active }) => (
                  <button
                    onClick={logout}
                    className={cn(
                      'flex items-center gap-3 w-full px-4 py-2 text-sm',
                      active ? 'bg-gray-100 dark:bg-gray-700' : '',
                      'text-danger-600 dark:text-danger-400'
                    )}
                  >
                    <ArrowRightOnRectangleIcon className="w-4 h-4" />
                    Sign out
                  </button>
                )}
              </Menu.Item>
            </Menu.Items>
          </Transition>
        </Menu>
      </div>
    </header>
  )
}

export default Navbar