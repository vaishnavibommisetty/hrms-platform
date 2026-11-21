import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { employeesApi } from '../../api/employees'
import type { Employee } from '../../types'
import { ArrowLeft, User, Briefcase, DollarSign, Calendar, Mail, Phone, MapPin, AlertTriangle } from 'lucide-react'

export default function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [employee, setEmployee] = useState<Employee | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    employeesApi
      .get(Number(id))
      .then(setEmployee)
      .catch(() => setError('Employee not found'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-slate-500 text-sm">Loading employee...</p>
        </div>
      </div>
    )
  }

  if (error || !employee) {
    return (
      <div className="p-8">
        <Link to="/employees" className="flex items-center gap-2 text-indigo-600 text-sm mb-6">
          <ArrowLeft className="w-4 h-4" /> Back to Employees
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 flex items-center gap-3">
          <AlertTriangle className="w-6 h-6 text-red-500" />
          <p className="text-red-700">{error || 'Employee not found'}</p>
        </div>
      </div>
    )
  }

  const statusColor: Record<string, string> = {
    active: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    inactive: 'bg-slate-100 text-slate-600 border-slate-200',
    terminated: 'bg-red-50 text-red-600 border-red-100',
    on_leave: 'bg-amber-50 text-amber-700 border-amber-100',
  }

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-4xl">
      {/* Back */}
      <Link
        to="/employees"
        className="inline-flex items-center gap-2 text-indigo-600 hover:text-indigo-700 text-sm font-medium"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Employees
      </Link>

      {/* Profile header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6">
        <div className="flex items-start gap-5">
          <div className="w-16 h-16 bg-gradient-to-br from-indigo-400 to-indigo-700 rounded-2xl flex items-center justify-center flex-shrink-0">
            <span className="text-white text-2xl font-bold">
              {employee.first_name?.charAt(0)}{employee.last_name?.charAt(0)}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-start gap-3 mb-1">
              <h1 className="text-2xl font-bold text-slate-900">{employee.full_name}</h1>
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${statusColor[employee.status] ?? 'bg-slate-100 text-slate-600'}`}>
                {employee.status}
              </span>
            </div>
            <p className="text-slate-500">{employee.designation_name ?? 'No designation'}</p>
            <p className="text-slate-400 text-sm">{employee.department_name}</p>
          </div>
          <span className="font-mono text-sm bg-slate-100 text-slate-600 px-3 py-1.5 rounded-lg">
            {employee.employee_code}
          </span>
        </div>
      </div>

      {/* Detail cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Contact Info */}
        <InfoCard title="Contact Information" icon={User}>
          <InfoRow icon={Mail} label="Email" value={employee.email} />
          <InfoRow icon={Phone} label="Phone" value={employee.phone} />
          <InfoRow icon={MapPin} label="Address" value={employee.address} />
        </InfoCard>

        {/* Employment Info */}
        <InfoCard title="Employment Details" icon={Briefcase}>
          <InfoRow icon={Calendar} label="Joining Date" value={
            new Date(employee.joining_date).toLocaleDateString('en-IN', {
              day: '2-digit', month: 'long', year: 'numeric',
            })
          } />
          <InfoRow icon={Briefcase} label="Type" value={employee.employment_type?.replace('_', ' ')} />
          <InfoRow icon={User} label="Manager" value={employee.manager_name} />
        </InfoCard>

        {/* Compensation */}
        <InfoCard title="Compensation" icon={DollarSign}>
          <InfoRow
            icon={DollarSign}
            label="Gross CTC"
            value={employee.gross_ctc ? `₹${employee.gross_ctc.toLocaleString('en-IN')}/month` : undefined}
          />
          <InfoRow icon={DollarSign} label="Annual CTC" value={
            employee.gross_ctc
              ? `₹${(employee.gross_ctc * 12).toLocaleString('en-IN')}/year`
              : undefined
          } />
        </InfoCard>

        {/* Personal */}
        <InfoCard title="Personal Details" icon={User}>
          <InfoRow icon={User} label="Gender" value={employee.gender?.replace('_', ' ')} />
          <InfoRow icon={Calendar} label="Date of Birth" value={
            employee.date_of_birth
              ? new Date(employee.date_of_birth).toLocaleDateString('en-IN', {
                  day: '2-digit', month: 'long', year: 'numeric',
                })
              : undefined
          } />
        </InfoCard>
      </div>
    </div>
  )
}

function InfoCard({
  title,
  icon: Icon,
  children,
}: {
  title: string
  icon: React.ComponentType<{ className?: string }>
  children: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5">
      <div className="flex items-center gap-2.5 mb-4">
        <Icon className="w-4 h-4 text-indigo-600" />
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  )
}

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value?: string | null
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
      <div className="min-w-0">
        <div className="text-xs text-slate-400 mb-0.5">{label}</div>
        <div className="text-sm text-slate-900 capitalize">{value ?? '—'}</div>
      </div>
    </div>
  )
}
