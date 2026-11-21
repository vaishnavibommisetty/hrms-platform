import { useState, useEffect, FormEvent } from 'react'
import { employeesApi, departmentsApi } from '../../api/employees'
import type { Department, Designation, EmployeeCreate } from '../../types'
import { X, AlertCircle, Loader2 } from 'lucide-react'

interface Props {
  open: boolean
  departments: Department[]
  onClose: () => void
  onCreated: () => void
}

export default function AddEmployeeModal({ open, departments, onClose, onCreated }: Props) {
  const [designations, setDesignations] = useState<Designation[]>([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const [form, setForm] = useState<EmployeeCreate>({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    gender: undefined,
    date_of_birth: '',
    department_id: 0,
    designation_id: undefined,
    joining_date: new Date().toISOString().split('T')[0],
    employment_type: 'full_time',
    gross_ctc: undefined,
    address: '',
    create_login: false,
    login_password: '',
  })

  useEffect(() => {
    if (form.department_id) {
      departmentsApi
        .getDesignations(form.department_id)
        .then(setDesignations)
        .catch(() => setDesignations([]))
    } else {
      setDesignations([])
    }
  }, [form.department_id])

  const set = (k: keyof EmployeeCreate, v: unknown) =>
    setForm((prev) => ({ ...prev, [k]: v }))

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!form.department_id) { setError('Please select a department'); return }
    setError('')
    setSaving(true)
    try {
      await employeesApi.create({
        ...form,
        gross_ctc: form.gross_ctc || undefined,
        designation_id: form.designation_id || undefined,
        login_password: form.create_login ? form.login_password : undefined,
      })
      onCreated()
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to create employee'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Add New Employee</h2>
            <p className="text-xs text-slate-500 mt-0.5">Employee code will be auto-generated</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-lg text-slate-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="overflow-y-auto scrollbar-thin">
          <div className="px-6 py-5 space-y-5">
            {error && (
              <div className="flex items-center gap-3 p-3.5 bg-red-50 border border-red-200 rounded-xl">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}

            {/* Name row */}
            <div className="grid grid-cols-2 gap-4">
              <Field label="First Name *">
                <input
                  required
                  value={form.first_name}
                  onChange={(e) => set('first_name', e.target.value)}
                  placeholder="Priya"
                  className={inputCls}
                />
              </Field>
              <Field label="Last Name *">
                <input
                  required
                  value={form.last_name}
                  onChange={(e) => set('last_name', e.target.value)}
                  placeholder="Sharma"
                  className={inputCls}
                />
              </Field>
            </div>

            {/* Email + Phone */}
            <div className="grid grid-cols-2 gap-4">
              <Field label="Email *">
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => set('email', e.target.value)}
                  placeholder="priya@company.com"
                  className={inputCls}
                />
              </Field>
              <Field label="Phone">
                <input
                  value={form.phone}
                  onChange={(e) => set('phone', e.target.value)}
                  placeholder="+91-9876543210"
                  className={inputCls}
                />
              </Field>
            </div>

            {/* Gender + DOB */}
            <div className="grid grid-cols-2 gap-4">
              <Field label="Gender">
                <select
                  value={form.gender ?? ''}
                  onChange={(e) => set('gender', e.target.value || undefined)}
                  className={inputCls}
                >
                  <option value="">Select</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                  <option value="prefer_not_to_say">Prefer not to say</option>
                </select>
              </Field>
              <Field label="Date of Birth">
                <input
                  type="date"
                  value={form.date_of_birth ?? ''}
                  onChange={(e) => set('date_of_birth', e.target.value)}
                  className={inputCls}
                />
              </Field>
            </div>

            {/* Department + Designation */}
            <div className="grid grid-cols-2 gap-4">
              <Field label="Department *">
                <select
                  required
                  value={form.department_id || ''}
                  onChange={(e) => { set('department_id', Number(e.target.value)); set('designation_id', undefined) }}
                  className={inputCls}
                >
                  <option value="">Select department</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Designation">
                <select
                  value={form.designation_id ?? ''}
                  onChange={(e) => set('designation_id', e.target.value ? Number(e.target.value) : undefined)}
                  disabled={!form.department_id}
                  className={inputCls}
                >
                  <option value="">Select designation</option>
                  {designations.map((d) => (
                    <option key={d.id} value={d.id}>{d.name} (L{d.level})</option>
                  ))}
                </select>
              </Field>
            </div>

            {/* Joining date + Employment type */}
            <div className="grid grid-cols-2 gap-4">
              <Field label="Joining Date *">
                <input
                  type="date"
                  required
                  value={form.joining_date}
                  onChange={(e) => set('joining_date', e.target.value)}
                  className={inputCls}
                />
              </Field>
              <Field label="Employment Type *">
                <select
                  required
                  value={form.employment_type}
                  onChange={(e) => set('employment_type', e.target.value as EmployeeCreate['employment_type'])}
                  className={inputCls}
                >
                  <option value="full_time">Full-time</option>
                  <option value="part_time">Part-time</option>
                  <option value="contract">Contract</option>
                  <option value="intern">Intern</option>
                </select>
              </Field>
            </div>

            {/* CTC */}
            <Field label="Gross CTC (₹/month)">
              <input
                type="number"
                min={0}
                value={form.gross_ctc ?? ''}
                onChange={(e) => set('gross_ctc', e.target.value ? Number(e.target.value) : undefined)}
                placeholder="40000"
                className={inputCls}
              />
            </Field>

            {/* Address */}
            <Field label="Address">
              <textarea
                value={form.address ?? ''}
                onChange={(e) => set('address', e.target.value)}
                placeholder="123 MG Road, Bengaluru, Karnataka"
                rows={2}
                className={inputCls + ' resize-none'}
              />
            </Field>

            {/* Create login account */}
            <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.create_login ?? false}
                  onChange={(e) => set('create_login', e.target.checked)}
                  className="w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
                />
                <div>
                  <span className="text-sm font-medium text-indigo-900">Create login account</span>
                  <p className="text-xs text-indigo-600 mt-0.5">Allows this employee to log in with EMPLOYEE role</p>
                </div>
              </label>
              {form.create_login && (
                <div className="mt-3">
                  <input
                    type="password"
                    required={form.create_login}
                    value={form.login_password ?? ''}
                    onChange={(e) => set('login_password', e.target.value)}
                    placeholder="Set initial password"
                    className={inputCls + ' bg-white'}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-white px-6 py-4 border-t border-slate-200 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 rounded-xl transition-colors flex items-center gap-2"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {saving ? 'Creating…' : 'Create Employee'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-700 mb-1.5">{label}</label>
      {children}
    </div>
  )
}

const inputCls =
  'w-full px-3.5 py-2.5 border border-slate-200 rounded-xl text-sm text-slate-900 ' +
  'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ' +
  'placeholder-slate-400 disabled:bg-slate-50 disabled:text-slate-400 transition-all'
