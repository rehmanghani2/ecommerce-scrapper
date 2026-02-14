import React, { forwardRef, Fragment } from 'react'
import { Listbox, Transition } from '@headlessui/react'
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'

export const Select = forwardRef(({
  label,
  options = [],
  value,
  onChange,
  placeholder = 'Select an option',
  error,
  disabled = false,
  className,
}, ref) => {
  const selectedOption = options.find(opt => opt.value === value)

  return (
    <div className={cn('w-full', className)} ref={ref}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {label}
        </label>
      )}
      
      <Listbox value={value} onChange={onChange} disabled={disabled}>
        <div className="relative">
          <Listbox.Button
            className={cn(
              'relative w-full cursor-pointer rounded-lg border bg-white py-2 pl-4 pr-10 text-left',
              'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
              'dark:bg-gray-800 dark:border-gray-600',
              'disabled:bg-gray-100 disabled:cursor-not-allowed',
              error ? 'border-danger-500' : 'border-gray-300 dark:border-gray-600'
            )}
          >
            <span className={cn(
              'block truncate text-sm',
              selectedOption ? 'text-gray-900 dark:text-gray-100' : 'text-gray-400'
            )}>
              {selectedOption ? selectedOption.label : placeholder}
            </span>
            <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
              <ChevronUpDownIcon className="h-5 w-5 text-gray-400" aria-hidden="true" />
            </span>
          </Listbox.Button>
          
          <Transition
            as={Fragment}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Listbox.Options
              className={cn(
                'absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-lg',
                'bg-white py-1 text-sm shadow-lg ring-1 ring-black ring-opacity-5',
                'focus:outline-none dark:bg-gray-800'
              )}
            >
              {options.map((option) => (
                <Listbox.Option
                  key={option.value}
                  value={option.value}
                  disabled={option.disabled}
                  className={({ active, selected }) =>
                    cn(
                      'relative cursor-pointer select-none py-2 pl-10 pr-4',
                      active ? 'bg-primary-50 text-primary-900 dark:bg-primary-900/20 dark:text-primary-100' : 'text-gray-900 dark:text-gray-100',
                      option.disabled && 'opacity-50 cursor-not-allowed'
                    )
                  }
                >
                  {({ selected }) => (
                    <>
                      <span className={cn('block truncate', selected && 'font-medium')}>
                        {option.label}
                      </span>
                      {selected && (
                        <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-primary-600 dark:text-primary-400">
                          <CheckIcon className="h-5 w-5" aria-hidden="true" />
                        </span>
                      )}
                    </>
                  )}
                </Listbox.Option>
              ))}
            </Listbox.Options>
          </Transition>
        </div>
      </Listbox>
      
      {error && (
        <p className="mt-1 text-sm text-danger-600">{error}</p>
      )}
    </div>
  )
})

Select.displayName = 'Select'

export default Select