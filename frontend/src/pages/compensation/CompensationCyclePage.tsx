import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCheck, Search, Sparkles } from 'lucide-react'
import { compensationApi, type CompPlan } from '../../api/modules'
import { useAuth } from '../../context/AuthContext'
import {
  Alert, Badge, Button, Card, Empty, ErrorState, Field, Input, Loading, Modal, Page, PageHeader, Progress,
  Select, TextArea, Table, apiError, inr, lakhs, td,
} from '../../components/ui/kit'
import { useLoad } from '../../components/ui/kit'

export default function CompensationCyclePage() {
  const id = Number(useParams().id)
  const { user } = useAuth()
  const { data: c, loading, error, reload } = useLoad(() => compensationApi.cycle(id), [id])
  const [msg, setMsg] = useState<{ tone: 'rose' | 'emerald'; text: string } | null>(null)
  const [busy, setBusy] = useState('')
  const [edit, setEdit] = useState<CompPlan | null>(null)
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')

  if (loading && !c) return <Page><Loading /></Page>
  if (error || !c) return <Page><ErrorState message={error || 'Not found'} onRetry={reload} /></Page>

  const run = async (key: string, fn: () => Promise<unknown>, ok: (r: never) => string) => {
    setBusy(key); setMsg(null)
    try { const r = await fn(); setMsg({ tone: 'emerald', text: ok(r as never) }); reload() }
    catch (e) { setMsg({ tone: 'rose', text: apiError(e) }) } finally { setBusy('') }
  }
  const isAdmin = ['company_admin', 'platform_admin'].includes(user?.role ?? '')
  const b = c.budget
  const rows = c.plans.filter((p) => (!status || p.status === status) &&
    `${p.employee_name} ${p.department}`.toLowerCase().includes(q.toLowerCase()))
  const open = c.status === 'active' || c.status === 'draft'

  return (
    <Page>
      <PageHeader title={<span className="flex items-center gap-3">{c.name} <Badge status={c.status} /></span>}
        subtitle={`${c.plan_count} employees · ${c.approved_count} approved`}
        back={<Link to="/compensation" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-emerald-700"><ArrowLeft className="w-4 h-4" />All cycles</Link>}
        actions={<>
          {open && <Button icon={Sparkles} variant={c.plan_count ? 'secondary' : 'primary'} loading={busy === 'gen'}
            onClick={() => run('gen', () => compensationApi.generate(id), (r: { created: number; without_review_score: number }) =>
              `${r.created} plan(s) created${r.without_review_score ? `, ${r.without_review_score} without a review score (0% recommended)` : ''}.`)}>
            {c.plan_count ? 'Add missing employees' : 'Generate recommendations'}</Button>}
          {c.status === 'active' && isAdmin && <Button icon={CheckCheck} loading={busy === 'apply'}
            onClick={() => confirm('Write all approved increments into employee salaries and close this cycle?') &&
              run('apply', () => compensationApi.apply(id), (r: { applied: number }) => `Salaries updated for ${r.applied} employees. Cycle closed.`)}>
            Apply to salaries</Button>}
        </>} />
      {msg && <div className="mb-5"><Alert tone={msg.tone}>{msg.text}</Alert></div>}

      <Card className="mb-5">
        <div className="grid sm:grid-cols-4 gap-4 mb-4">
          {[['Budget', b.total_budget, 'text-slate-900'], ['Approved', b.approved_cost, 'text-emerald-700'],
            ['Projected (all plans)', b.projected_cost, b.projected_cost > b.total_budget ? 'text-rose-600' : 'text-amber-700'],
            ['Remaining', b.remaining, b.remaining < 0 ? 'text-rose-600' : 'text-slate-900']].map(([label, v, cls]) => (
            <div key={label as string}>
              <div className="text-xs text-slate-400 font-medium">{label}</div>
              <div className={`text-lg font-bold tabular-nums ${cls}`}>{lakhs(v as number)}</div>
            </div>
          ))}
        </div>
        <div className="relative">
          <Progress value={b.projected_utilization_pct ?? 0} tone={(b.projected_utilization_pct ?? 0) > 100 ? 'rose' : 'amber'} />
          <div className="absolute inset-0"><Progress value={b.utilization_pct ?? 0} /></div>
        </div>
        <div className="flex gap-4 text-xs text-slate-500 mt-2">
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />Approved {b.utilization_pct}%</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-amber-500" />Projected {b.projected_utilization_pct}%</span>
        </div>
      </Card>

      <Card padded={false} title="Increment plans" actions={<>
        <Select value={status} onChange={(e) => setStatus(e.target.value)} className="!py-1.5 !w-40">
          <option value="">All statuses</option>
          {['pending', 'manager_review', 'hr_review', 'approved', 'rejected'].map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </Select>
        <div className="relative"><Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search…" className="!py-1.5 pl-9 !w-44" /></div>
      </>}>
        {!c.plans.length ? <Empty title="No plans yet" hint="Click “Generate recommendations” to create a plan per employee from their review scores." /> :
          <Table minWidth={960} head={['Employee', 'Score', 'Current CTC', 'System', 'Manager', 'New CTC', 'Bonus', 'Status', '']}>
            {rows.map((p) => {
              const newCtc = p.final_new_salary ?? p.current_salary * (1 + p.effective_pct / 100)
              return (
                <tr key={p.id} className="hover:bg-slate-50/70">
                  <td className={td}><div className="font-semibold text-slate-900">{p.employee_name}</div><div className="text-xs text-slate-400">{p.department}</div></td>
                  <td className={td + ' tabular-nums'}>{p.performance_score ?? '—'}</td>
                  <td className={td + ' tabular-nums'}>{inr(p.current_salary)}</td>
                  <td className={td + ' tabular-nums text-slate-500'}>{p.system_recommended_pct ?? 0}%</td>
                  <td className={td + ' tabular-nums'}>{p.manager_recommended_pct != null ? <span className="font-semibold text-indigo-700">{p.manager_recommended_pct}%</span> : '—'}</td>
                  <td className={td + ' tabular-nums font-semibold'}>{p.status === 'rejected' ? '—' : inr(newCtc)}</td>
                  <td className={td + ' tabular-nums'}>{p.bonus_amount ? inr(p.bonus_amount) : '—'}</td>
                  <td className={td}><Badge status={p.status} /></td>
                  <td className={td}><button onClick={() => setEdit(p)} className="text-emerald-600 text-xs font-semibold hover:underline">
                    {['pending', 'manager_review'].includes(p.status) && open ? 'Review' : 'View'}</button></td>
                </tr>
              )
            })}
          </Table>}
      </Card>

      <PlanModal plan={edit} editable={open} onClose={() => setEdit(null)} onDone={(text) => { setEdit(null); setMsg({ tone: 'emerald', text }); reload() }} />
    </Page>
  )
}

function PlanModal({ plan, editable, onClose, onDone }: { plan: CompPlan | null; editable: boolean; onClose: () => void; onDone: (msg: string) => void }) {
  const [f, setF] = useState({ pct: '', bonus: '', notes: '', reason: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  useEffect(() => {
    if (plan) {
      setF({ pct: plan.manager_recommended_pct?.toString() ?? '', bonus: plan.bonus_amount?.toString() ?? '', notes: plan.manager_notes ?? '', reason: '' })
      setError('')
    }
  }, [plan])
  if (!plan) return null
  const canEdit = editable && ['pending', 'manager_review'].includes(plan.status)
  const pct = f.pct === '' ? (plan.system_recommended_pct ?? 0) : Number(f.pct)

  const go = async (key: string, fn: () => Promise<unknown>, ok: string) => {
    setBusy(key); setError('')
    try { await fn(); onDone(ok) } catch (e) { setError(apiError(e)) } finally { setBusy('') }
  }
  const saveFirst = () => compensationApi.updatePlan(plan.id, {
    manager_recommended_pct: f.pct === '' ? undefined : Number(f.pct),
    bonus_amount: f.bonus === '' ? undefined : Number(f.bonus), manager_notes: f.notes,
  })

  return (
    <Modal open onClose={onClose} title={<span className="flex items-center gap-3">{plan.employee_name} <Badge status={plan.status} /></span>}
      footer={canEdit ? <>
        <Button variant="danger" loading={busy === 'reject'} onClick={() => go('reject', () => compensationApi.decide(plan.id, false, f.reason), 'Plan rejected.')}>Reject</Button>
        <Button variant="secondary" loading={busy === 'save'} onClick={() => go('save', saveFirst, 'Changes saved.')}>Save</Button>
        <Button variant="secondary" loading={busy === 'submit'} onClick={() => go('submit', async () => { await saveFirst(); await compensationApi.submit(plan.id) }, 'Sent for approval.')}>Send for approval</Button>
        <Button loading={busy === 'approve'} onClick={() => go('approve', async () => { await saveFirst(); await compensationApi.decide(plan.id, true) }, 'Increment approved.')}>Approve</Button>
      </> : <Button variant="secondary" onClick={onClose}>Close</Button>}>
      {error && <Alert>{error}</Alert>}
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div><div className="text-xs text-slate-400">Current CTC</div><div className="font-semibold tabular-nums">{inr(plan.current_salary)}</div></div>
        <div><div className="text-xs text-slate-400">Review score</div><div className="font-semibold">{plan.performance_score ?? 'No review'}</div></div>
        <div><div className="text-xs text-slate-400">System recommends</div><div className="font-semibold">{plan.system_recommended_pct ?? 0}%</div></div>
      </div>
      {plan.status === 'rejected' && <Alert tone="amber">Rejected: {plan.rejection_reason}</Alert>}
      {plan.status === 'approved' && <Alert tone="emerald">Approved {plan.final_increment_pct}% → new CTC {inr(plan.final_new_salary)}</Alert>}
      {canEdit && <>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Manager increment %" hint="Leave empty to use the system recommendation"><Input type="number" value={f.pct} onChange={(e) => setF({ ...f, pct: e.target.value })} /></Field>
          <Field label="One-time bonus (₹)"><Input type="number" value={f.bonus} onChange={(e) => setF({ ...f, bonus: e.target.value })} /></Field>
        </div>
        <div className="bg-slate-50 rounded-xl px-4 py-3 text-sm flex justify-between">
          <span className="text-slate-500">New CTC at {pct}%</span>
          <span className="font-bold tabular-nums text-emerald-700">{inr(plan.current_salary * (1 + pct / 100))}</span>
        </div>
        <Field label="Notes"><TextArea value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
        <Field label="Reason (needed only to reject)"><Input value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} /></Field>
        <p className="text-xs text-slate-400">“Send for approval” routes the plan through the company's increment workflow. HR and admins can also approve directly. Approval is blocked if it would exceed the cycle budget.</p>
      </>}
      {!canEdit && plan.manager_notes && <Field label="Notes"><p className="text-sm text-slate-600">{plan.manager_notes}</p></Field>}
    </Modal>
  )
}
