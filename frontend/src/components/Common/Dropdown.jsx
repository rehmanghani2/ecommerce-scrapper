import React, { Fragment } from 'react'
import { Menu, Transition } from '@headlessui/react'
import { ChevronDownIcon } from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'

export function Dropdown({
  trigger,
  children,
  align = 'right',
  width = 'w-56',
  className,
}) {
  const alignmentClasses = {
    left: 'left-0',
    right: 'right-0',
    center: 'left-1/2 -translate-x-1/2',
  }

  return (
    <Menu as="div" className={cn('relative inline-block text-left', className)}>
      <Menu.Button as={Fragment}>{trigger}</Menu.Button>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <Menu.Items
          className={cn(
            'absolute z-50 mt-2 origin-top-right rounded-lg',
            'bg-white dark:bg-gray-800 shadow-lg ring-1 ring-black ring-opacity-5',
            'focus:outline-none py-1',
            alignmentClasses[align],
            width
          )}
        >
          {children}
        </Menu.Items>
      </Transition>
    </Menu>
  )
}

export function DropdownItem({
  children,
  icon: Icon,
  onClick,
  disabled = false,
  danger = false,
  className,
}) {
  return (
    <Menu.Item disabled={disabled}>
      {({ active }) => (
        <button
          onClick={onClick}
          className={cn(
            'flex w-full items-center px-4 py-2 text-sm',
            active && !danger && 'bg-gray-100 dark:bg-gray-700',
            active && danger && 'bg-danger-50 dark:bg-danger-900/20',
            danger ? 'text-danger-600 dark:text-danger-400' : 'text-gray-700 dark:text-gray-200',
            disabled && 'opacity-50 cursor-not-allowed',
            className
          )}
          disabled={disabled}
        >
          {Icon && <Icon className="w-4 h-4 mr-3" />}
          {children}
        </button>
      )}
    </Menu.Item>
  )
}

export function DropdownDivider() {
  return <div className="my-1 border-t border-gray-100 dark:border-gray-700" />
}

export function DropdownLabel({ children, className }) {
  return (
    <div className={cn('px-4 py-2 text-xs font-semibold text-gray-500 uppercase', className)}>
      {children}
    </div>
  )
}

// Dropdown Button (combines button with dropdown)
export function DropdownButton({
  label,
  children,
  variant = 'secondary',
  size = 'md',
  icon: Icon,
  ...props
}) {
  return (
    <Dropdown
      trigger={
        <button
          className={cn(
            'inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-lg',
            'transition-all duration-200',
            'focus:outline-none focus:ring-2 focus:ring-offset-2',
            variant === 'primary' && 'bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500',
            variant === 'secondary' && 'bg-gray-200 text-gray-900 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-100 dark:hover:bg-gray-600'
          )}
        >
          {Icon && <Icon className="w-4 h-4 mr-2" />}
          {label}
          <ChevronDownIcon className="w-4 h-4 ml-2" />
        </button>
      }
      {...props}
    >
      {children}
    </Dropdown>
  )
}

export default Dropdown