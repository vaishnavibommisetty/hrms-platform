import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Award, ChevronRight, ClipboardList, Plus, Target, Trash2, TrendingUp } from 'lucide-react'
import { performanceApi } from '../../api/modules'
import {
  Alert, Badge, Button, Card, Empty, ErrorState, Field, Input, Loading, Modal, Page, PageHeader, Progress,
  Stat, StatGrid, apiError, fmtDate, useLoad,
} from '../../components/ui/kit'

export default function PerformancePage() {
  const { data, loading, error, reload } = useLoad(performanceApi.cycles)
  const [creating, setCreating] = useState(false)
  const active = data?.find((c) => c.status !== 'completed' && c.status !== 'draft')
  const lastClosed = data?.find((c) => c.status === 'completed')

  return (
    <Page>
      <PageHeader title="Performance" subtitle="Review cycles, weighted KPIs and ratings"
        actions={<Button icon={Plus} onClick={() => setCreating(true)}>New review cycle</Button>} />

      <StatGrid>
        <Stat label="Review cycles" value={data?.length ?? '—'} icon={ClipboardList} />
        <Stat label="Active cycle" value={active ? `${active.completed_reviews}/${active.total_reviews}` : '—'} icon={Target} tone="sky" hint={active ? `${active.name} · reviews done` : 'None running'} />
        <Stat label="Last cycle average" value={lastClosed?.average_score ?? '—'} icon={TrendingUp} tone="indigo" hint={lastClosed?.name} />
        <Stat label="Reviews completed" value={data?.reduce((s, c) => s + c.completed_reviews, 0) ?? '—'} icon={Award} tone="amber" />
      </StatGrid>

      {loading ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> :
        !data?.length ? <Card><Empty title="No review cycles yet" action={<Button icon={Plus} onClick={() => setCreating(true)}>Create the first one</Button>} /></Card> :
          <div className="grid md:grid-cols-2 gap-4">
            {data.map((c) => {
              const pct = c.total_reviews ? Math.round(c.completed_reviews / c.total_reviews * 100) : 0
              return (
                <Link key={c.id} to={`/performance/${c.id}`} className="block group">
                  <Card className="group-hover:border-emerald-200 group-hover:shadow-md transition-all">
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div>
                        <div className="font-semibold text-slate-900">{c.name}</div>
                        <div className="text-xs text-slate-400">{fmtDate(c.start_date)} – {fmtDate(c.end_date)} · {c.kpi_count} KPIs</div>
                      </div>
                      <div className="flex items-center gap-2"><Badge status={c.status} /><ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-emerald-500" /></div>
                    </div>
                    <div className="flex justify-between text-xs text-slate-500 mb-1.5">
                      <span>{c.completed_reviews} of {c.total_reviews} reviews completed</span>
                      <span>{c.average_score !== null ? `Avg score ${c.average_score}` : ''}</span>
                    </div>
                    <Progress value={pct} />
                  </Card>
                </Link>
              )
            })}
          </div>}

      <CycleModal open={creating} onClose={() => setCreating(false)} onDone={() => { setCreating(false); reload() }} />
    </Page>
  )
}

const DEFAULT_KPIS = [
  { name: 'Delivery & quality', weight_pct: '40' }, { name: 'Ownership', weight_pct: '25' },
  { name: 'Collaboration', weight_pct: '20' }, { name: 'Learning & growth', weight_pct: '15' },
]

function CycleModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const y = new Date().getFullYear()
  const [f, setF] = useState({ name: '', start: `${y}-10-01`, end: `${y + 1}-03-31` })
  const [kpis, setKpis] = useState(DEFAULT_KPIS)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (open) { setF({ name: `H2 Review ${y}`, start: `${y}-10-01`, end: `${y + 1}-03-31` }); setKpis(DEFAULT_KPIS); setError('') } }, [open, y])
  const total = kpis.reduce((s, k) => s + Number(k.weight_pct || 0), 0)
  const save = async () => {
    setSaving(true); setError('')
    try {
      await performanceApi.create({
        name: f.name, year: Number(f.start.slice(0, 4)), start_date: `${f.start}T00:00:00`, end_date: `${f.end}T00:00:00`,
        kpis: kpis.filter((k) => k.name.trim()).map((k) => ({ name: k.name, weight_pct: Number(k.weight_pct) })),
      })
      onDone()
    } catch (e) { setError(apiError(e)) } finally { setSaving(false) }
  }
  return (
    <Modal open={open} onClose={onClose} title="New review cycle" wide
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={save} loading={saving}>Create cycle</Button></>}>
      {error && <Alert>{error}</Alert>}
      <div className="grid sm:grid-cols-3 gap-4">
        <Field label="Cycle name"><Input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Starts"><Input type="date" value={f.start} onChange={(e) => setF({ ...f, start: e.target.value })} /></Field>
        <Field label="Ends"><Input type="date" value={f.end} onChange={(e) => setF({ ...f, end: e.target.value })} /></Field>
      </div>
      <div>
        <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1.5">
          <span>KPIs and weights</span>
          <span className={total === 100 ? 'text-emerald-600' : 'text-rose-600'}>Total {total}% {total === 100 ? '✓' : '(must be 100%)'}</span>
        </div>
        <div className="space-y-2">
          {kpis.map((k, i) => (
            <div key={i} className="flex gap-2">
              <Input value={k.name} onChange={(e) => setKpis(kpis.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} placeholder="KPI name" />
              <Input type="number" className="!w-28" value={k.weight_pct} onChange={(e) => setKpis(kpis.map((x, j) => j === i ? { ...x, weight_pct: e.target.value } : x))} />
              <button onClick={() => setKpis(kpis.filter((_, j) => j !== i))} className="p-2 text-slate-400 hover:text-rose-500"><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
        <Button variant="ghost" icon={Plus} className="mt-2" onClick={() => setKpis([...kpis, { name: '', weight_pct: '' }])}>Add KPI</Button>
      </div>
    </Modal>
  )
}
