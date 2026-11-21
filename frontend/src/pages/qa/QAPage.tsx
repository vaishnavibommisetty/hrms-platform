import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bug, CheckCircle2, ChevronRight, FlaskConical, Gauge, Plus } from 'lucide-react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { qaApi, type Defect } from '../../api/modules'
import {
  Alert, Badge, Button, Card, Empty, ErrorState, Field, Input, Loading, Modal, Page, PageHeader,
  Select, Stat, StatGrid, Table, Tabs, TextArea, apiError, fmtDate, td, titleCase, useLoad,
} from '../../components/ui/kit'

const STATUS_COLORS: Record<string, string> = { passed: '#10b981', failed: '#f43f5e', blocked: '#f97316', skipped: '#94a3b8', not_run: '#e2e8f0' }

export default function QAPage() {
  const [tab, setTab] = useState<'plans' | 'defects'>('plans')
  const summary = useLoad(qaApi.summary)
  const plans = useLoad(qaApi.plans)
  const [defFilter, setDefFilter] = useState('open')
  const defects = useLoad(() => qaApi.defects(defFilter), [defFilter])
  const [newPlan, setNewPlan] = useState(false)
  const [newDefect, setNewDefect] = useState(false)
  const s = summary.data
  const pie = s ? Object.entries(s.status_counts).filter(([, v]) => v).map(([k, v]) => ({ name: titleCase(k), key: k, value: v })) : []

  return (
    <Page>
      <PageHeader title="QA Management" subtitle="Test plans, execution results and the defect life-cycle"
        actions={<>
          <Button variant="secondary" icon={Bug} onClick={() => setNewDefect(true)}>Log defect</Button>
          <Button icon={Plus} onClick={() => setNewPlan(true)}>New test plan</Button>
        </>} />

      <StatGrid>
        <Stat label="Test cases" value={s?.test_cases ?? '—'} icon={FlaskConical} tone="indigo" hint={s ? `${s.plans} plans` : undefined} />
        <Stat label="Pass rate (latest runs)" value={s?.pass_rate != null ? `${s.pass_rate}%` : '—'} icon={CheckCircle2} />
        <Stat label="Execution coverage" value={s?.execution_coverage != null ? `${s.execution_coverage}%` : '—'} icon={Gauge} tone="sky" />
        <Stat label="Open defects" value={s?.defects_open ?? '—'} icon={Bug} tone="rose" hint={s?.open_by_severity.critical ? `${s.open_by_severity.critical} critical` : undefined} />
      </StatGrid>

      <Tabs value={tab} onChange={setTab} tabs={[
        { id: 'plans', label: 'Test plans', count: plans.data?.length },
        { id: 'defects', label: 'Defects', count: s?.defects_total },
      ]} />

      {tab === 'plans' && (
        <div className="grid lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 space-y-3">
            {plans.loading ? <Loading /> : plans.error ? <ErrorState message={plans.error} onRetry={plans.reload} /> :
              !plans.data?.length ? <Card><Empty title="No test plans yet" /></Card> :
                plans.data.map((p) => {
                  const executed = p.case_count - (p.status_counts.not_run ?? 0)
                  return (
                    <Link key={p.id} to={`/qa/plans/${p.id}`} className="block group">
                      <Card className="group-hover:border-emerald-200 group-hover:shadow-md transition-all">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <div className="font-semibold text-slate-900">{p.name}</div>
                            <div className="text-xs text-slate-400">{p.module} · v{p.version} · {p.case_count} cases</div>
                          </div>
                          <div className="flex items-center gap-2">
                            {p.pass_rate != null && <span className={`text-sm font-bold ${p.pass_rate >= 80 ? 'text-emerald-600' : 'text-amber-600'}`}>{p.pass_rate}%</span>}
                            <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-emerald-500" />
                          </div>
                        </div>
                        <div className="flex h-2 rounded-full overflow-hidden bg-slate-100">
                          {['passed', 'failed', 'blocked', 'skipped'].map((k) => p.status_counts[k] ? (
                            <div key={k} style={{ width: `${p.status_counts[k] / p.case_count * 100}%`, background: STATUS_COLORS[k] }} />) : null)}
                        </div>
                        <div className="flex gap-3 text-xs text-slate-500 mt-2">
                          {['passed', 'failed', 'blocked', 'not_run'].map((k) => <span key={k}>{titleCase(k)} {p.status_counts[k] ?? 0}</span>)}
                          <span className="ml-auto">{executed}/{p.case_count} executed</span>
                        </div>
                      </Card>
                    </Link>
                  )
                })}
          </div>
          <Card title="Latest result of every case">
            {!pie.length ? <Empty title="No cases yet" /> : <>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart><Pie data={pie} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
                  {pie.map((d) => <Cell key={d.key} fill={STATUS_COLORS[d.key]} />)}</Pie><Tooltip /></PieChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-1.5 text-xs">
                {pie.map((d) => <div key={d.key} className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm" style={{ background: STATUS_COLORS[d.key] }} />{d.name}: <b>{d.value}</b></div>)}
              </div>
              {s && <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500 space-y-1">
                <div className="font-semibold text-slate-600">Cases by type</div>
                {Object.entries(s.cases_by_type).map(([k, v]) => <div key={k} className="flex justify-between"><span>{titleCase(k)}</span><span>{v}</span></div>)}
              </div>}
            </>}
          </Card>
        </div>
      )}

      {tab === 'defects' && (
        <Card padded={false} title="Defects" actions={<Select value={defFilter} onChange={(e) => setDefFilter(e.target.value)} className="!py-1.5 !w-40">
          <option value="open">Open</option><option value="">All</option>
          {['fixed', 'verified', 'closed', 'reopened', 'wont_fix'].map((x) => <option key={x} value={x}>{titleCase(x)}</option>)}</Select>}>
          {defects.loading ? <Loading /> : !defects.data?.length ? <Empty title="No defects here" /> :
            <Table minWidth={900} head={['ID', 'Title', 'Module', 'Severity', 'Priority', 'Status', 'Logged', 'Move to']}>
              {defects.data.map((d) => <DefectRow key={d.id} d={d} onChanged={() => { defects.reload(); summary.reload() }} />)}
            </Table>}
        </Card>
      )}

      <PlanModal open={newPlan} onClose={() => setNewPlan(false)} onDone={() => { setNewPlan(false); plans.reload(); summary.reload() }} />
      <DefectModal open={newDefect} onClose={() => setNewDefect(false)} onDone={() => { setNewDefect(false); setTab('defects'); defects.reload(); summary.reload() }} />
    </Page>
  )
}

export function DefectRow({ d, onChanged }: { d: Defect; onChanged: () => void }) {
  const [error, setError] = useState('')
  const move = async (status: string) => {
    if (!status) return
    setError('')
    try { await qaApi.moveDefect(d.id, status); onChanged() } catch (e) { setError(apiError(e)) }
  }
  return (
    <tr className="hover:bg-slate-50/70 align-top">
      <td className={td}><code className="text-xs font-semibold text-slate-600">{d.defect_id}</code></td>
      <td className={td}><div className="font-medium text-slate-900">{d.title}</div>
        {d.test_case_ref && <div className="text-xs text-slate-400">From {d.test_case_ref}</div>}
        {error && <div className="text-xs text-rose-600 mt-1">{error}</div>}</td>
      <td className={td}>{d.module ?? '—'}</td>
      <td className={td}><Badge status={d.severity} /></td>
      <td className={td}><span className="text-xs font-semibold text-slate-500 uppercase">{d.priority}</span></td>
      <td className={td}><Badge status={d.status} /></td>
      <td className={td + ' text-slate-400 whitespace-nowrap'}>{fmtDate(d.created_at)}</td>
      <td className={td}>
        <Select value="" onChange={(e) => move(e.target.value)} className="!py-1.5 !w-36" disabled={!d.next_statuses.length}>
          <option value="">Change…</option>
          {d.next_statuses.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
        </Select>
      </td>
    </tr>
  )
}

function PlanModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const [f, setF] = useState({ name: '', module: '', description: '' })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (open) { setF({ name: '', module: '', description: '' }); setError('') } }, [open])
  const save = async () => {
    setSaving(true); setError('')
    try { await qaApi.createPlan(f); onDone() } catch (e) { setError(apiError(e)) } finally { setSaving(false) }
  }
  return (
    <Modal open={open} onClose={onClose} title="New test plan"
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={save} loading={saving}>Create</Button></>}>
      {error && <Alert>{error}</Alert>}
      <Field label="Plan name"><Input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Compensation regression" /></Field>
      <Field label="Module under test"><Input value={f.module} onChange={(e) => setF({ ...f, module: e.target.value })} placeholder="Compensation" /></Field>
      <Field label="Scope"><TextArea value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
    </Modal>
  )
}

