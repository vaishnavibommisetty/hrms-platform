import { ReactNode, useCallback, useEffect, useState } from 'react'
import { AlertTriangle, Inbox, X } from 'lucide-react'
import clsx from 'clsx'

// ─── Formatting ──────────────────────────────────────────────────────────
export const inr = (v: number | null | undefined, decimals = 0) =>
  v === null || v === undefined
    ? '—'
    : `₹${Number(v).toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`

export const lakhs = (v: number | null | undefined) =>
  v === null || v === undefined ? '—' : `₹${(Number(v) / 100000).toFixed(2)} L`

export const fmtDate = (v: string | null | undefined) =>
  v ? new Date(v).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : '—'

export const fmtDateTime = (v: string | null | undefined) =>
  v
    ? new Date(v.endsWith('Z') || v.includes('+') ? v : `${v}Z`).toLocaleString('en-IN', {
        day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
      })
    : '—'

export const titleCase = (s: string | null | undefined) =>
  (s ?? '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

/** Pull a readable message out of an API error (FastAPI detail string or 422 list). */
export function apiError(err: unknown, fallback = 'Something went wrong'): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    const d = detail[0] as { loc?: (string | number)[]; msg?: string }
    const field = d.loc?.filter((x) => x !== 'body').join(' → ')
    return field ? `${field}: ${d.msg}` : d.msg ?? fallback
  }
  return fallback
}

// ─── Data loading hook ───────────────────────────────────────────────────
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(fn, deps)
  const reload = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData(await load())
    } catch (e) {
      setError(apiError(e, 'Could not load data'))
    } finally {
      setLoading(false)
    }
  }, [load])
  useEffect(() => { reload() }, [reload])
  return { data, loading, error, reload, setData }
}

// ─── Layout pieces ───────────────────────────────────────────────────────
export function Page({ children }: { children: ReactNode }) {
  return <div className="p-6 lg:p-8 bg-slate-50/50 min-h-full">{children}</div>
}

