import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Cog6ToothIcon,
  UserCircleIcon,
  KeyIcon,
  BellIcon,
  GlobeAltIcon,
  PaintBrushIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/utils/helpers'
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  Input,
  Select,
  Alert,
  UnderlineTabs,
} from '@/components/Common'
import toast from 'react-hot-toast'

export default function Settings() {
  const { user, refreshUser } = useAuth()
  const [activeTab, setActiveTab] = useState(0)

  const tabs = [
    {
      key: 'profile',
      label: 'Profile',
      icon: UserCircleIcon,
      content: <ProfileSettings user={user} onUpdate={refreshUser} />,
    },
    {
      key: 'security',
      label: 'Security',
      icon: ShieldCheckIcon,
      content: <SecuritySettings />,
    },
    {
      key: 'notifications',
      label: 'Notifications',
      icon: BellIcon,
      content: <NotificationSettings />,
    },
    {
      key: 'scraping',
      label: 'Scraping',
      icon: GlobeAltIcon,
      content: <ScrapingSettings />,
    },
    {
      key: 'appearance',
      label: 'Appearance',
      icon: PaintBrushIcon,
      content: <AppearanceSettings />,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
          <Cog6ToothIcon className="w-8 h-8 text-primary-600" />
          Settings
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Manage your account and application preferences
        </p>
      </div>

      {/* Tabs */}
      <UnderlineTabs
        tabs={tabs}
        selectedIndex={activeTab}
        onChange={setActiveTab}
      />
    </div>
  )
}

function ProfileSettings({ user, onUpdate }) {
  const [formData, setFormData] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
    username: user?.username || '',
  })

  const handleChange = (key, value) => {
    setFormData((prev) => ({ ...prev, [key]: value }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    // Would call API to update profile
    toast.success('Profile updated successfully')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile Information</CardTitle>
      </CardHeader>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Full Name"
          value={formData.full_name}
          onChange={(e) => handleChange('full_name', e.target.value)}
        />
        
        <Input
          label="Email"
          type="email"
          value={formData.email}
          onChange={(e) => handleChange('email', e.target.value)}
        />
        
        <Input
          label="Username"
          value={formData.username}
          onChange={(e) => handleChange('username', e.target.value)}
          disabled
          hint="Username cannot be changed"
        />
        
        <div className="pt-4">
          <Button type="submit">Save Changes</Button>
        </div>
      </form>
    </Card>
  )
}

function SecuritySettings() {
  const [passwords, setPasswords] = useState({
    current: '',
    new: '',
    confirm: '',
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    
    if (passwords.new !== passwords.confirm) {
      toast.error('New passwords do not match')
      return
    }
    
    // Would call API to change password
    toast.success('Password changed successfully')
    setPasswords({ current: '', new: '', confirm: '' })
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Change Password</CardTitle>
        </CardHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Current Password"
            type="password"
            value={passwords.current}
            onChange={(e) => setPasswords((p) => ({ ...p, current: e.target.value }))}
          />
          
          <Input
            label="New Password"
            type="password"
            value={passwords.new}
            onChange={(e) => setPasswords((p) => ({ ...p, new: e.target.value }))}
          />
          
          <Input
            label="Confirm New Password"
            type="password"
            value={passwords.confirm}
            onChange={(e) => setPasswords((p) => ({ ...p, confirm: e.target.value }))}
          />
          
          <div className="pt-4">
            <Button type="submit">Update Password</Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>API Key</CardTitle>
        </CardHeader>
        
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Use this API key to access the scraper programmatically.
          </p>
          
          <div className="flex gap-2">
            <Input
              value="sk_live_xxxxxxxxxxxxxxxxxxxx"
              readOnly
              className="font-mono"
            />
            <Button variant="secondary">
              Regenerate
            </Button>
          </div>
          
          <Alert variant="warning">
            Keep your API key secret. Do not share it publicly.
          </Alert>
        </div>
      </Card>
    </div>
  )
}

function NotificationSettings() {
  const [settings, setSettings] = useState({
    email_job_completed: true,
    email_job_failed: true,
    email_weekly_report: false,
    push_job_completed: true,
    push_job_failed: true,
  })

  const handleToggle = (key) => {
    setSettings((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Notification Preferences</CardTitle>
      </CardHeader>
      
      <div className="space-y-6">
        <div>
          <h4 className="font-medium text-gray-900 dark:text-white mb-3">Email Notifications</h4>
          <div className="space-y-3">
            <ToggleItem
              label="Job completed"
              description="Receive an email when a scraping job finishes successfully"
              checked={settings.email_job_completed}
              onChange={() => handleToggle('email_job_completed')}
            />
            <ToggleItem
              label="Job failed"
              description="Receive an email when a scraping job fails"
              checked={settings.email_job_failed}
              onChange={() => handleToggle('email_job_failed')}
            />
            <ToggleItem
              label="Weekly report"
              description="Receive a weekly summary of your scraping activity"
              checked={settings.email_weekly_report}
              onChange={() => handleToggle('email_weekly_report')}
            />
          </div>
        </div>

        <div className="border-t dark:border-gray-700 pt-6">
          <h4 className="font-medium text-gray-900 dark:text-white mb-3">Push Notifications</h4>
          <div className="space-y-3">
            <ToggleItem
              label="Job completed"
              description="Get a browser notification when a job finishes"
              checked={settings.push_job_completed}
              onChange={() => handleToggle('push_job_completed')}
            />
            <ToggleItem
              label="Job failed"
              description="Get a browser notification when a job fails"
              checked={settings.push_job_failed}
              onChange={() => handleToggle('push_job_failed')}
            />
          </div>
        </div>

        <div className="pt-4">
          <Button>Save Preferences</Button>
        </div>
      </div>
    </Card>
  )
}

function ScrapingSettings() {
  const [settings, setSettings] = useState({
    default_max_pages: 100,
    default_max_products: 10000,
    default_delay: 1000,
    use_proxy: false,
    headless: true,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Default Scraping Settings</CardTitle>
      </CardHeader>
      
      <div className="space-y-4">
        <Input
          label="Default Max Pages"
          type="number"
          value={settings.default_max_pages}
          onChange={(e) => setSettings((s) => ({ ...s, default_max_pages: parseInt(e.target.value) }))}
          hint="Maximum pages to scrape per job"
        />
        
        <Input
          label="Default Max Products"
          type="number"
          value={settings.default_max_products}
          onChange={(e) => setSettings((s) => ({ ...s, default_max_products: parseInt(e.target.value) }))}
          hint="Maximum products to extract per job"
        />
        
        <Input
          label="Request Delay (ms)"
          type="number"
          value={settings.default_delay}
          onChange={(e) => setSettings((s) => ({ ...s, default_delay: parseInt(e.target.value) }))}
          hint="Delay between requests to avoid rate limiting"
        />

        <div className="space-y-3 pt-4 border-t dark:border-gray-700">
          <ToggleItem
            label="Use Proxy"
            description="Route requests through proxy servers"
            checked={settings.use_proxy}
            onChange={() => setSettings((s) => ({ ...s, use_proxy: !s.use_proxy }))}
          />
          <ToggleItem
            label="Headless Mode"
            description="Run browser in headless mode (faster)"
            checked={settings.headless}
            onChange={() => setSettings((s) => ({ ...s, headless: !s.headless }))}
          />
        </div>

        <div className="pt-4">
          <Button>Save Settings</Button>
        </div>
      </div>
    </Card>
  )
}

function AppearanceSettings() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'system'
  })

  const handleThemeChange = (newTheme) => {
    setTheme(newTheme)
    localStorage.setItem('theme', newTheme)
    
    if (newTheme === 'dark' || (newTheme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    
    toast.success('Theme updated')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Appearance</CardTitle>
      </CardHeader>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Theme
          </label>
          <div className="grid grid-cols-3 gap-3">
            {[
              { value: 'light', label: 'Light' },
              { value: 'dark', label: 'Dark' },
              { value: 'system', label: 'System' },
            ].map((option) => (
              <button
                key={option.value}
                onClick={() => handleThemeChange(option.value)}
                className={cn(
                  'p-4 rounded-lg border-2 transition-all',
                  theme === option.value
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                )}
              >
                <span className="font-medium text-gray-900 dark:text-white">
                  {option.label}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </Card>
  )
}

function ToggleItem({ label, description, checked, onChange }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="font-medium text-gray-900 dark:text-white">{label}</p>
        <p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
      </div>
      <button
        onClick={onChange}
        className={cn(
          'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
          checked ? 'bg-primary-600' : 'bg-gray-200 dark:bg-gray-700'
        )}
      >
        <span
          className={cn(
            'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
            checked ? 'translate-x-6' : 'translate-x-1'
          )}
        />
      </button>
    </div>
  )
}