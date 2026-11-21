import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CalendarClock, ChevronRight, CreditCard, Plus, TrendingUp, Users } from 'lucide-react'
import { payrollApi } from '../../api/modules'
import {
  Alert, Badge, Button, Card, Empty, ErrorState, Field, Loading, MONTHS, Modal, Page, PageHeader, Select,
  Stat, StatGrid, Table, apiError, fmtDate, inr, lakhs, td, useLoad,
} from '../../components/ui/kit'

export default function PayrollPage() {
  const { data, loading, error, reload } = useLoad(payrollApi.runs)
  const [creating, setCreating] = useState(false)
  const latest = data?.find((r) => ['approved', 'paid'].includes(r.status))
  const pending = data?.filter((r) => ['draft', 'pending_approval'].includes(r.status)).length ?? 0
  const ytd = data?.filter((r) => r.year === new Date().getFullYear() && r.status !== 'cancelled')
    .reduce((s, r) => s + (r.total_net ?? 0), 0)

  return (
    <Page>
      <PageHeader title="Payroll" subtitle="Monthly payroll runs: process, approve and pay"
        actions={<Button icon={Plus} onClick={() => setCreating(true)}>New payroll run</Button>} />

      <StatGrid>
        <Stat label="Last approved payroll (net)" value={lakhs(latest?.total_net)} icon={CreditCard} hint={latest?.period} />
        <Stat label="Employees paid" value={latest?.total_employees ?? '—'} icon={Users} tone="sky" />
        <Stat label="Runs in progress" value={pending} icon={CalendarClock} tone="amber" />
        <Stat label={`Net paid in ${new Date().getFullYear()}`} value={lakhs(ytd)} icon={TrendingUp} tone="indigo" />
      </StatGrid>

      <Card padded={false} title="Payroll runs">
        {loading ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> :
          !data?.length ? <Empty title="No payroll runs yet" hint="Create a run for a month, then process it to generate payslips." /> :
            <Table head={['Period', 'Status', 'Employees', 'Gross', 'Deductions', 'Net pay', 'Processed', '']}>
              {data.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50/70">
                  <td className={td}><Link to={`/payroll/${r.id}`} className="font-semibold text-slate-900 hover:text-emerald-700">{r.period}</Link></td>
                  <td className={td}><Badge status={r.status} /></td>
                  <td className={td}>{r.total_employees ?? '—'}</td>
                  <td className={td + ' tabular-nums'}>{inr(r.total_gross)}</td>
                  <td className={td + ' tabular-nums text-rose-600'}>{inr(r.total_deductions)}</td>
                  <td className={td + ' tabular-nums font-semibold'}>{inr(r.total_net)}</td>
                  <td className={td + ' text-slate-400'}>{fmtDate(r.processed_at)}</td>
                  <td className={td}><Link to={`/payroll/${r.id}`} className="text-emerald-600"><ChevronRight className="w-4 h-4" /></Link></td>
                </tr>
              ))}
            </Table>}
      </Card>

      <NewRunModal open={creating} onClose={() => setCreating(false)} />
    </Page>
  )
}

function NewRunModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const now = new Date()
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [year, setYear] = useState(now.getFullYear())
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const navigate = useNavigate()
  useEffect(() => { if (open) setError('') }, [open])
  const save = async () => {
    setSaving(true); setError('')
    try { const r = await payrollApi.create(month, year); navigate(`/payroll/${r.id}`) }
    catch (e) { setError(apiError(e)) } finally { setSaving(false) }
  }
  return (
    <Modal open={open} onClose={onClose} title="New payroll run"
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={save} loading={saving}>Create</Button></>}>
      {error && <Alert>{error}</Alert>}
      <div className="grid grid-cols-2 gap-4">
        <Field label="Month"><Select value={month} onChange={(e) => setMonth(Number(e.target.value))}>
          {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}</Select></Field>
        <Field label="Year"><Select value={year} onChange={(e) => setYear(Number(e.target.value))}>
          {[now.getFullYear() - 1, now.getFullYear(), now.getFullYear() + 1].map((y) => <option key={y}>{y}</option>)}</Select></Field>
      </div>
      <p className="text-xs text-slate-400">Only one run is allowed per month. After creating it, click Process to calculate payslips.</p>
    </Modal>
  )
}
