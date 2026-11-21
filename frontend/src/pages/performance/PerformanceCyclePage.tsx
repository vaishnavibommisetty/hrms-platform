import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Lock, Rocket, Search } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { performanceApi, type Review } from '../../api/modules'
import {
  Alert, Badge, Button, Card, Empty, ErrorState, Field, Input, Loading, Modal, Page, PageHeader, Select,
  TextArea, Table, apiError, fmtDate, td, useLoad,
} from '../../components/ui/kit'

const RATINGS = ['Outstanding', 'Exceeds Expectations', 'Meets Expectations', 'Needs Improvement', 'Unsatisfactory']
const RATING_COLORS = ['#059669', '#10b981', '#38bdf8', '#f59e0b', '#f43f5e']

export default function PerformanceCyclePage() {
  const id = Number(useParams().id)
  const { data: c, loading, error, reload } = useLoad(() => performanceApi.cycle(id), [id])
  const [review, setReview] = useState<number | null>(null)
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [msg, setMsg] = useState<{ tone: 'rose' | 'emerald'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  if (loading && !c) return <Page><Loading /></Page>
  if (error || !c) return <Page><ErrorState message={error || 'Not found'} onRetry={reload} /></Page>

  const dist = RATINGS.map((r) => ({ rating: r.split(' ')[0], full: r, count: c.rating_distribution[r] ?? 0 }))
  const rows = c.reviews.filter((r) => (!status || r.status === status) &&
    `${r.employee_name} ${r.department}`.toLowerCase().includes(q.toLowerCase()))

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true); setMsg(null)
    try { await fn(); setMsg({ tone: 'emerald', text: ok }); reload() } catch (e) { setMsg({ tone: 'rose', text: apiError(e) }) } finally { setBusy(false) }
  }

  return (
    <Page>
      <PageHeader title={<span className="flex items-center gap-3">{c.name} <Badge status={c.status} /></span>}
        subtitle={`${fmtDate(c.start_date)} – ${fmtDate(c.end_date)} · ${c.completed_reviews} of ${c.total_reviews} reviews completed`}
        back={<Link to="/performance" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-emerald-700"><ArrowLeft className="w-4 h-4" />All cycles</Link>}
        actions={<>
          {c.status !== 'completed' && <Button icon={Rocket} variant={c.status === 'draft' ? 'primary' : 'secondary'} loading={busy}
            onClick={() => run(() => performanceApi.launch(id), 'Reviews created for all active employees.')}>{c.status === 'draft' ? 'Launch cycle' : 'Add new joiners'}</Button>}
          {c.status !== 'completed' && c.status !== 'draft' && <Button icon={Lock} variant="secondary" loading={busy}
            onClick={() => run(() => performanceApi.close(id), 'Cycle closed.')}>Close cycle</Button>}
        </>} />
      {msg && <div className="mb-5"><Alert tone={msg.tone}>{msg.text}</Alert></div>}

      <div className="grid lg:grid-cols-3 gap-5 mb-5">
        <Card title="KPIs">
          <ul className="space-y-3">
            {c.kpis.map((k) => (
              <li key={k.id}>
                <div className="flex justify-between text-sm"><span className="font-medium text-slate-800">{k.name}</span><span className="text-slate-500 tabular-nums">{k.weight_pct}%</span></div>
                {k.description && <div className="text-xs text-slate-400">{k.description}</div>}
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Rating distribution" className="lg:col-span-2">
          {c.completed_reviews === 0 ? <Empty title="No completed reviews yet" /> :
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={dist} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="rating" tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v: number) => [v, 'Employees']} labelFormatter={(_, p) => p?.[0]?.payload?.full ?? ''} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>{dist.map((_, i) => <Cell key={i} fill={RATING_COLORS[i]} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>}
        </Card>
      </div>

      <Card padded={false} title="Reviews" actions={<>
        <Select value={status} onChange={(e) => setStatus(e.target.value)} className="!py-1.5 !w-44">
          <option value="">All statuses</option><option value="self_review">Self review</option>
          <option value="manager_review">Manager review</option><option value="completed">Completed</option>
        </Select>
        <div className="relative"><Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search…" className="!py-1.5 pl-9 !w-44" /></div>
      </>}>
        {!c.reviews.length ? <Empty title="No reviews yet" hint="Launch the cycle to create a review for every active employee." /> :
          <Table head={['Employee', 'Department', 'Status', 'Self score', 'Manager score', 'Final', 'Rating']}>
            {rows.map((r) => (
              <tr key={r.id} className="hover:bg-slate-50/70 cursor-pointer" onClick={() => setReview(r.id)}>
                <td className={td}><div className="font-semibold text-slate-900">{r.employee_name}</div><div className="text-xs text-slate-400">{r.employee_code}</div></td>
                <td className={td}>{r.department}</td>
                <td className={td}><Badge status={r.status} /></td>
                <td className={td + ' tabular-nums'}>{r.self_overall_score ?? '—'}</td>
                <td className={td + ' tabular-nums'}>{r.manager_overall_score ?? '—'}</td>
                <td className={td + ' tabular-nums font-semibold'}>{r.final_score ?? '—'}</td>
                <td className={td}>{r.rating ?? <span className="text-slate-300">—</span>}</td>
              </tr>
            ))}
          </Table>}
      </Card>

      <ReviewModal id={review} onClose={() => setReview(null)} onSaved={reload} />
    </Page>
  )
}

function ReviewModal({ id, onClose, onSaved }: { id: number | null; onClose: () => void; onSaved: () => void }) {
  const [r, setR] = useState<Review | null>(null)
  const [scores, setScores] = useState<Record<number, { self: string; mgr: string }>>({})
  const [comments, setComments] = useState({ self: '', mgr: '' })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState('')

  const hydrate = (x: Review) => {
    setR(x)
    setScores(Object.fromEntries(x.kpis.map((k) => [k.kpi_id, { self: k.self_score?.toString() ?? '', mgr: k.manager_score?.toString() ?? '' }])))
    setComments({ self: x.self_comments ?? '', mgr: x.manager_comments ?? '' })
  }
  useEffect(() => {
    if (!id) return
    setR(null); setError('')
    performanceApi.review(id).then(hydrate).catch((e) => setError(apiError(e)))
  }, [id])

  const save = async (submit?: 'self' | 'manager') => {
    if (!r) return
    setSaving(submit ?? 'save'); setError('')
    try {
      const updated = await performanceApi.updateReview(r.id, {
        scores: r.kpis.map((k) => ({
          kpi_id: k.kpi_id,
          self_score: scores[k.kpi_id]?.self === '' ? null : Number(scores[k.kpi_id]?.self),
          manager_score: scores[k.kpi_id]?.mgr === '' ? null : Number(scores[k.kpi_id]?.mgr),
        })),
        self_comments: comments.self, manager_comments: comments.mgr, submit,
      })
      hydrate(updated); onSaved()
      if (submit) onClose()
    } catch (e) { setError(apiError(e)) } finally { setSaving('') }
  }

  const done = r?.status === 'completed'
  const weighted = (key: 'self' | 'mgr') => {
    if (!r) return null
    const vals = r.kpis.map((k) => scores[k.kpi_id]?.[key])
    if (vals.some((v) => v === '' || v === undefined)) return null
    return (r.kpis.reduce((s, k) => s + Number(scores[k.kpi_id][key]) * k.weight_pct, 0) / 100).toFixed(1)
  }

  return (
    <Modal open={!!id} onClose={onClose} wide title={r ? <span className="flex items-center gap-3">{r.employee_name} <Badge status={r.status} /></span> : 'Review'}
      footer={r && !done ? <>
        <Button variant="secondary" onClick={() => save()} loading={saving === 'save'}>Save draft</Button>
        {r.status === 'self_review' && <Button variant="secondary" onClick={() => save('self')} loading={saving === 'self'}>Submit self review</Button>}
        <Button onClick={() => save('manager')} loading={saving === 'manager'}>Complete review</Button>
      </> : <Button variant="secondary" onClick={onClose}>Close</Button>}>
      {error && <Alert>{error}</Alert>}
      {!r ? !error && <Loading /> : <>
        {done && <Alert tone="emerald">Final score <b>{r.final_score}</b> · {r.rating}</Alert>}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-xs text-slate-400 uppercase tracking-wider text-left">
              <th className="py-2">KPI</th><th className="py-2 w-16">Weight</th><th className="py-2 w-28">Self (0–100)</th><th className="py-2 w-28">Manager (0–100)</th></tr></thead>
            <tbody>
              {r.kpis.map((k) => (
                <tr key={k.kpi_id} className="border-t border-slate-100">
                  <td className="py-2 pr-2"><div className="font-medium text-slate-800">{k.name}</div><div className="text-xs text-slate-400">{k.description}</div></td>
                  <td className="py-2 text-slate-500">{k.weight_pct}%</td>
                  {(['self', 'mgr'] as const).map((key) => (
                    <td key={key} className="py-2 pr-2">
                      <Input type="number" min={0} max={100} disabled={done} value={scores[k.kpi_id]?.[key] ?? ''}
                        onChange={(e) => setScores({ ...scores, [k.kpi_id]: { ...scores[k.kpi_id], [key]: e.target.value } })} className="!py-1.5" />
                    </td>
                  ))}
                </tr>
              ))}
              <tr className="border-t border-slate-200 font-semibold">
                <td className="py-2" colSpan={2}>Weighted score</td><td className="py-2">{weighted('self') ?? '—'}</td><td className="py-2">{weighted('mgr') ?? '—'}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Employee comments"><TextArea disabled={done} value={comments.self} onChange={(e) => setComments({ ...comments, self: e.target.value })} /></Field>
          <Field label="Manager comments"><TextArea disabled={done} value={comments.mgr} onChange={(e) => setComments({ ...comments, mgr: e.target.value })} /></Field>
        </div>
        {!done && <p className="text-xs text-slate-400">“Complete review” needs a manager score for every KPI. The final score is the weighted manager score.</p>}
      </>}
    </Modal>
  )
}