export function PageHeader({ title, subtitle, actions, back }: {
  title: ReactNode; subtitle?: ReactNode; actions?: ReactNode; back?: ReactNode
}) {
  return (
    <div className="mb-6">
      {back && <div className="mb-3">{back}</div>}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
          {subtitle && <p className="text-slate-400 text-sm mt-0.5">{subtitle}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  )
}

export function Card({ children, className, title, actions, padded = true }: {
  children: ReactNode; className?: string; title?: ReactNode; actions?: ReactNode; padded?: boolean
}) {
  return (
    <div className={clsx('bg-white rounded-2xl border border-slate-100 shadow-sm', className)}>
      {(title || actions) && (
        <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-slate-100">
          <div className="font-semibold text-slate-800 text-sm">{title}</div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={clsx(padded && 'p-5')}>{children}</div>
    </div>
  )
}

const TONES = {
  emerald: ['bg-emerald-50', 'text-emerald-600', 'text-emerald-700'],
  indigo: ['bg-indigo-50', 'text-indigo-600', 'text-indigo-700'],
  amber: ['bg-amber-50', 'text-amber-600', 'text-amber-700'],
  sky: ['bg-sky-50', 'text-sky-600', 'text-sky-700'],
  rose: ['bg-rose-50', 'text-rose-600', 'text-rose-700'],
  slate: ['bg-slate-100', 'text-slate-500', 'text-slate-700'],
} as const
export type Tone = keyof typeof TONES

export function Stat({ label, value, icon: Icon, tone = 'emerald', hint }: {
  label: string; value: ReactNode; icon: React.ComponentType<{ className?: string }>; tone?: Tone; hint?: ReactNode
}) {
  const [bg, ic, tx] = TONES[tone]
  return (
    <div className="bg-white rounded-2xl border border-slate-100 px-4 py-3.5 flex items-center gap-3 shadow-sm">
      <div className={`w-10 h-10 ${bg} rounded-xl flex items-center justify-center flex-shrink-0`}>
        <Icon className={`w-[18px] h-[18px] ${ic}`} />
      </div>
      <div className="min-w-0">
        <div className={`text-xl font-bold tabular-nums truncate ${tx}`}>{value}</div>
        <div className="text-xs text-slate-400 font-medium truncate">{label}</div>
        {hint && <div className="text-[11px] text-slate-400 truncate">{hint}</div>}
      </div>
    </div>
  )
}

export function StatGrid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">{children}</div>
}

// ─── Status badge ────────────────────────────────────────────────────────
const BADGE: Record<string, string> = {
  // positive
  approved: 'bg-emerald-50 text-emerald-700 ring-emerald-200', paid: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  completed: 'bg-emerald-50 text-emerald-700 ring-emerald-200', passed: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  active: 'bg-emerald-50 text-emerald-700 ring-emerald-200', closed: 'bg-slate-100 text-slate-600 ring-slate-200',
  verified: 'bg-teal-50 text-teal-700 ring-teal-200', fixed: 'bg-teal-50 text-teal-700 ring-teal-200',
  // in flight
  pending_approval: 'bg-amber-50 text-amber-700 ring-amber-200', pending: 'bg-amber-50 text-amber-700 ring-amber-200',
  in_progress: 'bg-sky-50 text-sky-700 ring-sky-200', processing: 'bg-sky-50 text-sky-700 ring-sky-200',
  self_review: 'bg-sky-50 text-sky-700 ring-sky-200', manager_review: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  hr_review: 'bg-indigo-50 text-indigo-700 ring-indigo-200', finance_review: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  draft: 'bg-slate-100 text-slate-600 ring-slate-200', not_run: 'bg-slate-100 text-slate-500 ring-slate-200',
  skipped: 'bg-slate-100 text-slate-500 ring-slate-200', open: 'bg-amber-50 text-amber-700 ring-amber-200',
  // negative
  rejected: 'bg-rose-50 text-rose-700 ring-rose-200', failed: 'bg-rose-50 text-rose-700 ring-rose-200',
  cancelled: 'bg-slate-100 text-slate-500 ring-slate-200', blocked: 'bg-orange-50 text-orange-700 ring-orange-200',
  reopened: 'bg-rose-50 text-rose-700 ring-rose-200', wont_fix: 'bg-slate-100 text-slate-500 ring-slate-200',
  critical: 'bg-rose-600 text-white ring-rose-600', high: 'bg-orange-50 text-orange-700 ring-orange-200',
  medium: 'bg-amber-50 text-amber-700 ring-amber-200', low: 'bg-slate-100 text-slate-600 ring-slate-200',
  inactive: 'bg-slate-100 text-slate-500 ring-slate-200',
}

export function Badge({ status, label }: { status: string | null | undefined; label?: string }) {
  if (!status) return <span className="text-slate-300">—</span>
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold ring-1 ring-inset whitespace-nowrap',
      BADGE[status] ?? 'bg-slate-100 text-slate-600 ring-slate-200')}>
      {label ?? titleCase(status)}
    </span>
  )
}

// ─── Buttons ─────────────────────────────────────────────────────────────
type BtnVariant = 'primary' | 'secondary' | 'danger' | 'ghost'
export function Button({ children, variant = 'primary', icon: Icon, loading, className, ...rest }:
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: BtnVariant; icon?: React.ComponentType<{ className?: string }>; loading?: boolean
  }) {
  const styles: Record<BtnVariant, string> = {
    primary: 'text-white shadow-sm hover:shadow-md bg-gradient-to-br from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700',
    secondary: 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300 shadow-sm',
    danger: 'bg-white border border-rose-200 text-rose-600 hover:bg-rose-50',
    ghost: 'text-slate-600 hover:bg-slate-100',
  }
  return (
    <button
      {...rest}
      disabled={rest.disabled || loading}
      className={clsx('inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap',
        styles[variant], className)}
    >
      {loading ? <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        : Icon && <Icon className="w-4 h-4" />}
      {children}
    </button>
  )
}

// ─── States ──────────────────────────────────────────────────────────────
export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="py-20 text-center">
      <div className="w-9 h-9 border-4 border-emerald-100 border-l-emerald-500 rounded-full animate-spin mx-auto mb-3" />
      <p className="text-slate-400 text-sm">{label}</p>
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="py-16 flex flex-col items-center gap-3 text-center">
      <AlertTriangle className="w-10 h-10 text-rose-300" />
      <p className="text-rose-600 text-sm font-medium max-w-md">{message}</p>
      {onRetry && <button onClick={onRetry} className="text-emerald-600 text-sm font-medium hover:underline">Retry</button>}
    </div>
  )
}

