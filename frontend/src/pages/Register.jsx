import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { GlobeAltIcon, EyeIcon, EyeSlashIcon, CheckIcon } from '@heroicons/react/24/outline'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/utils/helpers'
import { Button, Input, Alert, Card } from '@/components/Common'
import toast from 'react-hot-toast'

const PASSWORD_REQUIREMENTS = [
  { key: 'length', label: 'At least 8 characters', test: (p) => p.length >= 8 },
  { key: 'uppercase', label: 'One uppercase letter', test: (p) => /[A-Z]/.test(p) },
  { key: 'lowercase', label: 'One lowercase letter', test: (p) => /[a-z]/.test(p) },
  { key: 'number', label: 'One number', test: (p) => /\d/.test(p) },
]

export default function Register() {
  const navigate = useNavigate()
  const { register: registerUser } = useAuth()
  
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const { register, handleSubmit, watch, formState: { errors } } = useForm({
    defaultValues: {
      email: '',
      username: '',
      full_name: '',
      password: '',
      confirm_password: '',
    },
  })

  const password = watch('password', '')

  const onSubmit = async (data) => {
    if (data.password !== data.confirm_password) {
      setError('Passwords do not match')
      return
    }

    setIsLoading(true)
    setError('')
    
    try {
      await registerUser(data.email, data.username, data.password, data.full_name)
      toast.success('Account created successfully!')
      navigate('/')
    } catch (err) {
      setError(err.message || 'Failed to create account')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary-600 mb-4">
            <GlobeAltIcon className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Create Account
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Start scraping e-commerce data today
          </p>
        </div>

        <Card className="p-8">
          {error && (
            <Alert variant="danger" className="mb-4">
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Full Name"
              {...register('full_name')}
              error={errors.full_name?.message}
              autoComplete="name"
            />
            
            <Input
              label="Email"
              type="email"
              {...register('email', {
                required: 'Email is required',
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: 'Invalid email address',
                },
              })}
              error={errors.email?.message}
              autoComplete="email"
            />
            
            <Input
              label="Username"
              {...register('username', {
                required: 'Username is required',
                minLength: {
                  value: 3,
                  message: 'Username must be at least 3 characters',
                },
                pattern: {
                  value: /^[a-zA-Z0-9_]+$/,
                  message: 'Username can only contain letters, numbers, and underscores',
                },
              })}
              error={errors.username?.message}
              autoComplete="username"
            />
            
            <div className="relative">
              <Input
                label="Password"
                type={showPassword ? 'text' : 'password'}
                {...register('password', {
                  required: 'Password is required',
                  minLength: {
                    value: 8,
                    message: 'Password must be at least 8 characters',
                  },
                })}
                error={errors.password?.message}
                autoComplete="new-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-9 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                {showPassword ? (
                  <EyeSlashIcon className="w-5 h-5" />
                ) : (
                  <EyeIcon className="w-5 h-5" />
                )}
              </button>
            </div>

            {/* Password requirements */}
            {password && (
              <div className="space-y-1">
                {PASSWORD_REQUIREMENTS.map((req) => {
                  const met = req.test(password)
                  return (
                    <div
                      key={req.key}
                      className={cn(
                        'flex items-center gap-2 text-xs',
                        met ? 'text-success-600 dark:text-success-400' : 'text-gray-400'
                      )}
                    >
                      <CheckIcon className={cn('w-3 h-3', !met && 'opacity-0')} />
                      {req.label}
                    </div>
                  )
                })}
              </div>
            )}
            
            <Input
              label="Confirm Password"
              type="password"
              {...register('confirm_password', {
                required: 'Please confirm your password',
              })}
              error={errors.confirm_password?.message}
              autoComplete="new-password"
            />

            <div className="pt-2">
              <Button
                type="submit"
                fullWidth
                size="lg"
                loading={isLoading}
              >
                Create Account
              </Button>
            </div>
          </form>

          <p className="mt-4 text-xs text-center text-gray-500 dark:text-gray-400">
            By creating an account, you agree to our{' '}
            <Link to="/terms" className="text-primary-600 hover:underline">
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link to="/privacy" className="text-primary-600 hover:underline">
              Privacy Policy
            </Link>
          </p>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Already have an account?{' '}
              <Link
                to="/login"
                className="font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400"
              >
                Sign in
              </Link>
            </p>
          </div>
        </Card>
      </div>
    </div>
  )
}