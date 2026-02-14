import React from 'react'
import { Tab } from '@headlessui/react'
import { cn } from '@/utils/helpers'

export function Tabs({ tabs, selectedIndex, onChange, className }) {
  return (
    <Tab.Group selectedIndex={selectedIndex} onChange={onChange}>
      <Tab.List
        className={cn(
          'flex space-x-1 rounded-xl bg-gray-100 dark:bg-gray-800 p-1',
          className
        )}
      >
        {tabs.map((tab) => (
          <Tab
            key={tab.key}
            disabled={tab.disabled}
            className={({ selected }) =>
              cn(
                'w-full rounded-lg py-2.5 text-sm font-medium leading-5',
                'ring-white ring-opacity-60 ring-offset-2 ring-offset-primary-400 focus:outline-none focus:ring-2',
                'transition-all duration-200',
                selected
                  ? 'bg-white dark:bg-gray-700 text-primary-700 dark:text-primary-400 shadow'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-700/50 hover:text-gray-800 dark:hover:text-gray-200',
                tab.disabled && 'opacity-50 cursor-not-allowed'
              )
            }
          >
            <div className="flex items-center justify-center gap-2">
              {tab.icon && <tab.icon className="w-4 h-4" />}
              {tab.label}
              {tab.count !== undefined && (
                <span className="px-2 py-0.5 text-xs rounded-full bg-gray-200 dark:bg-gray-600">
                  {tab.count}
                </span>
              )}
            </div>
          </Tab>
        ))}
      </Tab.List>
      
      <Tab.Panels className="mt-4">
        {tabs.map((tab) => (
          <Tab.Panel
            key={tab.key}
            className={cn(
              'rounded-xl focus:outline-none',
              'ring-white ring-opacity-60 ring-offset-2 ring-offset-primary-400 focus:ring-2'
            )}
          >
            {tab.content}
          </Tab.Panel>
        ))}
      </Tab.Panels>
    </Tab.Group>
  )
}

// Underline style tabs
export function UnderlineTabs({ tabs, selectedIndex, onChange, className }) {
  return (
    <Tab.Group selectedIndex={selectedIndex} onChange={onChange}>
      <Tab.List
        className={cn(
          'flex border-b border-gray-200 dark:border-gray-700',
          className
        )}
      >
        {tabs.map((tab) => (
          <Tab
            key={tab.key}
            disabled={tab.disabled}
            className={({ selected }) =>
              cn(
                'px-4 py-2.5 text-sm font-medium focus:outline-none',
                'border-b-2 -mb-px transition-colors duration-200',
                selected
                  ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300',
                tab.disabled && 'opacity-50 cursor-not-allowed'
              )
            }
          >
            <div className="flex items-center gap-2">
              {tab.icon && <tab.icon className="w-4 h-4" />}
              {tab.label}
              {tab.count !== undefined && (
                <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-700">
                  {tab.count}
                </span>
              )}
            </div>
          </Tab>
        ))}
      </Tab.List>
      
      <Tab.Panels className="mt-4">
        {tabs.map((tab) => (
          <Tab.Panel key={tab.key} className="focus:outline-none">
            {tab.content}
          </Tab.Panel>
        ))}
      </Tab.Panels>
    </Tab.Group>
  )
}

export default Tabs