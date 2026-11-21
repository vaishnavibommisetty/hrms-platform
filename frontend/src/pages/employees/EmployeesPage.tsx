import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { employeesApi, departmentsApi } from '../../api/employees'
import type { Employee, Department, PaginatedResponse } from '../../types'
import {
  Search, Plus, Filter, ChevronLeft, ChevronRight,
  Users, Download, Eye, UserX, AlertTriangle, UserCheck, Clock,
  Building,
} from 'lucide-react'
import AddEmployeeModal from './AddEmployeeModal'

const STATUS_CONFIG: Record<string, { label: string; cls: string; dot: string }> = {
  active:     { label: 'Active',     cls: 'bg-emerald-50 text-emerald-700', dot: 'bg-emerald-500' },
  inactive:   { label: 'Inactive',   cls: 'bg-slate-100 text-slate-500',    dot: 'bg-slate-400'   },
  terminated: { label: 'Terminated', cls: 'bg-red-50 text-red-600',         dot: 'bg-red-500'     },
  on_leave:   { label: 'On Leave',   cls: 'bg-amber-50 text-amber-700',     dot: 'bg-amber-500'   },
}

const EMPLOYMENT_TYPE_LABEL: Record<string, string> = {
  full_time: 'Full-time',
  part_time: 'Part-time',
  contract: 'Contract',
  intern: 'Intern',
}

const EMPLOYMENT_TYPE_STYLE: Record<string, string> = {
  full_time: 'bg-blue-50 text-blue-700',
  part_time: 'bg-purple-50 text-purple-700',
  contract: 'bg-orange-50 text-orange-700',
  intern: 'bg-cyan-50 text-cyan-700',
}

// Avatar color palette
const AVATAR_GRADIENTS = [
  'linear-gradient(135deg, #10b981, #059669)',
  'linear-gradient(135deg, #6366f1, #4f46e5)',
  'linear-gradient(135deg, #f59e0b, #d97706)',
  'linear-gradient(135deg, #06b6d4, #0891b2)',
  'linear-gradient(135deg, #ec4899, #db2777)',
  'linear-gradient(135deg, #8b5cf6, #7c3aed)',
]

function avatarGradient(name: string) {
  const c = name.charCodeAt(0) % AVATAR_GRADIENTS.length
  return AVATAR_GRADIENTS[c]
}

