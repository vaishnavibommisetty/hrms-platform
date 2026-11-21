import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import {
  LayoutDashboard,
  Users,
  DollarSign,
  TrendingUp,
  CreditCard,
  GitBranch,
  ClipboardCheck,
  BarChart3,
  BookOpen,
  Building2,
  X,
  Zap,
  ScrollText,
} from 'lucide-react'
import clsx from 'clsx'

interface NavItem {
  label: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string
  comingSoon?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Employees', href: '/employees', icon: Users },
  { label: 'Salary Structures', href: '/salary', icon: DollarSign },
  { label: 'Performance', href: '/performance', icon: TrendingUp },
  { label: 'Compensation', href: '/compensation', icon: BarChart3 },
  { label: 'Payroll', href: '/payroll', icon: CreditCard },
  { label: 'Approvals', href: '/approvals', icon: GitBranch },
  { label: 'QA Management', href: '/qa', icon: ClipboardCheck },
  { label: 'SQL Reports', href: '/reports', icon: BookOpen },
  { label: 'Audit Log', href: '/audit', icon: ScrollText },
]

const ADMIN_ITEMS: NavItem[] = [
  { label: 'Companies', href: '/companies', icon: Building2, comingSoon: true },
]

const SECTION_GROUPS = [
  {
    title: 'Core HR',
    items: NAV_ITEMS.slice(0, 2),
  },
  {
    title: 'Compensation & Payroll',
    items: NAV_ITEMS.slice(2, 5),
  },
  {
    title: 'Operations',
    items: NAV_ITEMS.slice(5, 10),
  },
]

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { user } = useAuth()
  const location = useLocation()

  const roleLabel: Record<string, string> = {
    platform_admin: 'Platform Admin',
    company_admin: 'Company Admin',
    hr_manager: 'HR Manager',
    department_manager: 'Dept. Manager',
    finance_manager: 'Finance Manager',
    employee: 'Employee',
  }

  const initials = user?.full_name
    ?.split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase() ?? '?'

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-30 w-64 flex flex-col transition-transform duration-300 ease-in-out',
          'lg:static lg:translate-x-0 lg:z-auto',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
        style={{ background: 'linear-gradient(180deg, #052e16 0%, #064e3b 100%)' }}
      >
        {/* Logo / Brand */}
        <div className="flex items-center justify-between px-5 py-5 border-b border-emerald-900/60">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg"
              style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
            >
              <Zap className="w-4.5 h-4.5 text-white" style={{ width: 18, height: 18 }} />
            </div>
            <div>
              <div className="text-white font-bold text-sm leading-tight">HRMS Platform</div>
              <div className="text-emerald-400 text-xs font-medium truncate max-w-[120px]">
                {user?.company_name ?? 'Enterprise Suite'}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden text-emerald-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-5 scrollbar-thin">
          {SECTION_GROUPS.map((group) => (
            <div key={group.title}>
              <p className="text-xs font-semibold uppercase tracking-widest text-emerald-600 px-3 mb-1.5">
                {group.title}
              </p>
              <div className="space-y-0.5">
                {group.items.filter((item) => item.href !== '/audit' ||
                  ['company_admin', 'platform_admin', 'hr_manager'].includes(user?.role ?? '')).map((item) => (
                  <SidebarItem
                    key={item.href}
                    item={item}
                    active={location.pathname.startsWith(item.href)}
                    onClick={onClose}
                  />
                ))}
              </div>
            </div>
          ))}

          {user?.role === 'platform_admin' && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-emerald-600 px-3 mb-1.5">
                Platform
              </p>
              <div className="space-y-0.5">
                {ADMIN_ITEMS.map((item) => (
                  <SidebarItem
                    key={item.href}
                    item={item}
                    active={location.pathname.startsWith(item.href)}
                    onClick={onClose}
                  />
                ))}
              </div>
            </div>
          )}
        </nav>

        {/* User Footer */}
        <div className="px-3 py-4 border-t border-emerald-900/60">
          <div className="flex items-center gap-3 px-2 py-2.5 rounded-xl hover:bg-white/5 transition-colors cursor-pointer">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-white text-sm font-bold shadow"
              style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
            >
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-white text-sm font-medium truncate">{user?.full_name}</div>
              <div className="text-emerald-400 text-xs truncate">
                {roleLabel[user?.role ?? ''] ?? user?.role}
              </div>
            </div>
            <div className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
          </div>
        </div>
      </aside>
    </>
  )
}

function SidebarItem({
  item,
  active,
  onClick,
}: {
  item: NavItem
  active: boolean
  onClick: () => void
}) {
  const Icon = item.icon

  if (item.comingSoon) {
    return (
      <div className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-not-allowed select-none">
        <Icon className="w-4 h-4 text-emerald-800 flex-shrink-0" />
        <span className="text-emerald-800 text-sm flex-1 truncate">{item.label}</span>
        <span className="text-xs text-emerald-700 bg-emerald-900/40 px-1.5 py-0.5 rounded font-medium">
          Soon
        </span>
      </div>
    )
  }

  return (
    <NavLink
      to={item.href}
      onClick={onClick}
      className={({ isActive }) =>
        clsx(
          'flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-150 group relative',
          isActive || active
            ? 'bg-emerald-500/20 text-white'
            : 'text-emerald-300 hover:text-white hover:bg-white/8',
        )
      }
    >
      {(active) && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-emerald-400 rounded-full" />
      )}
      <Icon
        className={clsx(
          'w-4 h-4 flex-shrink-0 transition-colors',
          active ? 'text-emerald-300' : 'text-emerald-500 group-hover:text-emerald-300',
        )}
      />
      <span className="text-sm font-medium flex-1 truncate">{item.label}</span>
      {item.badge && (
        <span className="text-xs bg-emerald-500 text-white px-1.5 py-0.5 rounded-full font-semibold">
          {item.badge}
        </span>
      )}
    </NavLink>
  )
}
