import React, { useState } from 'react'
import { Outlet, NavLink, useNavigate, Link } from 'react-router-dom'
import {
  ShieldCheckIcon,
  HomeIcon,
  UserGroupIcon,
  BriefcaseIcon,
  ServerStackIcon,
  ArrowRightOnRectangleIcon,
  ArrowTopRightOnSquareIcon,
  Bars3Icon,
  XMarkIcon,
  CubeIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/utils/helpers'

const adminNav = [
  { name: 'Admin Dashboard', href: '/admin/dashboard', icon: HomeIcon },
  { name: 'Users & Permissions', href: '/admin/users', icon: UserGroupIcon },
  { name: 'All Platform Jobs', href: '/admin/jobs', icon: BriefcaseIcon },
  { name: 'System Telemetry', href: '/admin/system', icon: ServerStackIcon },
]

export default function AdminLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/admin/login')
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col md:flex-row">
      {/* Mobile Top Header */}
      <div className="md:hidden flex items-center justify-between p-4 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-rose-600 flex items-center justify-center text-white shadow-sm">
            <ShieldCheckIcon className="w-5 h-5" />
          </div>
          <span className="font-bold text-sm tracking-wide text-white">Root Admin</span>
        </div>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
        >
          {mobileMenuOpen ? <XMarkIcon className="w-6 h-6" /> : <Bars3Icon className="w-6 h-6" />}
        </button>
      </div>

      {/* Admin Sidebar */}
      <aside
        className={cn(
          'w-full md:w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between shrink-0 transition-all z-30',
          mobileMenuOpen ? 'block' : 'hidden md:flex'
        )}
      >
        <div>
          {/* Logo Header */}
          <div className="h-16 flex items-center gap-3 px-5 border-b border-slate-800">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-rose-600 to-indigo-600 flex items-center justify-center text-white shadow-md">
              <ShieldCheckIcon className="w-5 h-5" />
            </div>
            <div>
              <span className="font-extrabold text-sm tracking-wider uppercase text-white block leading-none">
                CommerceIntel
              </span>
              <span className="text-[10px] font-bold text-rose-400 tracking-widest uppercase">
                Root Admin Console
              </span>
            </div>
          </div>

          {/* Admin User Badge */}
          <div className="p-4 mx-3 my-3 rounded-xl bg-slate-950/80 border border-slate-800/80 flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-rose-500/20 text-rose-400 font-bold text-xs flex items-center justify-center uppercase shrink-0 border border-rose-500/30">
              {user?.username ? user.username[0] : 'A'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold text-white truncate">@{user?.username}</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[10px] font-semibold text-rose-300 uppercase tracking-wider">
                  Superuser
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">
              Admin Operations
            </p>
            {adminNav.map((item) => (
              <NavLink
                key={item.href}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all',
                    isActive
                      ? 'bg-rose-600 text-white shadow-md shadow-rose-950'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  )
                }
              >
                <item.icon className="w-4 h-4 shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Footer Actions */}
        <div className="p-3 border-t border-slate-800 space-y-1.5">
          {/* Switch to Client App */}
          <Link
            to="/"
            className="flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
          >
            <div className="flex items-center gap-2">
              <CubeIcon className="w-4 h-4 text-primary-400" />
              <span>Switch to Client App</span>
            </div>
            <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5" />
          </Link>

          {/* Admin Logout */}
          <button
            type="button"
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 transition-colors"
          >
            <ArrowRightOnRectangleIcon className="w-4 h-4" />
            <span>Admin Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Admin Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <header className="h-16 bg-slate-900/60 backdrop-blur-md border-b border-slate-800/80 px-6 hidden md:flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/20">
              Isolated Admin Zone
            </span>
            <span className="text-xs text-slate-400">• Standard users cannot access this portal</span>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="text-xs text-slate-300 hover:text-white px-3 py-1.5 rounded-lg border border-slate-700 hover:border-slate-600 bg-slate-800/50 flex items-center gap-1.5 transition-colors"
            >
              <span>User App View</span>
              <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5" />
            </Link>
          </div>
        </header>

        <div className="p-6 flex-1 bg-slate-950">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
