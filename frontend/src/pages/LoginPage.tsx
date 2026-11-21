import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Eye, EyeOff, Building2, AlertCircle } from 'lucide-react'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Invalid email or password'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const demoAccounts = [
    { label: 'Platform Admin', email: 'admin@hrmsplatform.com', role: 'platform_admin' },
    { label: 'ABC Tech Admin', email: 'admin@abctech.com', role: 'company_admin' },
    { label: 'ABC Tech HR', email: 'hr.manager@abct.com', role: 'hr_manager' },
  ]

  return (
    <div className="min-h-screen flex">
      {/* Left Panel — Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-900 flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center">
            <Building2 className="w-6 h-6 text-white" />
          </div>
          <span className="text-white text-xl font-bold">HRMS Platform</span>
        </div>

        <div>
          <h1 className="text-5xl font-extrabold text-white leading-tight mb-6">
            Enterprise HR &
            <span className="block text-indigo-400">Compensation</span>
            Management
          </h1>
          <p className="text-slate-400 text-lg leading-relaxed mb-10">
            Multi-tenant SaaS platform for managing employees, salary structures,
            performance appraisals, payroll, and configurable approval workflows.
          </p>

          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'Multi-tenant', desc: 'Company-level data isolation' },
              { label: 'Role-based', desc: '6 permission levels' },
              { label: 'Configurable', desc: 'JSON-driven workflows' },
              { label: 'Audit-ready', desc: 'Immutable audit logs' },
            ].map((f) => (
              <div key={f.label} className="bg-slate-800 rounded-lg p-4">
                <div className="text-indigo-400 font-semibold text-sm">{f.label}</div>
                <div className="text-slate-400 text-xs mt-1">{f.desc}</div>
              </div>
            ))}
          </div>
        </div>

        <p className="text-slate-600 text-sm">
          © 2025 HRMS Platform. Portfolio Project.
        </p>
      </div>

      {/* Right Panel — Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center gap-3 mb-8 lg:hidden">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center">
              <Building2 className="w-6 h-6 text-white" />
            </div>
            <span className="text-slate-900 text-xl font-bold">HRMS Platform</span>
          </div>

          <div className="mb-8">
            <h2 className="text-3xl font-bold text-slate-900">Welcome back</h2>
            <p className="text-slate-500 mt-2">Sign in to your account to continue</p>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-6 flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Email address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full px-4 py-3 border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400
                           focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                           transition-all duration-200"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-3 pr-12 border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400
                             focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                             transition-all duration-200"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400
                         text-white font-semibold rounded-xl transition-all duration-200
                         focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2
                         flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          {/* Demo Quick-Login */}
          <div className="mt-8">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="bg-white px-3 text-slate-500">Demo accounts (password: Admin@1234)</span>
              </div>
            </div>

            <div className="mt-4 space-y-2">
              {demoAccounts.map((acc) => (
                <button
                  key={acc.email}
                  type="button"
                  onClick={() => { setEmail(acc.email); setPassword('Admin@1234') }}
                  className="w-full text-left px-4 py-3 border border-slate-200 rounded-xl hover:border-indigo-300
                             hover:bg-indigo-50 transition-all duration-150 flex items-center justify-between"
                >
                  <span className="text-sm font-medium text-slate-800">{acc.label}</span>
                  <span className="text-xs text-slate-400 font-mono">{acc.email}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