export default function EmployeesPage() {
  const [data, setData] = useState<PaginatedResponse<Employee> | null>(null)
  const [departments, setDepartments] = useState<Department[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [search, setSearch] = useState('')
  const [deptFilter, setDeptFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 15

  const [addModalOpen, setAddModalOpen] = useState(false)

  const fetchEmployees = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = await employeesApi.list({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        department_id: deptFilter ? Number(deptFilter) : undefined,
        status: statusFilter || undefined,
      })
      setData(result)
    } catch {
      setError('Failed to load employees')
    } finally {
      setLoading(false)
    }
  }, [page, search, deptFilter, statusFilter])

  useEffect(() => { fetchEmployees() }, [fetchEmployees])
  useEffect(() => { departmentsApi.list().then((r) => setDepartments(r.items)) }, [])
  useEffect(() => { setPage(1) }, [search, deptFilter, statusFilter])

  const handleDeactivate = async (emp: Employee) => {
    if (!confirm(`Deactivate ${emp.full_name}? This will set their status to inactive.`)) return
    try {
      await employeesApi.deactivate(emp.id)
      fetchEmployees()
    } catch {
      alert('Failed to deactivate employee')
    }
  }

  const formatCurrency = (v: number | null) =>
    v ? `₹${v.toLocaleString('en-IN')}` : '—'

  // Computed stats
  const activeCount = data?.items.filter((e) => e.status === 'active').length ?? 0
  const onLeaveCount = data?.items.filter((e) => e.status === 'on_leave').length ?? 0

  return (
    <div className="p-6 lg:p-8 bg-slate-50/50 min-h-screen">

      {/* ─── Header ───────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Employees</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            Manage and view all employees in your organization
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-600 text-sm font-medium hover:bg-slate-50 hover:border-slate-300 transition-all shadow-sm">
            <Download className="w-4 h-4" />
            Export
          </button>
          <button
            onClick={() => setAddModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 text-white rounded-xl text-sm font-semibold transition-all shadow-sm hover:shadow-md hover:-translate-y-0.5"
            style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
          >
            <Plus className="w-4 h-4" />
            Add Employee
          </button>
        </div>
      </div>

      {/* ─── Stats Strip ──────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          {
            label: 'Total Employees',
            value: data?.total ?? '—',
            icon: Users,
            iconCls: 'text-indigo-600',
            iconBg: 'bg-indigo-50',
            cls: 'text-indigo-700',
          },
          {
            label: 'Active',
            value: activeCount,
            icon: UserCheck,
            iconCls: 'text-emerald-600',
            iconBg: 'bg-emerald-50',
            cls: 'text-emerald-700',
          },
          {
            label: 'On Leave',
            value: onLeaveCount,
            icon: Clock,
            iconCls: 'text-amber-600',
            iconBg: 'bg-amber-50',
            cls: 'text-amber-700',
          },
          {
            label: 'Departments',
            value: departments.length,
            icon: Building,
            iconCls: 'text-sky-600',
            iconBg: 'bg-sky-50',
            cls: 'text-sky-700',
          },
        ].map((s) => (
          <div
            key={s.label}
            className="bg-white rounded-2xl border border-slate-100 px-4 py-3.5 flex items-center gap-3 shadow-sm"
          >
            <div className={`w-9 h-9 ${s.iconBg} rounded-xl flex items-center justify-center flex-shrink-0`}>
              <s.icon className={`w-4 h-4 ${s.iconCls}`} />
            </div>
            <div>
              <div className={`text-xl font-bold tabular-nums ${s.cls}`}>{s.value}</div>
              <div className="text-xs text-slate-400 font-medium">{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ─── Filter Bar ───────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-3 flex flex-col sm:flex-row gap-2.5 mb-5">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, email or employee code…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-xl text-sm
                       placeholder:text-slate-400 focus:outline-none focus:ring-2
                       focus:ring-emerald-400 focus:border-transparent transition-all"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400 flex-shrink-0 ml-1" />
          <select
            value={deptFilter}
            onChange={(e) => setDeptFilter(e.target.value)}
            className="border border-slate-200 rounded-xl px-3 py-2.5 text-sm
                       focus:outline-none focus:ring-2 focus:ring-emerald-400
                       focus:border-transparent bg-white text-slate-700 transition-all"
          >
            <option value="">All Departments</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-slate-200 rounded-xl px-3 py-2.5 text-sm
                       focus:outline-none focus:ring-2 focus:ring-emerald-400
                       focus:border-transparent bg-white text-slate-700 transition-all"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="on_leave">On Leave</option>
            <option value="terminated">Terminated</option>
          </select>
        </div>
      </div>

      {/* ─── Table ────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-20 text-center">
            <div
              className="w-9 h-9 border-4 border-t-transparent rounded-full animate-spin mx-auto mb-3"
              style={{ borderColor: '#d1fae5', borderTopColor: 'transparent', borderLeftColor: '#10b981' }}
            />
            <p className="text-slate-400 text-sm">Loading employees…</p>
          </div>
        ) : error ? (
          <div className="py-16 flex flex-col items-center gap-3">
            <AlertTriangle className="w-10 h-10 text-red-300" />
            <p className="text-red-500 text-sm font-medium">{error}</p>
            <button
              onClick={fetchEmployees}
              className="text-emerald-600 text-sm font-medium hover:underline"
            >
              Retry
            </button>
          </div>
        ) : !data?.items.length ? (
          <div className="py-20 flex flex-col items-center gap-3">
            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center">
              <Users className="w-8 h-8 text-slate-300" />
            </div>
            <p className="text-slate-600 font-semibold">No employees found</p>
            <p className="text-slate-400 text-sm">Try adjusting your search or filters</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  {['Employee', 'Code', 'Department', 'Designation', 'Type', 'CTC', 'Status', ''].map(
                    (h) => (
                      <th
                        key={h}
                        className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3.5 whitespace-nowrap"
                      >
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {data.items.map((emp, idx) => (
                  <tr
                    key={emp.id}
                    className={`hover:bg-slate-50/70 transition-colors group border-b border-slate-50 ${
                      idx === data.items.length - 1 ? 'border-b-0' : ''
                    }`}
                  >
                    {/* Name + email */}
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 text-white text-xs font-bold shadow-sm"
                          style={{ background: avatarGradient(emp.full_name ?? 'A') }}
                        >
                          {emp.first_name?.charAt(0)}{emp.last_name?.charAt(0)}
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-slate-900">{emp.full_name}</div>
                          <div className="text-xs text-slate-400">{emp.email}</div>
                        </div>
                      </div>
                    </td>

                    {/* Code */}
                    <td className="px-4 py-3.5">
                      <span className="text-xs font-mono bg-slate-100 text-slate-600 px-2 py-1 rounded-lg">
                        {emp.employee_code}
                      </span>
                    </td>

                    {/* Department */}
                    <td className="px-4 py-3.5">
                      <span className="text-sm text-slate-700">{emp.department_name ?? '—'}</span>
                    </td>

                    {/* Designation */}
                    <td className="px-4 py-3.5">
                      <span className="text-sm text-slate-600 whitespace-nowrap">{emp.designation_name ?? '—'}</span>
                    </td>

                    {/* Employment type */}
                    <td className="px-4 py-3.5">
                      <span
                        className={`text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap ${
                          EMPLOYMENT_TYPE_STYLE[emp.employment_type] ?? 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {EMPLOYMENT_TYPE_LABEL[emp.employment_type] ?? emp.employment_type}
                      </span>
                    </td>

                    {/* CTC */}
                    <td className="px-4 py-3.5">
                      <span className="text-sm text-slate-700 font-medium tabular-nums whitespace-nowrap">
                        {formatCurrency(emp.gross_ctc)}
                      </span>
                    </td>

                    {/* Status */}
                    <td className="px-4 py-3.5">
                      {(() => {
                        const cfg = STATUS_CONFIG[emp.status] ?? {
                          label: emp.status,
                          cls: 'bg-slate-100 text-slate-500',
                          dot: 'bg-slate-400',
                        }
                        return (
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${cfg.cls}`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                            {cfg.label}
                          </span>
                        )
                      })()}
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Link
                          to={`/employees/${emp.id}`}
                          className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                          title="View details"
                        >
                          <Eye className="w-4 h-4" />
                        </Link>
                        {emp.status === 'active' && (
                          <button
                            onClick={() => handleDeactivate(emp)}
                            className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                            title="Deactivate"
                          >
                            <UserX className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ─── Pagination ─────────────────────────────────────── */}
        {data && data.total_pages > 1 && (
          <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between">
            <p className="text-sm text-slate-400">
              Showing{' '}
              <span className="font-medium text-slate-700">
                {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data.total)}
              </span>{' '}
              of{' '}
              <span className="font-medium text-slate-700">{data.total}</span> employees
            </p>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 rounded-xl border border-slate-200 disabled:opacity-30 hover:bg-slate-50 hover:border-slate-300 transition-all disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4 text-slate-600" />
              </button>
              {Array.from({ length: data.total_pages }, (_, i) => i + 1)
                .filter((p) => p === 1 || p === data.total_pages || Math.abs(p - page) <= 1)
                .map((p, i, arr) => (
                  <>
                    {i > 0 && arr[i - 1] !== p - 1 && (
                      <span key={`ellipsis-${p}`} className="text-slate-300 px-1 text-sm">…</span>
                    )}
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`w-9 h-9 rounded-xl text-sm font-medium transition-all ${
                        p === page
                          ? 'text-white shadow-sm'
                          : 'text-slate-600 hover:bg-slate-50 border border-slate-200'
                      }`}
                      style={p === page ? { background: 'linear-gradient(135deg, #10b981, #059669)' } : {}}
                    >
                      {p}
                    </button>
                  </>
                ))}
              <button
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                disabled={page === data.total_pages}
                className="p-2 rounded-xl border border-slate-200 disabled:opacity-30 hover:bg-slate-50 hover:border-slate-300 transition-all disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4 text-slate-600" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Add Employee Modal */}
      <AddEmployeeModal
        open={addModalOpen}
        departments={departments}
        onClose={() => setAddModalOpen(false)}
        onCreated={() => { setAddModalOpen(false); fetchEmployees() }}
      />
    </div>
  )
}
