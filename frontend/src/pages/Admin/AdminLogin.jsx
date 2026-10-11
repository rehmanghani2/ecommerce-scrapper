import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  ShieldCheckIcon,
  KeyIcon,
  UserIcon,
  LockClosedIcon,
  ExclamationCircleIcon,
  ArrowLeftIcon,
} from '@heroicons/react/24/outline'
import { Button, Input } from '@/components/Common'
import { useAuth } from '@/hooks/useAuth'
import { apiPost } from '@/services/api'
import { STORAGE_KEYS } from '@/utils/constants'
import toast from 'react-hot-toast'

export default function AdminLogin() {
  const navigate = useNavigate()
  const { refreshUser } = useAuth()
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (e) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }))
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      // Call dedicated admin login endpoint
      const data = await apiPost('/admin/login', {
        username: formData.username,
        password: formData.password,
      })

      if (data?.access_token) {
        localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, data.access_token)
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(data.user))
        await refreshUser()
        toast.success(`Welcome, Administrator @${data.user.username}!`)
        navigate('/admin/dashboard')
      }
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Authentication failed. Please verify your root administrator credentials.'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-slate-900 to-indigo-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-white">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Shield Icon Header */}
        <div className="flex justify-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-rose-600 via-red-600 to-indigo-600 p-0.5 shadow-2xl ring-4 ring-rose-500/20">
            <div className="w-full h-full bg-gray-950 rounded-[14px] flex items-center justify-center">
              <ShieldCheckIcon className="w-8 h-8 text-rose-500" />
            </div>
          </div>
        </div>

        <h2 className="mt-5 text-center text-2xl font-extrabold tracking-tight text-white">
          Admin Portal Authentication
        </h2>
        <p className="mt-1.5 text-center text-xs text-gray-400">
          Restricted zone. Superuser credentials required.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-gray-900/90 backdrop-blur-xl py-8 px-6 shadow-2xl rounded-2xl border border-gray-800 sm:px-10 space-y-6">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-200 text-xs flex items-start gap-2.5">
              <ExclamationCircleIcon className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1">
                Admin Username or Email
              </label>
              <div className="relative">
                <input
                  type="text"
                  name="username"
                  required
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="admin username"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-gray-800/80 border border-gray-700 text-white placeholder-gray-500 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-1">
                Security Password
              </label>
              <div className="relative">
                <input
                  type="password"
                  name="password"
                  required
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••••••"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-gray-800/80 border border-gray-700 text-white placeholder-gray-500 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500"
                />
              </div>
            </div>

            <div className="pt-2">
              <Button
                type="submit"
                variant="primary"
                className="w-full justify-center bg-rose-600 hover:bg-rose-700 focus:ring-rose-500 py-2.5"
                isLoading={loading}
              >
                Authenticate & Enter Root Console
              </Button>
            </div>
          </form>

          <div className="pt-4 border-t border-gray-800/80 flex items-center justify-between text-xs text-gray-400">
            <Link
              to="/login"
              className="flex items-center gap-1.5 hover:text-white transition-colors"
            >
              <ArrowLeftIcon className="w-3.5 h-3.5" />
              Standard Client Login
            </Link>

            <span className="text-[11px] font-mono text-gray-500">
              Role: SUPERUSER_ONLY
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
