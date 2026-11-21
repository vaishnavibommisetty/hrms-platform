import { Menu, Bell, LogOut, User, ChevronRight, Settings } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useNavigate, useLocation } from 'react-router-dom'
import { useState } from 'react'

interface TopBarProps {
  onMenuClick: () => void
}

const ROUTE_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  employees: 'Employees',
  salary: 'Salary Structures',
  performance: 'Performance',
  compensation: 'Compensation',
  payroll: 'Payroll',
  approvals: 'Approvals',
  qa: 'QA Management',
  reports: 'SQL Reports',
  companies: 'Companies',
}

export default function TopBar({ onMenuClick }: TopBarProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)

  const handleLogout = () => {
    setDropdownOpen(false)
    logout()
    navigate('/login')
  }

  // Breadcrumb from path
  const pathSegments = location.pathname.split('/').filter(Boolean)
  const pageKey = pathSegments[0] ?? 'dashboard'
  const pageLabel = ROUTE_LABELS[pageKey] ?? pageKey

  const roleBadgeStyle: Record<string, string> = {
    platform_admin: 'bg-purple-50 text-purple-700 ring-1 ring-purple-200',
    company_admin: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200',
    hr_manager: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200',
    department_manager: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
    finance_manager: 'bg-orange-50 text-orange-700 ring-1 ring-orange-200',
    employee: 'bg-slate-100 text-slate-600 ring-1 ring-slate-200',
  }
  const roleLabel: Record<string, string> = {
    platform_admin: 'Platform Admin',
    company_admin: 'Company Admin',
    hr_manager: 'HR Manager',
    department_manager: 'Dept. Manager',
    finance_manager: 'Finance',
    employee: 'Employee',
  }

  const initials = user?.full_name
    ?.split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase() ?? '?'

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-4 lg:px-6 flex items-center justify-between flex-shrink-0 z-10 sticky top-0">
      {/* Left — hamburger + breadcrumb */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 rounded-lg hover:bg-slate-100 text-slate-600 transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Breadcrumb */}
        <nav className="hidden sm:flex items-center gap-1.5 text-sm">
          <span className="text-slate-400">HRMS</span>
          <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
          <span className="font-semibold text-slate-800">{pageLabel}</span>
        </nav>
        {/* Mobile: just page name */}
        <span className="sm:hidden font-semibold text-slate-800 text-sm">{pageLabel}</span>
      </div>

      {/* Right — role badge, notifications, avatar */}
      <div className="flex items-center gap-2">
        {/* Role badge */}
        <span
          className={`hidden md:inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full ${
            roleBadgeStyle[user?.role ?? ''] ?? 'bg-slate-100 text-slate-600'
          }`}
        >
          {roleLabel[user?.role ?? ''] ?? user?.role}
        </span>

        {/* Notification bell */}
        <div className="relative">
          <button
            onClick={() => { setNotifOpen((v) => !v); setDropdownOpen(false) }}
            className="relative p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-colors"
          >
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-emerald-500 rounded-full ring-2 ring-white" />
          </button>

          {notifOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setNotifOpen(false)} />
              <div className="absolute right-0 mt-2 w-72 bg-white border border-slate-200 rounded-2xl shadow-xl z-20 overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                  <p className="font-semibold text-sm text-slate-800">Notifications</p>
                  <span className="text-xs text-emerald-600 font-medium cursor-pointer hover:underline">Mark all read</span>
                </div>
                <div className="divide-y divide-slate-50">
                  {[
                    { title: 'New employee added', sub: 'Priya Sharma joined Engineering', time: '2m ago', dot: 'bg-blue-400' },
                    { title: 'Payroll processed', sub: 'November payroll completed', time: '1h ago', dot: 'bg-emerald-400' },
                    { title: 'Approval pending', sub: '3 requests need your action', time: '3h ago', dot: 'bg-amber-400' },
                  ].map((n) => (
                    <div key={n.title} className="flex items-start gap-3 px-4 py-3 hover:bg-slate-50 cursor-pointer transition-colors">
                      <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${n.dot}`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800">{n.title}</p>
                        <p className="text-xs text-slate-500 truncate">{n.sub}</p>
                      </div>
                      <span className="text-xs text-slate-400 flex-shrink-0">{n.time}</span>
                    </div>
                  ))}
                </div>
                <div className="px-4 py-2.5 border-t border-slate-100 text-center">
                  <span className="text-xs text-emerald-600 font-medium cursor-pointer hover:underline">View all notifications</span>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Divider */}
        <div className="w-px h-6 bg-slate-200 mx-1 hidden sm:block" />

        {/* Avatar + dropdown */}
        <div className="relative">
          <button
            onClick={() => { setDropdownOpen((v) => !v); setNotifOpen(false) }}
            className="flex items-center gap-2.5 pl-1 pr-2.5 py-1.5 rounded-xl hover:bg-slate-100 transition-colors"
          >
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-white text-xs font-bold ring-2 ring-emerald-200"
              style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
            >
              {initials}
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-sm font-semibold text-slate-800 leading-tight max-w-[100px] truncate">
                {user?.full_name?.split(' ')[0]}
              </p>
              <p className="text-xs text-slate-400 leading-tight">Online</p>
            </div>
          </button>

          {dropdownOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setDropdownOpen(false)} />
              <div className="absolute right-0 mt-2 w-52 bg-white border border-slate-200 rounded-2xl shadow-xl z-20 overflow-hidden py-1">
                <div className="px-4 py-3 border-b border-slate-100">
                  <p className="text-sm font-semibold text-slate-900 truncate">{user?.full_name}</p>
                  <p className="text-xs text-slate-400 truncate">{user?.email}</p>
                </div>
                <button
                  onClick={() => setDropdownOpen(false)}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  <User className="w-4 h-4 text-slate-400" />
                  My Profile
                </button>
                <button
                  onClick={() => setDropdownOpen(false)}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  <Settings className="w-4 h-4 text-slate-400" />
                  Settings
                </button>
                <div className="border-t border-slate-100 mt-1" />
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