export function DefectModal({ open, onClose, onDone, testCaseId, module }: {
  open: boolean; onClose: () => void; onDone: () => void; testCaseId?: number; module?: string
}) {
  const blank = { title: '', description: '', steps_to_reproduce: '', expected_behaviour: '', actual_behaviour: '', severity: 'medium', priority: 'p3', module: module ?? '' }
  const [f, setF] = useState(blank)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (open) { setF(blank); setError('') } }, [open])
  const save = async () => {
    setSaving(true); setError('')
    try { await qaApi.createDefect({ ...f, test_case_id: testCaseId ?? null }); onDone() } catch (e) { setError(apiError(e)) } finally { setSaving(false) }
  }
  return (
    <Modal open={open} onClose={onClose} title="Log a defect" wide
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={save} loading={saving}>Log defect</Button></>}>
      {error && <Alert>{error}</Alert>}
      <Field label="Title"><Input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field>
      <div className="grid sm:grid-cols-3 gap-4">
        <Field label="Severity"><Select value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value })}>
          {['critical', 'high', 'medium', 'low'].map((x) => <option key={x} value={x}>{titleCase(x)}</option>)}</Select></Field>
        <Field label="Priority"><Select value={f.priority} onChange={(e) => setF({ ...f, priority: e.target.value })}>
          {['p1', 'p2', 'p3', 'p4'].map((x) => <option key={x} value={x}>{x.toUpperCase()}</option>)}</Select></Field>
        <Field label="Module"><Input value={f.module} onChange={(e) => setF({ ...f, module: e.target.value })} /></Field>
      </div>
      <Field label="Description"><TextArea value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
      <Field label="Steps to reproduce"><TextArea value={f.steps_to_reproduce} onChange={(e) => setF({ ...f, steps_to_reproduce: e.target.value })} /></Field>
      <div className="grid sm:grid-cols-2 gap-4">
        <Field label="Expected"><TextArea rows={2} value={f.expected_behaviour} onChange={(e) => setF({ ...f, expected_behaviour: e.target.value })} /></Field>
        <Field label="Actual"><TextArea rows={2} value={f.actual_behaviour} onChange={(e) => setF({ ...f, actual_behaviour: e.target.value })} /></Field>
      </div>
    </Modal>
  )
}

