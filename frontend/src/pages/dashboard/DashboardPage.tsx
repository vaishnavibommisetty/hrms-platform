import { useEffect, useState } from 'react'
import { dashboardApi } from '../../api/dashboard'
import type { DashboardMetrics } from '../../types'
import { useAuth } from '../../context/AuthContext'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import {
  Users, Building2, DollarSign, TrendingUp,
  CheckSquare, Bug, Clock, AlertTriangle, ArrowUpRight, ArrowDownRight,
  Activity, Layers,
} from 'lucide-react'

// ─── Metric Card ──────────────────────────────────────────────────
interface KpiCardProps {
  label: string
  value: string | number
  sub?: string
  icon: React.ComponentType<{ className?: string }>
  gradient: string
  iconColor: string
  trend?: { value: string; positive: boolean }
  accent?: string
}

function KpiCard({ label, value, sub, icon: Icon, gradient, iconColor, trend, accent = '#10b981' }: KpiCardProps) {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-5 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group">
      <div className="flex items-start justify-between mb-3">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm"
          style={{ background: gradient }}
        >
          <Icon className={`w-5 h-5 ${iconColor}`} />
        </div>
        {trend && (
          <div
            className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full ${
              trend.positive
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-red-50 text-red-600'
            }`}
          >
            {trend.positive
              ? <ArrowUpRight className="w-3 h-3" />
              : <ArrowDownRight className="w-3 h-3" />}
            {trend.value}
          </div>
        )}
      </div>
      <div className="text-2xl font-bold text-slate-900 mb-0.5 tabular-nums">{value}</div>
      <div className="text-sm font-medium text-slate-600">{label}</div>
      {sub && <div className="text-xs text-slate-400 mt-0.5">{sub}</div>}
      {/* Bottom accent bar */}
      <div
        className="mt-4 h-0.5 rounded-full opacity-20 group-hover:opacity-40 transition-opacity"
        style={{ background: accent }}
      />
    </div>
  )
}

// ─── Pie colors ───────────────────────────────────────────────────
const DEPT_COLORS = ['#10b981', '#059669', '#6366f1', '#8b5cf6', '#06b6d4', '#f59e0b', '#ef4444']

// ─── Custom Tooltip ───────────────────────────────────────────────
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-slate-200 rounded-xl px-3 py-2.5 shadow-lg text-xs">
      <p className="font-semibold text-slate-700 mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} className="text-slate-600">
          <span style={{ color: p.fill ?? p.color }}>{p.name}: </span>
          <span className="font-semibold">{p.value}</span>
        </p>
      ))}
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    dashboardApi
      .getMetrics()
      .then(setMetrics)
      .catch(() => setError('Failed to load dashboard metrics'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-96">
        <div className="text-center">
          <div
            className="w-10 h-10 border-4 border-t-transparent rounded-full animate-spin mx-auto mb-3"
            style={{ borderColor: '#d1fae5', borderTopColor: 'transparent', borderLeftColor: '#10b981' }}
          />
          <p className="text-slate-400 text-sm">Loading dashboard…</p>
        </div>
      </div>
    )
  }

  if (error || !metrics) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-100 rounded-2xl p-6 flex items-center gap-3">
          <AlertTriangle className="w-6 h-6 text-red-500 flex-shrink-0" />
          <p className="text-red-700 text-sm">{error || 'No data available'}</p>
        </div>
      </div>
    )
  }

  const formatCurrency = (v: number | null) =>
    v == null ? '—' : `₹${(v / 100000).toFixed(1)}L`

  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 17) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div className="p-6 lg:p-8 space-y-7 bg-slate-50/50 min-h-screen">

      {/* ─── Welcome Banner ─────────────────────────────────────── */}
      <div
        className="rounded-2xl px-6 py-5 flex items-center justify-between overflow-hidden relative"
        style={{
          background: 'linear-gradient(135deg, #064e3b 0%, #065f46 50%, #047857 100%)',
        }}
      >
        {/* Background decoration */}
        <div
          className="absolute -right-10 -top-10 w-48 h-48 rounded-full opacity-10"
          style={{ background: 'white' }}
        />
        <div
          className="absolute right-24 bottom-0 w-24 h-24 rounded-full opacity-5"
          style={{ background: 'white' }}
        />

        <div className="relative z-10">
          <p className="text-emerald-300 text-sm font-medium mb-0.5">{greeting()},</p>
          <h1 className="text-white text-xl font-bold">{user?.full_name?.split(' ')[0]} 👋</h1>
          <p className="text-emerald-300 text-sm mt-1">
            {user?.company_name
              ? `${user.company_name} · HR Dashboard`
              : 'Platform Overview'}
          </p>
        </div>

        <div className="hidden sm:flex items-center gap-4 relative z-10">
          <div className="text-right">
            <p className="text-emerald-300 text-xs mb-0.5">Total Employees</p>
            <p className="text-white text-2xl font-bold tabular-nums">{metrics.total_employees}</p>
          </div>
          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center"
            style={{ background: 'rgba(255,255,255,0.15)' }}
          >
            <Activity className="w-6 h-6 text-white" />
          </div>
        </div>
      </div>

      {/* ─── KPI Grid ───────────────────────────────────────────── */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Layers className="w-4 h-4 text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Key Metrics</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Total Employees"
            value={metrics.total_employees}
            sub="Active headcount"
            icon={Users}
            gradient="linear-gradient(135deg, #d1fae5, #a7f3d0)"
            iconColor="text-emerald-700"
            accent="#10b981"
            trend={{ value: '+3 this month', positive: true }}
          />
          {user?.role === 'platform_admin' && metrics.total_companies != null && (
            <KpiCard
              label="Companies"
              value={metrics.total_companies}
              sub="Registered tenants"
              icon={Building2}
              gradient="linear-gradient(135deg, #ede9fe, #ddd6fe)"
              iconColor="text-violet-700"
              accent="#8b5cf6"
            />
          )}
          <KpiCard
            label="Monthly Payroll"
            value={formatCurrency(metrics.monthly_payroll)}
            sub="Latest approved run (net)"
            icon={DollarSign}
            gradient="linear-gradient(135deg, #dcfce7, #bbf7d0)"
            iconColor="text-green-700"
            accent="#16a34a"
          />
          <KpiCard
            label="Budget Utilization"
            value={metrics.budget_utilization_pct != null ? `${metrics.budget_utilization_pct}%` : '—'}
            sub="Compensation cycle"
            icon={TrendingUp}
            gradient="linear-gradient(135deg, #e0f2fe, #bae6fd)"
            iconColor="text-sky-700"
            accent="#0284c7"
          />
          <KpiCard
            label="Avg Performance"
            value={metrics.avg_performance_score != null ? `${metrics.avg_performance_score}/100` : '—'}
            sub="Across completed reviews"
            icon={TrendingUp}
            gradient="linear-gradient(135deg, #fef3c7, #fde68a)"
            iconColor="text-amber-700"
            accent="#d97706"
          />
          <KpiCard
            label="Pending Approvals"
            value={metrics.pending_approvals}
            sub="Awaiting action"
            icon={Clock}
            gradient="linear-gradient(135deg, #ffedd5, #fed7aa)"
            iconColor="text-orange-700"
            accent="#ea580c"
            trend={metrics.pending_approvals > 0 ? { value: 'Action needed', positive: false } : undefined}
          />
          <KpiCard
            label="QA Pass Rate"
            value={metrics.qa_pass_pct != null ? `${metrics.qa_pass_pct}%` : '—'}
            sub="Test executions"
            icon={CheckSquare}
            gradient="linear-gradient(135deg, #ccfbf1, #99f6e4)"
            iconColor="text-teal-700"
            accent="#0d9488"
          />
          <KpiCard
            label="Open Defects"
            value={metrics.open_defects}
            sub="Requiring resolution"
            icon={Bug}
            gradient="linear-gradient(135deg, #fee2e2, #fecaca)"
            iconColor="text-red-700"
            accent="#dc2626"
            trend={metrics.open_defects > 0 ? { value: `${metrics.open_defects} open`, positive: false } : undefined}
          />
        </div>
      </div>

      {/* ─── Charts Row ─────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Bar chart — wider */}
        <div className="lg:col-span-3 bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
          <div className="flex items-start justify-between mb-5">
            <div>
              <h3 className="text-base font-semibold text-slate-900">Headcount by Department</h3>
              <p className="text-xs text-slate-400 mt-0.5">Employee distribution across departments</p>
            </div>
            <span className="text-xs bg-emerald-50 text-emerald-700 font-medium px-2.5 py-1 rounded-full">
              {metrics.department_breakdown?.length ?? 0} depts
            </span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={metrics.department_breakdown}
              barSize={28}
              margin={{ top: 0, right: 4, left: -20, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f8fafc" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                tickLine={false}
                axisLine={false}
                width={28}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f0fdf4' }} />
              <Bar
                dataKey="count"
                name="Employees"
                fill="#10b981"
                radius={[6, 6, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Donut chart */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
          <div className="mb-5">
            <h3 className="text-base font-semibold text-slate-900">Department Share</h3>
            <p className="text-xs text-slate-400 mt-0.5">Proportional distribution</p>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={metrics.department_breakdown}
                dataKey="count"
                nameKey="name"
                cx="50%"
                cy="45%"
                outerRadius={80}
                innerRadius={48}
                paddingAngle={3}
                strokeWidth={0}
              >
                {metrics.department_breakdown.map((_, i) => (
                  <Cell key={i} fill={DEPT_COLORS[i % DEPT_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                iconType="circle"
                iconSize={7}
                formatter={(v) => <span style={{ fontSize: 11, color: '#64748b' }}>{v}</span>}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ─── Recent Joiners ──────────────────────────────────────── */}
      {metrics.recent_employees?.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-50 flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-slate-900">Recent Joiners</h3>
              <p className="text-xs text-slate-400 mt-0.5">Latest employees added to the system</p>
            </div>
            <span className="text-xs text-emerald-600 font-medium hover:underline cursor-pointer">
              View all →
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50/60">
                  {['Employee', 'Department', 'Joining Date', 'Status'].map((h) => (
                    <th
                      key={h}
                      className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-6 py-3"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {metrics.recent_employees.map((emp) => (
                  <tr key={emp.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-white text-xs font-bold"
                          style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
                        >
                          {(emp.name ?? '?').charAt(0).toUpperCase()}
                        </div>
                        <span className="text-sm font-semibold text-slate-900">{emp.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-3.5">
                      <span className="text-sm text-slate-600">{emp.department}</span>
                    </td>
                    <td className="px-6 py-3.5">
                      <span className="text-sm text-slate-600">
                        {new Date(emp.joining_date).toLocaleDateString('en-IN', {
                          day: '2-digit', month: 'short', year: 'numeric',
                        })}
                      </span>
                    </td>
                    <td className="px-6 py-3.5">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                          emp.status === 'active'
                            ? 'bg-emerald-50 text-emerald-700'
                            : 'bg-slate-100 text-slate-500'
                        }`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            emp.status === 'active' ? 'bg-emerald-500' : 'bg-slate-400'
                          }`}
                        />
                        {(emp.status ?? 'active').replace('_', ' ').replace(/^./, (c) => c.toUpperCase())}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
