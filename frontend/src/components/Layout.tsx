import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { FileText, MessageSquare, LogOut, Home, FlaskConical, Brain } from 'lucide-react'
import { clsx } from 'clsx'

export default function Layout() {
  const { user, logout } = useAuthStore()
  const location = useLocation()

  const navItems = [
    { path: '/dashboard',  label: 'Dashboard',  icon: Home },
    { path: '/documents',  label: 'Documents',  icon: FileText },
    { path: '/queries',    label: 'Queries',    icon: MessageSquare },
    { path: '/evaluate',   label: 'Evaluate',   icon: FlaskConical },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            {/* Brand */}
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-indigo-600 rounded-lg">
                  <Brain className="w-4 h-4 text-white" />
                </div>
                <span className="text-lg font-bold text-gray-900">MicroBrain</span>
                <span className="text-[10px] bg-indigo-100 text-indigo-600 px-1.5 py-0.5 rounded font-semibold">
                  Policy RAG
                </span>
              </div>

              {/* Nav links */}
              <div className="hidden sm:flex sm:space-x-1">
                {navItems.map(({ path, label, icon: Icon }) => {
                  const active = location.pathname === path
                  return (
                    <Link
                      key={path}
                      to={path}
                      className={clsx(
                        'inline-flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                        active
                          ? 'bg-indigo-50 text-indigo-700'
                          : 'text-gray-500 hover:bg-gray-100 hover:text-gray-800'
                      )}
                    >
                      <Icon className="w-4 h-4 mr-1.5" />
                      {label}
                    </Link>
                  )
                })}
              </div>
            </div>

            {/* User */}
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500 hidden sm:block">{user?.email}</span>
              <button
                onClick={logout}
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  )
}
