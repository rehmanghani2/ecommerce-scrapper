import React, { Suspense, lazy } from 'react'
import { Routes, Route, Navigate, Link } from 'react-router-dom'

import Layout from './components/Layout/Layout'
import AdminLayout from './components/Admin/AdminLayout'
import { useAuth } from './hooks/useAuth'
import Spinner from './components/Common/Spinner'
import { ShieldExclamationIcon } from '@heroicons/react/24/outline'

// Lazy load Client pages
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Scraper = lazy(() => import('./pages/Scraper'))
const Jobs = lazy(() => import('./pages/Jobs'))
const JobDetail = lazy(() => import('./pages/JobDetail'))
const Products = lazy(() => import('./pages/Products'))
const Schedules = lazy(() => import('./pages/Schedules'))
const Exports = lazy(() => import('./pages/Exports'))
const Proxies = lazy(() => import('./pages/Proxies'))
const Reports = lazy(() => import('./pages/Reports'))
const SerpTracking = lazy(() => import('./pages/SerpTracking'))
const Settings = lazy(() => import('./pages/Settings'))
const Notifications = lazy(() => import('./pages/Notifications'))
const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const NotFound = lazy(() => import('./pages/NotFound'))

// Lazy load Admin pages
const AdminLogin = lazy(() => import('./pages/Admin/AdminLogin'))
const AdminDashboard = lazy(() => import('./pages/Admin/AdminDashboard'))
const AdminUsers = lazy(() => import('./pages/Admin/AdminUsers'))
const AdminJobs = lazy(() => import('./pages/Admin/AdminJobs'))
const AdminSystem = lazy(() => import('./pages/Admin/AdminSystem'))

// Loading component
const PageLoader = () => (
  <div className="flex items-center justify-center min-h-screen bg-slate-950/20">
    <Spinner size="lg" />
  </div>
)

// Protected route wrapper for standard users
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <PageLoader />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return children
}

// Protected route wrapper strictly for superusers/admins
const AdminProtectedRoute = ({ children }) => {
  const { user, isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <PageLoader />
  }

  // Not logged in -> send to dedicated Admin Login
  if (!isAuthenticated) {
    return <Navigate to="/admin/login" replace />
  }

  // Logged in, but NOT a superuser -> Strict 403 Forbidden Access Denied screen
  if (!user?.is_superuser) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center text-white">
        <div className="w-16 h-16 rounded-2xl bg-rose-600/20 border border-rose-600/30 flex items-center justify-center text-rose-500 mb-4 shadow-xl">
          <ShieldExclamationIcon className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-extrabold text-white">Access Denied: Administrator Only</h1>
        <p className="text-sm text-slate-400 mt-2 max-w-md">
          You are authenticated as <strong className="text-white">@{user?.username}</strong>, but this account does not possess root administrator privileges to access the Admin Portal.
        </p>
        <div className="mt-6 flex items-center gap-3">
          <Link
            to="/"
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
          >
            Return to Client App
          </Link>
          <Link
            to="/admin/login"
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-md transition-colors"
          >
            Login with Admin Account
          </Link>
        </div>
      </div>
    )
  }

  return children
}

// Public route wrapper (redirect if authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <PageLoader />
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return children
}

function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* ==================== CLIENT AUTH ROUTES ==================== */}
        <Route
          path="/login"
          element={
            <PublicRoute>
              <Login />
            </PublicRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicRoute>
              <Register />
            </PublicRoute>
          }
        />

        {/* ==================== DEDICATED ADMIN AUTH ==================== */}
        <Route path="/admin/login" element={<AdminLogin />} />

        {/* ==================== ISOLATED ADMIN PORTAL ==================== */}
        <Route
          path="/admin"
          element={
            <AdminProtectedRoute>
              <AdminLayout />
            </AdminProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="dashboard" element={<AdminDashboard />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="jobs" element={<AdminJobs />} />
          <Route path="system" element={<AdminSystem />} />
        </Route>

        {/* ==================== CLIENT APPLICATION ==================== */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="scraper" element={<Scraper />} />
          <Route path="jobs" element={<Jobs />} />
          <Route path="jobs/:jobId" element={<JobDetail />} />
          <Route path="products" element={<Products />} />
          <Route path="schedules" element={<Schedules />} />
          <Route path="exports" element={<Exports />} />
          <Route path="proxies" element={<Proxies />} />
          <Route path="reports" element={<Reports />} />
          <Route path="serp" element={<SerpTracking />} />
          <Route path="notifications" element={<Notifications />} />
          <Route path="settings" element={<Settings />} />
        </Route>

        {/* 404 */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  )
}

export default App