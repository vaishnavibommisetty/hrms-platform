import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, Percent, PiggyBank, Plus, Scale } from 'lucide-react'
import { compensationApi } from '../../api/modules'
import {
  Alert, Badge, Button, Card, Empty, ErrorState, Field, Input, Loading, Modal, Page, PageHeader, Progress,
  Stat, StatGrid, Table, apiError, lakhs, td, useLoad,
} from '../../components/ui/kit'

export default function CompensationPage() {
  const cycles = useLoad(compensationApi.cycles)
  const rules = useLoad(compensationApi.rules)
  const [newCycle, setNewCycle] = useState(false)
  const [newRule, setNewRule] = useState(false)
  const active = cycles.data?.find((c) => c.status === 'active')

  return (
    <Page>
      <PageHeader title="Compensation" subtitle="Annual increment planning driven by performance, within budget"
        actions={<Button icon={Plus} onClick={() => setNewCycle(true)}>New increment cycle</Button>} />

      <StatGrid>
        <Stat label="Active cycle budget" value={lakhs(active?.total_budget)} icon={PiggyBank} hint={active?.name} />
        <Stat label="Budget used (approved)" value={active?.budget.utilization_pct != null ? `${active.budget.utilization_pct}%` : '—'} icon={Percent} tone="amber" />
        <Stat label="Plans approved" value={active ? `${active.approved_count}/${active.plan_count}` : '—'} icon={Scale} tone="sky" />
        <Stat label="Increment rules" value={rules.data?.length ?? '—'} icon={Percent} tone="indigo" />
      </StatGrid>

      <div className="grid lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-4">
          {cycles.loading ? <Loading /> : cycles.error ? <ErrorState message={cycles.error} onRetry={cycles.reload} /> :
            !cycles.data?.length ? <Card><Empty title="No increment cycles yet" /></Card> :
              cycles.data.map((c) => {
                const used = c.budget.utilization_pct ?? 0
                const projected = c.budget.projected_utilization_pct ?? 0
                return (
                  <Link key={c.id} to={`/compensation/${c.id}`} className="block group">
                    <Card className="group-hover:border-emerald-200 group-hover:shadow-md transition-all">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <div className="font-semibold text-slate-900">{c.name}</div>
                          <div className="text-xs text-slate-400">{c.plan_count} employees · {c.approved_count} approved</div>
                        </div>
                        <div className="flex items-center gap-2"><Badge status={c.status} /><ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-emerald-500" /></div>
                      </div>
                      <div className="flex justify-between text-xs text-slate-500 mb-1.5">
                        <span>Approved {lakhs(c.budget.approved_cost)} of {lakhs(c.budget.total_budget)}</span>
                        <span className={projected > 100 ? 'text-rose-600 font-semibold' : ''}>Projected {projected}%</span>
                      </div>
                      <Progress value={used} tone={projected > 100 ? 'rose' : used > 80 ? 'amber' : 'emerald'} />
                    </Card>
                  </Link>
                )
              })}
        </div>

        <Card padded={false} title="Increment rules" actions={<Button variant="secondary" icon={Plus} onClick={() => setNewRule(true)} className="!py-1.5">Add</Button>}>
          {rules.loading ? <Loading /> : !rules.data?.length ? <Empty title="No rules" /> :
            <Table head={['Rating', 'Score', 'Raise']}>
              {rules.data.map((r) => (
                <tr key={r.id}>
                  <td className={td + ' font-medium'}>{r.name}</td>
                  <td className={td + ' tabular-nums text-slate-500'}>{r.min_score}–{r.max_score}</td>
                  <td className={td + ' tabular-nums font-semibold text-emerald-700'}>{r.recommended_increment_pct}%</td>
                </tr>
              ))}
            </Table>}
          <p className="text-xs text-slate-400 px-4 py-3 border-t border-slate-100">Each employee's latest review score picks the rule that sets their recommended raise.</p>
        </Card>
      </div>

      <CycleModal open={newCycle} onClose={() => setNewCycle(false)} onDone={() => { setNewCycle(false); cycles.reload() }} />
      <RuleModal open={newRule} onClose={() => setNewRule(false)} onDone={() => { setNewRule(false); rules.reload() }} />
    </Page>
  )
}

function CycleModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const y = new Date().getFullYear()
  const [f, setF] = useState({ name: '', budget: '', start: `${y + 1}-04-01`, end: `${y + 2}-03-31` })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (open) { setF({ name: `FY ${y + 1}-${String(y + 2).slice(-2)} Increments`, budget: '3000000', start: `${y + 1}-04-01`, end: `${y + 2}-03-31` }); setError('') } }, [open, y])
  const save = async () => {
    setSaving(true); setError('')
    try {
      await compensationApi.createCycle({ name: f.name, year: Number(f.start.slice(0, 4)), total_budget: Number(f.budget),
        start_date: `${f.start}T00:00:00`, end_date: `${f.end}T00:00:00` })
      onDone()
    } catch (e) { setError(apiError(e)) } finally { setSaving(false) }
  }
  return (
    <Modal open={open} onClose={onClose} title="New increment cycle"
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={save} loading={saving}>Create</Button></>}>
      {error && <Alert>{error}</Alert>}
      <Field label="Name"><Input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
      <Field label="Total budget (₹ per year)" hint={Number(f.budget) ? lakhs(Number(f.budget)) : undefined}>
        <Input type="number" value={f.budget} onChange={(e) => setF({ ...f, budget: e.target.value })} /></Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Starts"><Input type="date" value={f.start} onChange={(e) => setF({ ...f, start: e.target.value })} /></Field>
        <Field label="Ends"><Input type="date" value={f.end} onChange={(e) => setF({ ...f, end: e.target.value })} /></Field>
      </div>
    </Modal>
  )
}

function RuleModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const [f, setF] = useState({ name: '', min: '', max: '', pct: '' })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (open) { setF({ name: '', min: '', max: '', pct: '' }); setError('') } }, [open])
  const save = async () => {
    setSaving(true); setError('')
    try {
      await compensationApi.createRule({ name: f.name, min_score: Number(f.min), max_score: Number(f.max), recommended_increment_pct: Number(f.pct) })
      onDone()
    } catch (e) { setError(apiError(e)) } finally { setSaving(false) }
  }
  return (
    <Modal open={open} onClose={onClose} title="Add increment rule"
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={save} loading={saving}>Add rule</Button></>}>
      {error && <Alert>{error}</Alert>}
      <Field label="Rating name"><Input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="e.g. Star performer" /></Field>
      <div className="grid grid-cols-3 gap-4">
        <Field label="Min score"><Input type="number" value={f.min} onChange={(e) => setF({ ...f, min: e.target.value })} /></Field>
        <Field label="Max score"><Input type="number" value={f.max} onChange={(e) => setF({ ...f, max: e.target.value })} /></Field>
        <Field label="Raise %"><Input type="number" value={f.pct} onChange={(e) => setF({ ...f, pct: e.target.value })} /></Field>
      </div>
      <p className="text-xs text-slate-400">Score ranges cannot overlap with existing rules.</p>
    </Modal>
  )
}
