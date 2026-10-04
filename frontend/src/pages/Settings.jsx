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
  SparklesIcon,
  BellAlertIcon,
  ChatBubbleLeftRightIcon,
  PhotoIcon,
  ServerStackIcon,
  CircleStackIcon,
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
import scraperService from '@/services/scraperService'
import alertService from '@/services/alertService'
import cloudinaryService from '@/services/cloudinaryService'
import s3Service from '@/services/s3Service'
import supabaseService from '@/services/supabaseService'
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
      key: 'cloudinary',
      label: 'Cloudinary CDN',
      icon: PhotoIcon,
      content: <CloudinarySettings />,
    },
    {
      key: 's3',
      label: 'AWS S3 / Cloud Storage',
      icon: ServerStackIcon,
      content: <S3StorageSettings />,
    },
    {
      key: 'supabase',
      label: 'Supabase Free Storage',
      icon: CircleStackIcon,
      content: <SupabaseStorageSettings />,
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
  // Telegram State
  const [telegram, setTelegram] = useState({ bot_token: '', chat_id: '', min_drop_percentage: 5.0, is_active: true })
  const [testingTelegram, setTestingTelegram] = useState(false)
  const [telegramTestResult, setTelegramTestResult] = useState(null)

  // Slack State
  const [slack, setSlack] = useState({ webhook_url: '', min_drop_percentage: 5.0, is_active: true })
  const [testingSlack, setTestingSlack] = useState(false)
  const [slackTestResult, setSlackTestResult] = useState(null)

  // Discord State
  const [discord, setDiscord] = useState({ webhook_url: '', min_drop_percentage: 5.0, is_active: true })
  const [testingDiscord, setTestingDiscord] = useState(false)
  const [discordTestResult, setDiscordTestResult] = useState(null)

  // Alert Logs
  const [alertLogs, setAlertLogs] = useState([])
  const [loadingLogs, setLoadingLogs] = useState(false)

  useEffect(() => {
    loadAlertConfigs()
    loadAlertLogs()
  }, [])

  const loadAlertConfigs = async () => {
    try {
      const data = await alertService.getConfigs()
      const tg = (data || []).find((c) => c.channel === 'telegram')
      if (tg) {
        setTelegram({
          bot_token: tg.masked_credentials?.bot_token || '',
          chat_id: tg.masked_credentials?.chat_id || '',
          min_drop_percentage: tg.min_drop_percentage || 5.0,
          is_active: tg.is_active,
        })
      }
      const sl = (data || []).find((c) => c.channel === 'slack')
      if (sl) {
        setSlack({
          webhook_url: sl.masked_credentials?.webhook_url || '',
          min_drop_percentage: sl.min_drop_percentage || 5.0,
          is_active: sl.is_active,
        })
      }
      const dc = (data || []).find((c) => c.channel === 'discord')
      if (dc) {
        setDiscord({
          webhook_url: dc.masked_credentials?.webhook_url || '',
          min_drop_percentage: dc.min_drop_percentage || 5.0,
          is_active: dc.is_active,
        })
      }
    } catch (e) {
      console.error('Failed to load alert configs', e)
    }
  }

  const loadAlertLogs = async () => {
    try {
      setLoadingLogs(true)
      const logs = await alertService.getLogs(20)
      setAlertLogs(logs || [])
    } catch (e) {
      console.error('Failed to load alert logs', e)
    } finally {
      setLoadingLogs(false)
    }
  }

  // Telegram Handlers
  const handleTestTelegram = async () => {
    setTestingTelegram(true)
    setTelegramTestResult(null)
    try {
      const res = await alertService.testChannel('telegram', {
        bot_token: telegram.bot_token,
        chat_id: telegram.chat_id,
      })
      setTelegramTestResult(res)
      if (res.success) toast.success('Test alert sent to Telegram!')
      else toast.error(res.message)
    } catch (e) {
      toast.error('Telegram test failed: ' + (e.response?.data?.detail || e.message))
    } finally {
      setTestingTelegram(false)
    }
  }

  const handleSaveTelegram = async () => {
    try {
      await alertService.saveConfig({
        channel: 'telegram',
        name: 'Telegram Price Drop Alerts',
        is_active: telegram.is_active,
        min_drop_percentage: telegram.min_drop_percentage,
        credentials: { bot_token: telegram.bot_token, chat_id: telegram.chat_id },
      })
      toast.success('Telegram alert settings saved!')
      loadAlertConfigs()
    } catch (e) {
      toast.error('Failed to save Telegram settings: ' + e.message)
    }
  }

  // Slack Handlers
  const handleTestSlack = async () => {
    setTestingSlack(true)
    setSlackTestResult(null)
    try {
      const res = await alertService.testChannel('slack', {
        webhook_url: slack.webhook_url,
      })
      setSlackTestResult(res)
      if (res.success) toast.success('Test alert sent to Slack!')
      else toast.error(res.message)
    } catch (e) {
      toast.error('Slack test failed: ' + (e.response?.data?.detail || e.message))
    } finally {
      setTestingSlack(false)
    }
  }

  const handleSaveSlack = async () => {
    try {
      await alertService.saveConfig({
        channel: 'slack',
        name: 'Slack Price Drop Alerts',
        is_active: slack.is_active,
        min_drop_percentage: slack.min_drop_percentage,
        credentials: { webhook_url: slack.webhook_url },
      })
      toast.success('Slack alert settings saved!')
      loadAlertConfigs()
    } catch (e) {
      toast.error('Failed to save Slack settings: ' + e.message)
    }
  }

  // Discord Handlers
  const handleTestDiscord = async () => {
    setTestingDiscord(true)
    setDiscordTestResult(null)
    try {
      const res = await alertService.testChannel('discord', {
        webhook_url: discord.webhook_url,
      })
      setDiscordTestResult(res)
      if (res.success) toast.success('Test alert sent to Discord!')
      else toast.error(res.message)
    } catch (e) {
      toast.error('Discord test failed: ' + (e.response?.data?.detail || e.message))
    } finally {
      setTestingDiscord(false)
    }
  }

  const handleSaveDiscord = async () => {
    try {
      await alertService.saveConfig({
        channel: 'discord',
        name: 'Discord Price Drop Alerts',
        is_active: discord.is_active,
        min_drop_percentage: discord.min_drop_percentage,
        credentials: { webhook_url: discord.webhook_url },
      })
      toast.success('Discord alert settings saved!')
      loadAlertConfigs()
    } catch (e) {
      toast.error('Failed to save Discord settings: ' + e.message)
    }
  }

  return (
    <div className="space-y-6">
      {/* Intro Banner */}
      <div className="bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 rounded-xl p-4">
        <h3 className="font-semibold text-indigo-900 dark:text-indigo-100 flex items-center gap-2">
          <BellAlertIcon className="w-5 h-5 text-indigo-600" />
          Price Drop & Stock Alert Notification Center
        </h3>
        <p className="text-xs text-indigo-700 dark:text-indigo-300 mt-1">
          Receive real-time instant alerts on Telegram, Slack, or Discord whenever a competitor drops their price, runs a promotion, or changes inventory availability during scheduled crawls.
        </p>
      </div>

      {/* 1. Telegram Bot Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <span className="text-lg">✈️</span>
              Telegram Bot Alerts
            </CardTitle>
            <Badge variant="primary" className="bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300">
              Instant Push
            </Badge>
          </div>
        </CardHeader>
        <div className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Receive rich Markdown alerts with direct store links, previous price comparisons, and savings calculations on your private chat or team channel.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Telegram Bot Token"
              type="password"
              placeholder="123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
              value={telegram.bot_token}
              onChange={(e) => setTelegram({ ...telegram, bot_token: e.target.value })}
              hint="Create a bot via @BotFather on Telegram"
            />
            <Input
              label="Target Chat ID or @Channel"
              placeholder="-100123456789 or @my_channel"
              value={telegram.chat_id}
              onChange={(e) => setTelegram({ ...telegram, chat_id: e.target.value })}
              hint="Your personal user ID or channel ID"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center pt-2">
            <Input
              label="Minimum Price Drop Trigger (%)"
              type="number"
              value={telegram.min_drop_percentage}
              onChange={(e) => setTelegram({ ...telegram, min_drop_percentage: parseFloat(e.target.value) || 0 })}
              hint="Only trigger alerts if price drops by at least this percentage"
              min={1}
              max={100}
            />
            <div className="pt-2">
              <ToggleItem
                label="Enable Telegram Alerts"
                description="Deliver price drop notifications to Telegram"
                checked={telegram.is_active}
                onChange={() => setTelegram({ ...telegram, is_active: !telegram.is_active })}
              />
            </div>
          </div>

          {telegramTestResult && (
            <Alert
              variant={telegramTestResult.success ? 'success' : 'danger'}
              title={telegramTestResult.message}
            />
          )}

          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              disabled={testingTelegram || !telegram.bot_token || !telegram.chat_id}
              onClick={handleTestTelegram}
            >
              {testingTelegram ? 'Sending Test...' : 'Send Test Telegram Alert'}
            </Button>
            <Button
              variant="primary"
              disabled={!telegram.bot_token || !telegram.chat_id}
              onClick={handleSaveTelegram}
            >
              Save Telegram Config
            </Button>
          </div>
        </div>
      </Card>

      {/* 2. Slack Incoming Webhook Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <ChatBubbleLeftRightIcon className="w-5 h-5 text-emerald-500" />
              Slack Channel Alerts
            </CardTitle>
            <Badge variant="success">Incoming Webhook</Badge>
          </div>
        </CardHeader>
        <div className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Posts interactive Slack Block Kit cards with product photo, competitor pricing, savings percentages, and direct view links.
          </p>

          <Input
            label="Slack Incoming Webhook URL"
            type="password"
            placeholder="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
            value={slack.webhook_url}
            onChange={(e) => setSlack({ ...slack, webhook_url: e.target.value })}
            hint="From Slack App Directory → Incoming Webhooks"
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center pt-2">
            <Input
              label="Minimum Price Drop Trigger (%)"
              type="number"
              value={slack.min_drop_percentage}
              onChange={(e) => setSlack({ ...slack, min_drop_percentage: parseFloat(e.target.value) || 0 })}
              hint="Only trigger alerts if price drops by at least this percentage"
              min={1}
              max={100}
            />
            <div className="pt-2">
              <ToggleItem
                label="Enable Slack Alerts"
                description="Deliver price drop notifications to Slack channel"
                checked={slack.is_active}
                onChange={() => setSlack({ ...slack, is_active: !slack.is_active })}
              />
            </div>
          </div>

          {slackTestResult && (
            <Alert
              variant={slackTestResult.success ? 'success' : 'danger'}
              title={slackTestResult.message}
            />
          )}

          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              disabled={testingSlack || !slack.webhook_url}
              onClick={handleTestSlack}
            >
              {testingSlack ? 'Sending Test...' : 'Send Test Slack Alert'}
            </Button>
            <Button
              variant="primary"
              disabled={!slack.webhook_url}
              onClick={handleSaveSlack}
            >
              Save Slack Config
            </Button>
          </div>
        </div>
      </Card>

      {/* 3. Discord / Custom Webhook Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <span className="text-lg">🎮</span>
              Discord & Custom Webhook Alerts
            </CardTitle>
            <Badge variant="warning">Rich Embed / Webhook</Badge>
          </div>
        </CardHeader>
        <div className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Posts rich Discord embeds with color-coded price drop badges or pushes raw events to Zapier, Make, and custom servers.
          </p>

          <Input
            label="Discord Webhook URL"
            type="password"
            placeholder="https://discord.com/api/webhooks/123456789/abcdefgh..."
            value={discord.webhook_url}
            onChange={(e) => setDiscord({ ...discord, webhook_url: e.target.value })}
            hint="From Discord Channel Settings → Integrations → Webhooks"
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center pt-2">
            <Input
              label="Minimum Price Drop Trigger (%)"
              type="number"
              value={discord.min_drop_percentage}
              onChange={(e) => setDiscord({ ...discord, min_drop_percentage: parseFloat(e.target.value) || 0 })}
              hint="Only trigger alerts if price drops by at least this percentage"
              min={1}
              max={100}
            />
            <div className="pt-2">
              <ToggleItem
                label="Enable Discord Alerts"
                description="Deliver price drop notifications to Discord channel"
                checked={discord.is_active}
                onChange={() => setDiscord({ ...discord, is_active: !discord.is_active })}
              />
            </div>
          </div>

          {discordTestResult && (
            <Alert
              variant={discordTestResult.success ? 'success' : 'danger'}
              title={discordTestResult.message}
            />
          )}

          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              disabled={testingDiscord || !discord.webhook_url}
              onClick={handleTestDiscord}
            >
              {testingDiscord ? 'Sending Test...' : 'Send Test Discord Alert'}
            </Button>
            <Button
              variant="primary"
              disabled={!discord.webhook_url}
              onClick={handleSaveDiscord}
            >
              Save Discord Config
            </Button>
          </div>
        </div>
      </Card>

      {/* 4. Real-Time Triggered Alert History Log */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Recent Triggered Alerts ({alertLogs.length})</CardTitle>
            <Button size="sm" variant="outline" onClick={loadAlertLogs}>
              Refresh Logs
            </Button>
          </div>
        </CardHeader>
        <div className="space-y-3">
          {alertLogs.length === 0 ? (
            <p className="text-xs text-gray-500 dark:text-gray-400 py-3 text-center">
              No price drop alerts triggered yet. As scheduled crawls detect price drops, audit logs will appear here.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b dark:border-gray-700 text-gray-500">
                    <th className="py-2">Product</th>
                    <th className="py-2">Price Drop</th>
                    <th className="py-2">Discount</th>
                    <th className="py-2">Channel</th>
                    <th className="py-2">Status</th>
                    <th className="py-2">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y dark:divide-gray-800">
                  {alertLogs.map((log) => (
                    <tr key={log.id}>
                      <td className="py-2.5 font-medium text-gray-900 dark:text-white truncate max-w-xs">
                        {log.product_name}
                      </td>
                      <td className="py-2.5 font-mono">
                        <span className="line-through text-gray-400 mr-1.5">{log.currency} {log.old_price}</span>
                        <span className="text-emerald-600 font-bold">{log.currency} {log.new_price}</span>
                      </td>
                      <td className="py-2.5">
                        <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 font-semibold">
                          -{log.price_change_percentage}%
                        </span>
                      </td>
                      <td className="py-2.5 uppercase font-semibold text-gray-500">
                        {log.channel}
                      </td>
                      <td className="py-2.5">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${log.status === 'sent' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400' : 'bg-rose-100 text-rose-700'}`}>
                          {log.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2.5 text-gray-400">
                        {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

function ScrapingSettings() {
  const [settings, setSettings] = useState({
    default_max_pages: 100,
    default_max_products: 10000,
    default_delay: 1000,
    use_proxy: true,
    headless: true,
  })

  // Proxy Pool State
  const [proxyListText, setProxyListText] = useState('')
  const [failoverEnabled, setFailoverEnabled] = useState(true)
  const [poolStatus, setPoolStatus] = useState(null)
  const [loadingPool, setLoadingPool] = useState(false)
  const [testingPool, setTestingPool] = useState(false)
  const [testResults, setTestResults] = useState(null)

  useEffect(() => {
    loadProxyStatus()
  }, [])

  const loadProxyStatus = async () => {
    try {
      setLoadingPool(true)
      const res = await scraperService.getProxyStatus()
      setPoolStatus(res)
      if (res && res.failover_enabled !== undefined) {
        setFailoverEnabled(res.failover_enabled)
      }
    } catch (e) {
      console.error('Failed to load proxy status', e)
    } finally {
      setLoadingPool(false)
    }
  }

  const handleTestProxies = async () => {
    setTestingPool(true)
    setTestResults(null)
    try {
      const explicit = proxyListText.trim()
        ? proxyListText.split('\n').map((s) => s.trim()).filter(Boolean)
        : null
      const res = await scraperService.testProxyPool(explicit)
      setTestResults(res)
      if (res.success) {
        toast.success(`Proxy test passed! ${res.active}/${res.total} proxies operational.`)
      } else {
        toast.error(res.message || 'Proxy test failed: no proxies reachable.')
      }
      loadProxyStatus()
    } catch (e) {
      toast.error('Proxy test failed: ' + (e.response?.data?.detail || e.message))
    } finally {
      setTestingPool(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* 1. General Scraping Defaults */}
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
              label="Headless Mode"
              description="Run browser in headless mode (faster and lighter)"
              checked={settings.headless}
              onChange={() => setSettings((s) => ({ ...s, headless: !s.headless }))}
            />
          </div>

          <div className="pt-2">
            <Button onClick={() => toast.success('Default settings saved!')}>Save Defaults</Button>
          </div>
        </div>
      </Card>

      {/* 2. Rotating Proxy Pool & Automated Anti-Bot Failover */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <ShieldCheckIcon className="w-5 h-5 text-indigo-500" />
              Rotating Proxy Pool & Anti-Bot Failover
            </CardTitle>
            <Badge variant="primary" className="bg-indigo-100 text-indigo-800 dark:bg-indigo-900/60 dark:text-indigo-300">
              Auto-Failover on 403 / 429
            </Badge>
          </div>
        </CardHeader>

        <div className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Distribute scraping requests across rotating IP addresses and automatically switch proxies the moment a target website issues an HTTP 403 Forbidden, 429 Rate Limit, or 503 Bot Challenge.
          </p>

          {/* Health Stats Bar */}
          {poolStatus && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-gray-50 dark:bg-gray-800/60 p-3 rounded-lg border border-gray-200 dark:border-gray-700 text-xs">
              <div>
                <span className="text-gray-500 dark:text-gray-400">Total Proxies</span>
                <p className="text-base font-bold text-gray-900 dark:text-white">{poolStatus.total}</p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">Active / Healthy</span>
                <p className="text-base font-bold text-emerald-600 dark:text-emerald-400">{poolStatus.healthy}</p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">Cooling Down</span>
                <p className="text-base font-bold text-amber-500">{poolStatus.cooling}</p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">Failover Mode</span>
                <p className="text-base font-bold text-indigo-600 dark:text-indigo-400">
                  {failoverEnabled ? 'Enabled (Auto-Switch)' : 'Disabled'}
                </p>
              </div>
            </div>
          )}

          {/* Failover Toggle */}
          <div className="pt-2">
            <ToggleItem
              label="Automatic Failover on 403 / 429 / 503"
              description="Instantly switch to the next proxy in the pool and retry the request when blocked by Cloudflare, Akamai, or rate-limits."
              checked={failoverEnabled}
              onChange={() => {
                setFailoverEnabled(!failoverEnabled)
                toast.success(`Proxy auto-failover ${!failoverEnabled ? 'enabled' : 'disabled'}`)
              }}
            />
          </div>

          {/* Proxy Pool Textarea */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Custom Proxy Pool List (one per line)
            </label>
            <textarea
              rows={4}
              value={proxyListText}
              onChange={(e) => setProxyListText(e.target.value)}
              placeholder="http://user:password@proxy-host-1.com:8080&#10;http://user:password@proxy-host-2.com:8080"
              className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-primary-500 focus:border-primary-500"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Supports HTTP, HTTPS, and SOCKS5 proxies with or without authentication. Leave empty to use system .env SCRAPER_PROXY defaults.
            </p>
          </div>

          {/* Test Results Display */}
          {testResults && (
            <div className="space-y-2 mt-3">
              <p className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                Test Results ({testResults.active}/{testResults.total} operational):
              </p>
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {testResults.results.map((r, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-2 rounded bg-gray-100 dark:bg-gray-800 text-xs"
                  >
                    <span className="font-mono truncate max-w-xs">{r.proxy}</span>
                    <div className="flex items-center gap-2">
                      {r.latency_ms && <span className="text-gray-500">{r.latency_ms}ms</span>}
                      {r.success ? (
                        <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                          ✓ {r.origin_ip || 'Online'}
                        </span>
                      ) : (
                        <span className="text-rose-500 font-medium">✕ {r.error || 'Failed'}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              disabled={testingPool}
              onClick={handleTestProxies}
            >
              {testingPool ? 'Testing All Proxies...' : 'Test Proxy Pool'}
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                toast.success('Proxy pool configuration saved!')
                loadProxyStatus()
              }}
            >
              Save Proxy Pool
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}

function CloudinarySettings() {
  const [cloudName, setCloudName] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [folder, setFolder] = useState('ecommerce_scraper')
  const [autoUpload, setAutoUpload] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)

  // Quick single-image upload test state
  const [sampleUrl, setSampleUrl] = useState('')
  const [uploadResult, setUploadResult] = useState(null)
  const [uploading, setUploading] = useState(false)

  const handleTestConnection = async () => {
    try {
      setTesting(true)
      setTestResult(null)
      const res = await cloudinaryService.testConnection({
        cloud_name: cloudName,
        api_key: apiKey,
        api_secret: apiSecret,
      })
      setTestResult(res)
      if (res.success) {
        toast.success(res.message || 'Connected to Cloudinary!')
      } else {
        toast.error(res.message || 'Failed to connect to Cloudinary.')
      }
    } catch (e) {
      toast.error(e.message || 'Error testing Cloudinary credentials')
    } finally {
      setTesting(false)
    }
  }

  const handleTestImageUpload = async () => {
    if (!sampleUrl.trim()) {
      toast.error('Please enter an image URL to test upload')
      return
    }
    try {
      setUploading(true)
      setUploadResult(null)
      const res = await cloudinaryService.uploadImage(sampleUrl, folder)
      setUploadResult(res)
      toast.success('Image successfully uploaded and transformed on Cloudinary CDN!')
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <PhotoIcon className="w-5 h-5 text-sky-500" />
              Cloudinary Media CDN & Image Optimization
            </CardTitle>
            <Badge variant="info">Global CDN • WebP • Auto-Crop</Badge>
          </div>
        </CardHeader>
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Host scraped competitor images on Cloudinary to prevent hotlink-blocking (403 errors), 
            automatically convert large product images to lightweight modern WebP formats, and generate 
            instant responsive thumbnails for your catalog exports.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Cloud Name"
              placeholder="e.g. my-ecommerce-cloud"
              value={cloudName}
              onChange={(e) => setCloudName(e.target.value)}
              hint="Found on your Cloudinary Dashboard"
            />
            <Input
              label="Folder Name"
              placeholder="ecommerce_scraper"
              value={folder}
              onChange={(e) => setFolder(e.target.value)}
              hint="Target directory in your Cloudinary Media Library"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="API Key"
              placeholder="e.g. 123456789012345"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
            <Input
              label="API Secret"
              type="password"
              placeholder="••••••••••••••••••••••••••••"
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
            />
          </div>

          {/* Connection Test Diagnostics */}
          {testResult && (
            <div className={`p-4 rounded-xl text-xs space-y-1.5 border ${
              testResult.success
                ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
                : 'bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300'
            }`}>
              <div className="font-semibold flex items-center gap-1.5">
                {testResult.success ? '✓' : '✕'} {testResult.message}
              </div>
              {testResult.plan && (
                <div className="text-gray-600 dark:text-gray-400">
                  Plan: <span className="font-semibold">{testResult.plan}</span> • Storage: {testResult.storage?.usage ? `${(testResult.storage.usage / (1024*1024)).toFixed(1)} MB` : 'Active'} • Objects: {testResult.objects?.usage || 0}
                </div>
              )}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              disabled={testing || (!cloudName && !apiKey)}
              onClick={handleTestConnection}
            >
              {testing ? 'Testing Connection...' : 'Test Cloudinary Connection'}
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                toast.success('Cloudinary CDN preferences saved!')
              }}
            >
              Save Configuration
            </Button>
          </div>
        </div>
      </Card>

      {/* Live CDN Upload & Transformation Tester */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <SparklesIcon className="w-4 h-4 text-primary-600" />
            Live CDN Upload & Transformation Sandbox
          </CardTitle>
        </CardHeader>
        <div className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Paste any remote competitor product image URL to test uploading and instant WebP/thumbnail CDN generation.
          </p>

          <div className="flex flex-col sm:flex-row gap-3">
            <Input
              placeholder="https://images.unsplash.com/photo-1542291026-7eec264c27ff"
              value={sampleUrl}
              onChange={(e) => setSampleUrl(e.target.value)}
              className="flex-1"
            />
            <Button
              variant="secondary"
              onClick={handleTestImageUpload}
              disabled={uploading || !sampleUrl.trim()}
            >
              {uploading ? 'Uploading to CDN...' : 'Upload & Optimize'}
            </Button>
          </div>

          {uploadResult && uploadResult.success && (
            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40 flex flex-col md:flex-row gap-4 items-center">
              <img
                src={uploadResult.thumbnail_url || uploadResult.secure_url}
                alt="Cloudinary preview"
                className="w-24 h-24 object-cover rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm"
              />
              <div className="space-y-1 text-xs flex-1">
                <div className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <CheckCircleIcon className="w-4 h-4 text-emerald-500" />
                  Successfully Uploaded to Cloudinary
                </div>
                <div className="text-gray-600 dark:text-gray-300 font-mono break-all">
                  CDN URL: <a href={uploadResult.secure_url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">{uploadResult.secure_url}</a>
                </div>
                <div className="text-gray-500">
                  Format: {uploadResult.format?.toUpperCase()} • {uploadResult.width}×{uploadResult.height}px • {(uploadResult.bytes / 1024).toFixed(1)} KB
                </div>
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

function S3StorageSettings() {
  const [accessKeyId, setAccessKeyId] = useState('')
  const [secretAccessKey, setSecretAccessKey] = useState('')
  const [bucketName, setBucketName] = useState('')
  const [region, setRegion] = useState('us-east-1')
  const [endpointUrl, setEndpointUrl] = useState('')
  const [prefix, setPrefix] = useState('products')
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)

  // Image upload sandbox state
  const [sampleUrl, setSampleUrl] = useState('')
  const [uploadResult, setUploadResult] = useState(null)
  const [uploading, setUploading] = useState(false)

  const handleTestConnection = async () => {
    try {
      setTesting(true)
      setTestResult(null)
      const res = await s3Service.testConnection({
        access_key_id: accessKeyId,
        secret_access_key: secretAccessKey,
        bucket_name: bucketName,
        region,
        endpoint_url: endpointUrl || null,
      })
      setTestResult(res)
      if (res.success) {
        toast.success(res.message || 'Connected to AWS S3 bucket!')
      } else {
        toast.error(res.message || 'Failed to connect to S3.')
      }
    } catch (e) {
      toast.error(e.message || 'Error testing S3 credentials')
    } finally {
      setTesting(false)
    }
  }

  const handleTestUpload = async () => {
    if (!sampleUrl.trim()) {
      toast.error('Please enter an image URL to test S3 archiving')
      return
    }
    try {
      setUploading(true)
      setUploadResult(null)
      const res = await s3Service.uploadImage(sampleUrl, bucketName || null, prefix || null)
      setUploadResult(res)
      toast.success('Image successfully downloaded and stored in S3 bucket!')
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message || 'S3 upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <ServerStackIcon className="w-5 h-5 text-amber-500" />
              AWS S3 & Cloud Storage Archiving
            </CardTitle>
            <Badge variant="warning">AWS S3 • Cloudflare R2 • MinIO • Wasabi</Badge>
          </div>
        </CardHeader>
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Automatically download remote product images during scraper jobs and stream them directly into 
            your private or public AWS S3 bucket, Cloudflare R2 bucket, or self-hosted MinIO cluster.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="S3 Bucket Name"
              placeholder="e.g. my-scraped-products"
              value={bucketName}
              onChange={(e) => setBucketName(e.target.value)}
              hint="Required: The target bucket name"
            />
            <Input
              label="AWS Region"
              placeholder="us-east-1"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              hint="Default: us-east-1 (or auto for Cloudflare R2)"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Access Key ID"
              placeholder="AKIAIOSFODNN7EXAMPLE"
              value={accessKeyId}
              onChange={(e) => setAccessKeyId(e.target.value)}
            />
            <Input
              label="Secret Access Key"
              type="password"
              placeholder="••••••••••••••••••••••••••••"
              value={secretAccessKey}
              onChange={(e) => setSecretAccessKey(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Custom S3 Endpoint URL (Optional)"
              placeholder="https://<accountid>.r2.cloudflarestorage.com"
              value={endpointUrl}
              onChange={(e) => setEndpointUrl(e.target.value)}
              hint="For Cloudflare R2, MinIO, Wasabi, or Backblaze B2"
            />
            <Input
              label="Storage Path Prefix"
              placeholder="products"
              value={prefix}
              onChange={(e) => setPrefix(e.target.value)}
              hint="Folder inside bucket (default: products/)"
            />
          </div>

          {/* Connection Test Diagnostics */}
          {testResult && (
            <div className={`p-4 rounded-xl text-xs space-y-1.5 border ${
              testResult.success
                ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
                : 'bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300'
            }`}>
              <div className="font-semibold flex items-center gap-1.5">
                {testResult.success ? '✓' : '✕'} {testResult.message}
              </div>
              {testResult.bucket && (
                <div className="text-gray-600 dark:text-gray-400">
                  Target Bucket: <span className="font-semibold">{testResult.bucket}</span> • Region: {testResult.region}
                </div>
              )}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              disabled={testing || (!accessKeyId && !bucketName)}
              onClick={handleTestConnection}
            >
              {testing ? 'Testing S3 Bucket...' : 'Test S3 Bucket Connection'}
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                toast.success('AWS S3 storage configuration saved!')
              }}
            >
              Save Configuration
            </Button>
          </div>
        </div>
      </Card>

      {/* Live S3 Upload Tester */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <SparklesIcon className="w-4 h-4 text-primary-600" />
            Live S3 Image Ingestion Sandbox
          </CardTitle>
        </CardHeader>
        <div className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Paste any competitor product image URL to test download and direct streaming into your configured S3 bucket.
          </p>

          <div className="flex flex-col sm:flex-row gap-3">
            <Input
              placeholder="https://images.unsplash.com/photo-1523275335684-37898b6baf30"
              value={sampleUrl}
              onChange={(e) => setSampleUrl(e.target.value)}
              className="flex-1"
            />
            <Button
              variant="secondary"
              onClick={handleTestUpload}
              disabled={uploading || !sampleUrl.trim()}
            >
              {uploading ? 'Archiving to S3...' : 'Download & Stream to S3'}
            </Button>
          </div>

          {uploadResult && uploadResult.success && (
            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40 space-y-1 text-xs">
              <div className="font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                <CheckCircleIcon className="w-4 h-4" />
                Successfully Streamed to S3 Bucket ({uploadResult.bucket})
              </div>
              <div className="text-gray-600 dark:text-gray-300 font-mono break-all">
                S3 Key: <span className="font-semibold text-gray-800 dark:text-gray-200">{uploadResult.s3_key}</span>
              </div>
              <div className="text-gray-600 dark:text-gray-300 font-mono break-all">
                Public URL: <a href={uploadResult.s3_url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">{uploadResult.s3_url}</a>
              </div>
              <div className="text-gray-500">
                Content-Type: {uploadResult.content_type} • Size: {(uploadResult.size_bytes / 1024).toFixed(1)} KB
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

function SupabaseStorageSettings() {
  const [supabaseUrl, setSupabaseUrl] = useState('')
  const [supabaseKey, setSupabaseKey] = useState('')
  const [bucketName, setBucketName] = useState('product-images')
  const [folder, setFolder] = useState('products')
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)

  // Sandbox upload state
  const [sampleUrl, setSampleUrl] = useState('')
  const [uploadResult, setUploadResult] = useState(null)
  const [uploading, setUploading] = useState(false)

  const handleTestConnection = async () => {
    try {
      setTesting(true)
      setTestResult(null)
      const res = await supabaseService.testConnection({
        supabase_url: supabaseUrl,
        supabase_key: supabaseKey,
        bucket_name: bucketName,
      })
      setTestResult(res)
      if (res.success) {
        toast.success(res.message || 'Connected to Supabase Storage!')
      } else {
        toast.error(res.message || 'Failed to connect to Supabase.')
      }
    } catch (e) {
      toast.error(e.message || 'Error testing Supabase credentials')
    } finally {
      setTesting(false)
    }
  }

  const handleTestUpload = async () => {
    if (!sampleUrl.trim()) {
      toast.error('Please enter an image URL to test upload')
      return
    }
    try {
      setUploading(true)
      setUploadResult(null)
      const res = await supabaseService.uploadImage(
        sampleUrl,
        bucketName || null,
        folder || null,
        supabaseUrl || null,
        supabaseKey || null
      )
      setUploadResult(res)
      toast.success('Image successfully downloaded and streamed into Supabase Storage!')
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <CircleStackIcon className="w-5 h-5 text-emerald-500" />
              Supabase Free Cloud Storage
            </CardTitle>
            <Badge variant="success">100% Free Tier • No AWS Bill • Fast Global CDN</Badge>
          </div>
        </CardHeader>
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Host scraped competitor images completely free on <strong>Supabase Storage</strong> without needing an AWS account or paid credit card. 
            All images are automatically served over Supabase's global CDN with zero bandwidth egress charges on the generous free plan.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Supabase Project URL"
              placeholder="https://xyzcompany.supabase.co"
              value={supabaseUrl}
              onChange={(e) => setSupabaseUrl(e.target.value)}
              hint="Found under Project Settings → API in your Supabase Dashboard"
            />
            <Input
              label="Supabase API Key (anon / service_role)"
              type="password"
              placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
              value={supabaseKey}
              onChange={(e) => setSupabaseKey(e.target.value)}
              hint="Public anon key or service_role secret key"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Storage Bucket Name"
              placeholder="product-images"
              value={bucketName}
              onChange={(e) => setBucketName(e.target.value)}
              hint="Make sure the bucket is marked as 'Public' in Supabase Storage"
            />
            <Input
              label="Directory Folder Prefix"
              placeholder="products"
              value={folder}
              onChange={(e) => setFolder(e.target.value)}
              hint="Subfolder path inside the bucket (default: products/)"
            />
          </div>

          {/* Connection Test Diagnostics */}
          {testResult && (
            <div className={`p-4 rounded-xl text-xs space-y-1.5 border ${
              testResult.success
                ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
                : 'bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300'
            }`}>
              <div className="font-semibold flex items-center gap-1.5">
                {testResult.success ? '✓' : '✕'} {testResult.message}
              </div>
              {testResult.bucket && (
                <div className="text-gray-600 dark:text-gray-400">
                  Target Bucket: <span className="font-semibold">{testResult.bucket}</span> • Public Access: {testResult.is_public ? 'Enabled ✓' : 'Disabled (Images won\'t be publicly visible)'}
                </div>
              )}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              disabled={testing || (!supabaseUrl && !supabaseKey)}
              onClick={handleTestConnection}
            >
              {testing ? 'Testing Bucket...' : 'Test Supabase Bucket'}
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                toast.success('Supabase Storage configuration saved!')
              }}
            >
              Save Configuration
            </Button>
          </div>
        </div>
      </Card>

      {/* Live Supabase Upload Sandbox */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <SparklesIcon className="w-4 h-4 text-primary-600" />
            Live Supabase Image Ingestion Sandbox
          </CardTitle>
        </CardHeader>
        <div className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Paste any competitor product image URL to test download and direct streaming into your free Supabase Storage bucket.
          </p>

          <div className="flex flex-col sm:flex-row gap-3">
            <Input
              placeholder="https://images.unsplash.com/photo-1505740420928-5e560c06d30e"
              value={sampleUrl}
              onChange={(e) => setSampleUrl(e.target.value)}
              className="flex-1"
            />
            <Button
              variant="secondary"
              onClick={handleTestUpload}
              disabled={uploading || !sampleUrl.trim()}
            >
              {uploading ? 'Archiving to Supabase...' : 'Download & Stream to Supabase'}
            </Button>
          </div>

          {uploadResult && uploadResult.success && (
            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40 flex flex-col md:flex-row gap-4 items-center">
              <img
                src={uploadResult.supabase_url}
                alt="Supabase preview"
                className="w-24 h-24 object-cover rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm"
              />
              <div className="space-y-1 text-xs flex-1">
                <div className="font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                  <CheckCircleIcon className="w-4 h-4" />
                  Successfully Streamed to Supabase Bucket ({uploadResult.bucket})
                </div>
                <div className="text-gray-600 dark:text-gray-300 font-mono break-all">
                  Object Path: <span className="font-semibold text-gray-800 dark:text-gray-200">{uploadResult.supabase_path}</span>
                </div>
                <div className="text-gray-600 dark:text-gray-300 font-mono break-all">
                  Public CDN URL: <a href={uploadResult.supabase_url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">{uploadResult.supabase_url}</a>
                </div>
                <div className="text-gray-500">
                  Content-Type: {uploadResult.content_type} • Size: {(uploadResult.size_bytes / 1024).toFixed(1)} KB
                </div>
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
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

  // Gemini AI state
  const [gemini, setGemini] = useState({ api_key: '' })
  const [testingGemini, setTestingGemini] = useState(false)
  const [geminiTestResult, setGeminiTestResult] = useState(null)

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

      const geminiCfg = (data || []).find((c) => c.platform === 'gemini' || c.platform === 'google_gemini')
      if (geminiCfg?.masked_credentials) {
        setGemini({
          api_key: geminiCfg.masked_credentials.api_key || '',
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

  // Gemini Handlers
  const handleTestGemini = async () => {
    setTestingGemini(true)
    setGeminiTestResult(null)
    try {
      const res = await integrationService.testConnection('gemini', gemini)
      setGeminiTestResult(res)
      if (res.success) toast.success('Google Gemini connection verified!')
      else toast.error(res.message)
    } catch (err) {
      const msg = err.response?.data?.detail || err.message
      setGeminiTestResult({ success: false, message: msg })
      toast.error(msg)
    } finally {
      setTestingGemini(false)
    }
  }

  const handleSaveGemini = async () => {
    try {
      await integrationService.saveConfig({
        platform: 'gemini',
        name: 'Google Gemini AI Engine',
        credentials: gemini,
        is_active: true,
      })
      toast.success('Google Gemini API configuration saved!')
      loadConfigs()
    } catch (err) {
      toast.error('Failed to save Gemini settings: ' + err.message)
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

      {/* 4. Google Gemini AI Engine Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <SparklesIcon className="w-5 h-5 text-purple-500" />
              Google Gemini AI Engine
            </CardTitle>
            <Badge variant="primary" className="bg-purple-100 text-purple-800 dark:bg-purple-900/60 dark:text-purple-300">
              Zero-Shot LLM Extraction
            </Badge>
          </div>
        </CardHeader>
        <div className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Powers zero-shot e-commerce product extraction and AI reverse-engineering of CSS selectors for complex, custom, or obfuscated storefronts.
          </p>
          <Input
            label="Google Gemini API Key"
            type="password"
            placeholder="AIzaSy..."
            value={gemini.api_key}
            onChange={(e) => setGemini({ api_key: e.target.value })}
            hint="Get an API key for free from Google AI Studio (aistudio.google.com)"
          />

          {geminiTestResult && (
            <Alert
              variant={geminiTestResult.success ? 'success' : 'danger'}
              title={geminiTestResult.message}
            />
          )}

          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              disabled={testingGemini || !gemini.api_key}
              onClick={handleTestGemini}
            >
              {testingGemini ? 'Testing Gemini API...' : 'Test Gemini Connection'}
            </Button>
            <Button
              variant="primary"
              disabled={!gemini.api_key}
              onClick={handleSaveGemini}
            >
              Save Gemini Config
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}