export function Empty({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="py-14 flex flex-col items-center gap-2 text-center">
      <div className="w-14 h-14 bg-slate-100 rounded-2xl flex items-center justify-center mb-1">
        <Inbox className="w-7 h-7 text-slate-300" />
      </div>
      <p className="text-slate-600 font-semibold">{title}</p>
      {hint && <p className="text-slate-400 text-sm max-w-sm">{hint}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function Alert({ children, tone = 'rose' }: { children: ReactNode; tone?: 'rose' | 'amber' | 'emerald' | 'sky' }) {
  const s = {
    rose: 'bg-rose-50 border-rose-200 text-rose-700', amber: 'bg-amber-50 border-amber-200 text-amber-800',
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-800', sky: 'bg-sky-50 border-sky-200 text-sky-800',
  }[tone]
  return <div className={`border rounded-xl px-4 py-3 text-sm ${s}`}>{children}</div>
}

// ─── Table ───────────────────────────────────────────────────────────────
export function Table({ head, children, minWidth }: { head: ReactNode[]; children: ReactNode; minWidth?: number }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full" style={minWidth ? { minWidth } : undefined}>
        <thead>
          <tr className="bg-slate-50 border-b border-slate-100">
            {head.map((h, i) => (
              <th key={i} className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3 whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50">{children}</tbody>
      </table>
    </div>
  )
}

export const td = 'px-4 py-3 text-sm text-slate-700'
export const tdNum = 'px-4 py-3 text-sm text-slate-700 tabular-nums text-right'

// ─── Tabs ────────────────────────────────────────────────────────────────
export function Tabs<T extends string>({ tabs, value, onChange }: {
  tabs: { id: T; label: string; count?: number }[]; value: T; onChange: (v: T) => void
}) {
  return (
    <div className="flex gap-1 bg-white border border-slate-100 rounded-xl p-1 shadow-sm mb-5 w-fit max-w-full overflow-x-auto">
      {tabs.map((t) => (
        <button key={t.id} onClick={() => onChange(t.id)}
          className={clsx('px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap',
            value === t.id ? 'bg-emerald-50 text-emerald-700' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50')}>
          {t.label}
          {t.count !== undefined && (
            <span className={clsx('ml-2 text-xs px-1.5 py-0.5 rounded-md', value === t.id ? 'bg-emerald-100' : 'bg-slate-100')}>{t.count}</span>
          )}
        </button>
      ))}
    </div>
  )
}

// ─── Modal ───────────────────────────────────────────────────────────────
export function Modal({ open, title, onClose, children, footer, wide }: {
  open: boolean; title: ReactNode; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-start sm:items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm overflow-y-auto" onMouseDown={onClose}>
      <div className={clsx('bg-white rounded-2xl shadow-2xl w-full my-8', wide ? 'max-w-3xl' : 'max-w-lg')} onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="font-bold text-slate-900">{title}</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"><X className="w-4 h-4" /></button>
        </div>
        <div className="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">{children}</div>
        {footer && <div className="px-6 py-4 border-t border-slate-100 flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  )
}

// ─── Form fields ─────────────────────────────────────────────────────────
const inputCls = 'w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent bg-white text-slate-800 placeholder:text-slate-400 disabled:bg-slate-50'

export function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs font-semibold text-slate-600 mb-1.5">{label}</span>
      {children}
      {hint && <span className="block text-xs text-slate-400 mt-1">{hint}</span>}
    </label>
  )
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={clsx(inputCls, props.className)} />
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={clsx(inputCls, props.className)} />
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea rows={3} {...props} className={clsx(inputCls, props.className)} />
}

// ─── Progress bar ────────────────────────────────────────────────────────
export function Progress({ value, tone = 'emerald' }: { value: number; tone?: 'emerald' | 'amber' | 'rose' }) {
  const color = { emerald: 'bg-emerald-500', amber: 'bg-amber-500', rose: 'bg-rose-500' }[tone]
  return (
    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
      <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  )
}

export const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
  'September', 'October', 'November', 'December']
