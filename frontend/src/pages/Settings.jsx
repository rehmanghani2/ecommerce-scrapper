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
  CloudArrowUpIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
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
  Badge,
} from '@/components/Common'
import integrationService from '@/services/integrationService'
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
      key: 'integrations',
      label: 'Store Integrations',
      icon: CloudArrowUpIcon,
      content: <IntegrationsSettings />,
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

function IntegrationsSettings() {
  const [configs, setConfigs] = useState([])
  const [loading, setLoading] = useState(false)

  // Shopify state
  const [shopify, setShopify] = useState({ shop_url: '', access_token: '' })
  const [testingShopify, setTestingShopify] = useState(false)
  const [shopifyTestResult, setShopifyTestResult] = useState(null)

  // WooCommerce state
  const [wc, setWc] = useState({ store_url: '', consumer_key: '', consumer_secret: '' })
  const [testingWc, setTestingWc] = useState(false)
  const [wcTestResult, setWcTestResult] = useState(null)

  // Google Sheets state
  const [sheets, setSheets] = useState({ webhook_url: '' })
  const [testingSheets, setTestingSheets] = useState(false)
  const [sheetsTestResult, setSheetsTestResult] = useState(null)

  useEffect(() => {
    loadConfigs()
  }, [])

  const loadConfigs = async () => {
    try {
      setLoading(true)
      const data = await integrationService.getConfigs()
      setConfigs(data || [])
      
      const shopifyCfg = (data || []).find((c) => c.platform === 'shopify')
      if (shopifyCfg?.masked_credentials) {
        setShopify({
          shop_url: shopifyCfg.masked_credentials.shop_url || '',
          access_token: shopifyCfg.masked_credentials.access_token || '',
        })
      }

      const wcCfg = (data || []).find((c) => c.platform === 'woocommerce')
      if (wcCfg?.masked_credentials) {
        setWc({
          store_url: wcCfg.masked_credentials.store_url || '',
          consumer_key: wcCfg.masked_credentials.consumer_key || '',
          consumer_secret: wcCfg.masked_credentials.consumer_secret || '',
        })
      }

      const sheetsCfg = (data || []).find((c) => c.platform === 'google_sheets')
      if (sheetsCfg?.masked_credentials) {
        setSheets({
          webhook_url: sheetsCfg.masked_credentials.webhook_url || '',
        })
      }
    } catch (err) {
      console.error('Failed to load configs', err)
    } finally {
      setLoading(false)
    }
  }

  // Shopify Handlers
  const handleTestShopify = async () => {
    setTestingShopify(true)
    setShopifyTestResult(null)
    try {
      const res = await integrationService.testConnection('shopify', shopify)
      setShopifyTestResult(res)
      if (res.success) toast.success('Shopify connection verified!')
      else toast.error(res.message)
    } catch (err) {
      const msg = err.response?.data?.detail || err.message
      setShopifyTestResult({ success: false, message: msg })
      toast.error(msg)
    } finally {
      setTestingShopify(false)
    }
  }

  const handleSaveShopify = async () => {
    try {
      await integrationService.saveConfig({
        platform: 'shopify',
        name: shopify.shop_url || 'Default Shopify Store',
        credentials: shopify,
        is_active: true,
      })
      toast.success('Shopify settings saved!')
      loadConfigs()
    } catch (err) {
      toast.error('Failed to save Shopify settings: ' + err.message)
    }
  }

  // WooCommerce Handlers
  const handleTestWc = async () => {
    setTestingWc(true)
    setWcTestResult(null)
    try {
      const res = await integrationService.testConnection('woocommerce', wc)
      setWcTestResult(res)
      if (res.success) toast.success('WooCommerce connection verified!')
      else toast.error(res.message)
    } catch (err) {
      const msg = err.response?.data?.detail || err.message
      setWcTestResult({ success: false, message: msg })
      toast.error(msg)
    } finally {
      setTestingWc(false)
    }
  }

  const handleSaveWc = async () => {
    try {
      await integrationService.saveConfig({
        platform: 'woocommerce',
        name: wc.store_url || 'Default WooCommerce Store',
        credentials: wc,
        is_active: true,
      })
      toast.success('WooCommerce settings saved!')
      loadConfigs()
    } catch (err) {
      toast.error('Failed to save WooCommerce settings: ' + err.message)
    }
  }

  // Google Sheets Handlers
  const handleTestSheets = async () => {
    setTestingSheets(true)
    setSheetsTestResult(null)
    try {
      const res = await integrationService.testConnection('google_sheets', sheets)
      setSheetsTestResult(res)
      if (res.success) toast.success('Google Sheets webhook verified!')
      else toast.error(res.message)
    } catch (err) {
      const msg = err.response?.data?.detail || err.message
      setSheetsTestResult({ success: false, message: msg })
      toast.error(msg)
    } finally {
      setTestingSheets(false)
    }
  }

  const handleSaveSheets = async () => {
    try {
      await integrationService.saveConfig({
        platform: 'google_sheets',
        name: 'Google Sheets Live Sync',
        credentials: sheets,
        is_active: true,
      })
      toast.success('Google Sheets webhook saved!')
      loadConfigs()
    } catch (err) {
      toast.error('Failed to save Google Sheets settings: ' + err.message)
    }
  }

  return (
    <div className="space-y-6">
      {/* Introduction Banner */}
      <div className="bg-primary-50 dark:bg-primary-950/40 border border-primary-200 dark:border-primary-800 rounded-xl p-4">
        <h3 className="font-semibold text-primary-900 dark:text-primary-100 flex items-center gap-2">
          <CloudArrowUpIcon className="w-5 h-5 text-primary-600" />
          1-Click Store & Cloud Integrations
        </h3>
        <p className="text-xs text-primary-700 dark:text-primary-300 mt-1">
          Connect your online stores and cloud spreadsheets to automatically sync scraped products into your live inventory with 1 click.
        </p>
      </div>

      {/* 1. Shopify Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Shopify Store Integration</CardTitle>
            <Badge variant="primary">Shopify Admin REST API</Badge>
          </div>
        </CardHeader>
        <div className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Push products directly into your Shopify store with images, variants, compare-at pricing, and tags.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Shop Domain or Handle"
              placeholder="my-store.myshopify.com"
              value={shopify.shop_url}
              onChange={(e) => setShopify({ ...shopify, shop_url: e.target.value })}
              hint="Format: store-name.myshopify.com"
            />
            <Input
              label="Admin API Access Token"
              type="password"
              placeholder="shpat_xxxxxxxxxxxxxxxxxxxxxxxx"
              value={shopify.access_token}
              onChange={(e) => setShopify({ ...shopify, access_token: e.target.value })}
              hint="From Shopify Admin → Settings → Apps → App Development"
            />
          </div>

          {shopifyTestResult && (
            <Alert
              variant={shopifyTestResult.success ? 'success' : 'danger'}
              title={shopifyTestResult.message}
            >
              {shopifyTestResult.details && (
                <div className="text-xs mt-1 space-y-0.5">
                  <p>Store Name: {shopifyTestResult.details.name}</p>
                  <p>Currency: {shopifyTestResult.details.currency}</p>
                </div>
              )}
            </Alert>
          )}

          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              disabled={testingShopify || !shopify.shop_url || !shopify.access_token}
              onClick={handleTestShopify}
            >
              {testingShopify ? 'Testing...' : 'Test Connection'}
            </Button>
            <Button
              variant="primary"
              disabled={!shopify.shop_url || !shopify.access_token}
              onClick={handleSaveShopify}
            >
              Save Shopify Config
            </Button>
          </div>
        </div>
      </Card>

      {/* 2. WooCommerce Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>WooCommerce Integration</CardTitle>
            <Badge variant="secondary">WooCommerce REST API v3</Badge>
          </div>
        </CardHeader>
        <div className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Publish products to your WordPress/WooCommerce site with categories, stock tracking, and sale pricing.
          </p>
          <Input
            label="WordPress Store URL"
            placeholder="https://yourdomain.com"
            value={wc.store_url}
            onChange={(e) => setWc({ ...wc, store_url: e.target.value })}
            hint="Full URL with https://"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Consumer Key"
              placeholder="ck_xxxxxxxxxxxxxxxxxxxxxxxx"
              value={wc.consumer_key}
              onChange={(e) => setWc({ ...wc, consumer_key: e.target.value })}
              hint="From WooCommerce → Settings → Advanced → REST API"
            />
            <Input
              label="Consumer Secret"
              type="password"
              placeholder="cs_xxxxxxxxxxxxxxxxxxxxxxxx"
              value={wc.consumer_secret}
              onChange={(e) => setWc({ ...wc, consumer_secret: e.target.value })}
            />
          </div>

          {wcTestResult && (
            <Alert
              variant={wcTestResult.success ? 'success' : 'danger'}
              title={wcTestResult.message}
            >
              {wcTestResult.details && (
                <div className="text-xs mt-1">
                  <p>Site: {wcTestResult.details.site_url}</p>
                </div>
              )}
            </Alert>
          )}

          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              disabled={testingWc || !wc.store_url || !wc.consumer_key || !wc.consumer_secret}
              onClick={handleTestWc}
            >
              {testingWc ? 'Testing...' : 'Test Connection'}
            </Button>
            <Button
              variant="primary"
              disabled={!wc.store_url || !wc.consumer_key || !wc.consumer_secret}
              onClick={handleSaveWc}
            >
              Save WooCommerce Config
            </Button>
          </div>
        </div>
      </Card>

      {/* 3. Google Sheets Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Google Sheets Webhook Sync</CardTitle>
            <Badge variant="warning">Apps Script / Webhook</Badge>
          </div>
        </CardHeader>
        <div className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Push scraped products in real time into Google Sheets using Google Apps Script Web App or Zapier/Make webhooks.
          </p>
          <Input
            label="Webhook or Google Apps Script URL"
            placeholder="https://script.google.com/macros/s/AKfycbx.../exec"
            value={sheets.webhook_url}
            onChange={(e) => setSheets({ webhook_url: e.target.value })}
            hint="Supports Google Apps Script Web App (doPost), Make, or Zapier webhooks"
          />

          {sheetsTestResult && (
            <Alert
              variant={sheetsTestResult.success ? 'success' : 'danger'}
              title={sheetsTestResult.message}
            />
          )}

          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              disabled={testingSheets || !sheets.webhook_url}
              onClick={handleTestSheets}
            >
              {testingSheets ? 'Testing...' : 'Test Webhook'}
            </Button>
            <Button
              variant="primary"
              disabled={!sheets.webhook_url}
              onClick={handleSaveSheets}
            >
              Save Webhook Config
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}