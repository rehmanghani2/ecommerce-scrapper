import React from 'react'
import { BellIcon, CheckIcon, TrashIcon } from '@heroicons/react/24/outline'
import { useNotifications } from '@/hooks/useNotifications'
import { Button, Card, EmptyState } from '@/components/Common'

function formatDate(value) {
  if (!value) return 'Just now'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
}

export default function Notifications() {
  const { notifications, unreadCount, markAsRead, clearNotifications } = useNotifications()

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-primary-50 p-2.5 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400">
              <BellIcon className="h-6 w-6" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Notifications</h1>
          </div>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Job updates and activity from your scraping workspace.
            {unreadCount > 0 ? ` ${unreadCount} unread.` : ' You are all caught up.'}
          </p>
        </div>
        {notifications.length > 0 && (
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => markAsRead()}>
              <CheckIcon className="mr-2 h-4 w-4" /> Mark all read
            </Button>
            <Button variant="ghost" onClick={clearNotifications}>
              <TrashIcon className="mr-2 h-4 w-4" /> Clear
            </Button>
          </div>
        )}
      </div>

      {notifications.length === 0 ? (
        <EmptyState icon={BellIcon} title="No notifications yet" description="When a scraping job starts, completes, or needs attention, updates will appear here." />
      ) : (
        <Card padding="none">
          <ul className="divide-y divide-gray-100 dark:divide-gray-800">
            {notifications.map((notification, index) => {
              const title = notification.data?.job_name || notification.type || 'Workspace update'
              const description = notification.data?.message || notification.message
              return (
                <li key={notification.id || `${notification.type}-${index}`}>
                  <div className={`flex gap-4 px-5 py-4 ${notification.read ? '' : 'bg-primary-50/50 dark:bg-primary-900/10'}`}>
                    <span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${notification.read ? 'bg-gray-300 dark:bg-gray-600' : 'bg-primary-600'}`} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-gray-900 dark:text-white">{title}</p>
                      {description && <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">{description}</p>}
                      <p className="mt-1 text-xs text-gray-400">{formatDate(notification.created_at)}</p>
                    </div>
                    {!notification.read && notification.id && (
                      <button type="button" onClick={() => markAsRead(notification.id)} className="self-start rounded-lg px-2 py-1 text-xs font-medium text-primary-700 hover:bg-primary-100 dark:text-primary-300 dark:hover:bg-primary-900/40">
                        Mark read
                      </button>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </Card>
      )}
    </div>
  )
}
