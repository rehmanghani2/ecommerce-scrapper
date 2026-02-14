import React from 'react'
import { Link } from 'react-router-dom'
import { HomeIcon, ArrowLeftIcon } from '@heroicons/react/24/outline'
import { Button } from '@/components/Common'

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
      <div className="text-center">
        {/* 404 illustration */}
        <div className="mb-8">
          <h1 className="text-9xl font-bold text-gray-200 dark:text-gray-800">
            404
          </h1>
        </div>

        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Page Not Found
        </h2>
        
        <p className="text-gray-500 dark:text-gray-400 mb-8 max-w-md mx-auto">
          Sorry, the page you're looking for doesn't exist or has been moved.
        </p>

        <div className="flex items-center justify-center gap-4">
          <Button
            variant="secondary"
            icon={ArrowLeftIcon}
            onClick={() => window.history.back()}
          >
            Go Back
          </Button>
          
          <Link to="/">
            <Button icon={HomeIcon}>
              Back to Home
            </Button>
          </Link>
        </div>

        {/* Quick links */}
        <div className="mt-12">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Here are some helpful links:
          </p>
          <div className="flex items-center justify-center gap-6">
            {[
              { to: '/', label: 'Dashboard' },
              { to: '/scraper', label: 'Scraper' },
              { to: '/jobs', label: 'Jobs' },
              { to: '/products', label: 'Products' },
            ].map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="text-primary-600 hover:text-primary-700 dark:text-primary-400 text-sm"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}