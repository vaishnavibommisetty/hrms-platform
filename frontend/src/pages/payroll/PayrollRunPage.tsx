import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Ban, CheckCircle2, Cpu, GitBranch, IndianRupee, Printer, Search, Users, Wallet } from 'lucide-react'
import { payrollApi, type Payslip } from '../../api/modules'
import { useAuth } from '../../context/AuthContext'
import {
  Alert, Badge, Button, Card, Empty, ErrorState, Input, Loading, Modal, Page, PageHeader, Stat, StatGrid,
  Table, apiError, fmtDateTime, inr, td, useLoad,
} from '../../components/ui/kit'

export default function PayrollRunPage() {
  const id = Number(useParams().id)
  const { user } = useAuth()
  const { data: run, loading, error, reload } = useLoad(() => payrollApi.run(id), [id])
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState<{ tone: 'rose' | 'emerald' | 'amber'; text: string; list?: string[] } | null>(null)
  const [q, setQ] = useState('')
  const [slip, setSlip] = useState<number | null>(null)

  const act = async (name: string, fn: () => Promise<unknown>, success: string) => {
    setBusy(name); setMsg(null)
    try {
      const r = await fn() as { skipped?: string[]; approval_request_id?: number | null }
      setMsg({ tone: 'emerald', text: success + (r?.approval_request_id ? ' It is now waiting in the approval workflow.' : ''), list: r?.skipped?.length ? r.skipped : undefined })
      reload()
    } catch (e) { setMsg({ tone: 'rose', text: apiError(e) }) } finally { setBusy('') }
  }

  if (loading && !run) return <Page><Loading /></Page>
  if (error || !run) return <Page><ErrorState message={error || 'Not found'} onRetry={reload} /></Page>

  const role = user?.role ?? ''
  const canProcess = ['company_admin', 'hr_manager', 'finance_manager', 'platform_admin'].includes(role)
  const canFinance = ['company_admin', 'finance_manager', 'platform_admin'].includes(role)
  const slips = run.payslips.filter((p) => `${p.employee_name} ${p.employee_code} ${p.department}`.toLowerCase().includes(q.toLowerCase()))

  return (
    <Page>
      <PageHeader title={<span className="flex items-center gap-3">Payroll · {run.period} <Badge status={run.status} /></span>}
        subtitle={run.processed_at ? `Last processed ${fmtDateTime(run.processed_at)}` : 'Not processed yet'}
        back={<Link to="/payroll" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-emerald-700"><ArrowLeft className="w-4 h-4" />All payroll runs</Link>}
        actions={<>
          {['draft', 'pending_approval'].includes(run.status) && canProcess && (
            <Button icon={Cpu} variant={run.status === 'draft' ? 'primary' : 'secondary'} loading={busy === 'process'}
              onClick={() => act('process', () => payrollApi.process(id), 'Payslips calculated.')}>
              {run.status === 'draft' ? 'Process payroll' : 'Reprocess'}
            </Button>)}
          {run.status === 'pending_approval' && run.approval_request_id && (
            <Link to="/approvals"><Button variant="secondary" icon={GitBranch}>Open in Approvals</Button></Link>)}
          {run.status === 'pending_approval' && !run.approval_request_id && canFinance && (
            <Button icon={CheckCircle2} loading={busy === 'approve'} onClick={() => act('approve', () => payrollApi.approve(id), 'Payroll approved.')}>Approve</Button>)}
          {run.status === 'approved' && canFinance && (
            <Button icon={Wallet} loading={busy === 'paid'} onClick={() => act('paid', () => payrollApi.markPaid(id), 'Marked as paid.')}>Mark as paid</Button>)}
          {['draft', 'pending_approval'].includes(run.status) && canProcess && (
            <Button variant="danger" icon={Ban} loading={busy === 'cancel'} onClick={() => confirm('Cancel this payroll run?') && act('cancel', () => payrollApi.cancel(id), 'Payroll run cancelled.')}>Cancel run</Button>)}
        </>} />

      {msg && (
        <div className="mb-5"><Alert tone={msg.tone}>
          {msg.text}
          {msg.list && <details className="mt-1"><summary className="cursor-pointer text-xs">{msg.list.length} employee(s) skipped</summary>
            <ul className="text-xs mt-1 list-disc pl-5">{msg.list.map((s) => <li key={s}>{s}</li>)}</ul></details>}
        </Alert></div>
      )}
      {run.notes && run.status === 'draft' && <div className="mb-5"><Alert tone="amber">{run.notes}</Alert></div>}

      <StatGrid>
        <Stat label="Employees" value={run.total_employees ?? '—'} icon={Users} tone="sky" />
        <Stat label="Gross pay" value={inr(run.total_gross)} icon={IndianRupee} tone="indigo" />
        <Stat label="Deductions" value={inr(run.total_deductions)} icon={Ban} tone="rose" />
        <Stat label="Net pay" value={inr(run.total_net)} icon={Wallet} />
      </StatGrid>

      <Card padded={false} title={`Payslips (${run.payslips.length})`}
        actions={<div className="relative"><Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search…" className="!py-1.5 pl-9 !w-52" /></div>}>
        {!run.payslips.length ? <Empty title="No payslips yet" hint={run.status === 'draft' ? 'Click “Process payroll” to calculate them.' : undefined} /> :
          <Table head={['Employee', 'Department', 'Paid days', 'Earnings', 'Deductions', 'Net pay', '']}>
            {slips.map((p) => (
              <tr key={p.id} className="hover:bg-slate-50/70 cursor-pointer" onClick={() => setSlip(p.id)}>
                <td className={td}><div className="font-semibold text-slate-900">{p.employee_name}</div><div className="text-xs text-slate-400">{p.employee_code}</div></td>
                <td className={td}>{p.department}</td>
                <td className={td}>{p.paid_days < p.working_days
                  ? <span className="text-amber-700 font-medium">{p.paid_days} / {p.working_days}</span> : `${p.paid_days} / ${p.working_days}`}</td>
                <td className={td + ' tabular-nums'}>{inr(p.total_earnings)}</td>
                <td className={td + ' tabular-nums text-rose-600'}>{inr(p.total_deductions)}</td>
                <td className={td + ' tabular-nums font-semibold'}>{inr(p.net_salary)}</td>
                <td className="px-4 py-3 text-emerald-600 text-xs font-semibold">View</td>
              </tr>
            ))}
          </Table>}
      </Card>

      <PayslipModal id={slip} onClose={() => setSlip(null)} />
    </Page>
  )
}

function PayslipModal({ id, onClose }: { id: number | null; onClose: () => void }) {
  const [p, setP] = useState<Payslip | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    if (!id) return
    setP(null); setErr('')
    payrollApi.payslip(id).then(setP).catch((e) => setErr(apiError(e)))
  }, [id])
  const earnings = p?.items.filter((i) => i.type === 'earning') ?? []
  const deductions = p?.items.filter((i) => i.type === 'deduction') ?? []
  return (
    <Modal open={!!id} onClose={onClose} title="Payslip" wide
      footer={<><Button variant="secondary" onClick={onClose}>Close</Button><Button icon={Printer} onClick={() => window.print()} disabled={!p}>Print / save PDF</Button></>}>
      {err && <Alert>{err}</Alert>}
      {!p ? !err && <Loading /> : (
        <div id="payslip-print" className="text-sm">
          <div className="flex justify-between items-start border-b border-slate-200 pb-3 mb-3">
            <div>
              <div className="font-bold text-lg text-slate-900">{p.employee.name}</div>
              <div className="text-slate-500">{p.employee.code} · {p.employee.designation ?? '—'} · {p.employee.department}</div>
            </div>
            <div className="text-right">
              <div className="font-semibold">{p.period}</div>
              <div className="text-slate-500">Paid days {p.paid_days} of {p.working_days}</div>
            </div>
          </div>
          <div className="grid sm:grid-cols-2 gap-6">
            <Lines title="Earnings" items={earnings} total={p.total_earnings} />
            <Lines title="Deductions" items={deductions} total={p.total_deductions} negative />
          </div>
          <div className="mt-4 bg-emerald-50 rounded-xl px-4 py-3 flex justify-between items-center">
            <span className="font-semibold text-emerald-800">Net pay</span>
            <span className="text-xl font-bold text-emerald-700 tabular-nums">{inr(p.net_salary, 2)}</span>
          </div>
        </div>
      )}
    </Modal>
  )
}

function Lines({ title, items, total, negative }: { title: string; items: { name: string; amount: number }[]; total: number; negative?: boolean }) {
  return (
    <div>
      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">{title}</div>
      {items.map((i) => (
        <div key={i.name} className="flex justify-between py-1 border-b border-slate-50">
          <span className="text-slate-600">{i.name}</span><span className="tabular-nums">{inr(i.amount, 2)}</span>
        </div>
      ))}
      <div className={`flex justify-between pt-2 font-semibold ${negative ? 'text-rose-600' : 'text-slate-900'}`}>
        <span>Total</span><span className="tabular-nums">{inr(total, 2)}</span>
      </div>
    </div>
  )
}
