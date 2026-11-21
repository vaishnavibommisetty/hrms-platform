import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Bug, Play, Plus } from 'lucide-react'
import { qaApi } from '../../api/modules'
import {
  Alert, Badge, Button, Card, Empty, ErrorState, Field, Input, Loading, Modal, Page, PageHeader, Select,
  Table, TextArea, apiError, fmtDateTime, td, titleCase, useLoad,
} from '../../components/ui/kit'
import { DefectModal } from './QAPage'

export default function TestPlanPage() {
  const id = Number(useParams().id)
  const { data: plan, loading, error, reload } = useLoad(() => qaApi.plan(id), [id])
  const [newCase, setNewCase] = useState(false)
  const [open, setOpen] = useState<number | null>(null)

  if (loading && !plan) return <Page><Loading /></Page>
  if (error || !plan) return <Page><ErrorState message={error || 'Not found'} onRetry={reload} /></Page>

  return (
    <Page>
      <PageHeader title={plan.name} subtitle={`${plan.module} · v${plan.version}${plan.pass_rate != null ? ` · ${plan.pass_rate}% pass rate` : ''}`}
        back={<Link to="/qa" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-emerald-700"><ArrowLeft className="w-4 h-4" />QA Management</Link>}
        actions={<Button icon={Plus} onClick={() => setNewCase(true)}>Add test case</Button>} />
      {plan.description && <p className="text-sm text-slate-500 -mt-3 mb-5">{plan.description}</p>}

      <Card padded={false}>
        {!plan.cases.length ? <Empty title="No test cases yet" /> :
          <Table minWidth={820} head={['ID', 'Title', 'Type', 'Priority', 'Last result', 'Runs', '']}>
            {plan.cases.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50/70 cursor-pointer" onClick={() => setOpen(c.id)}>
                <td className={td}><code className="text-xs font-semibold text-slate-600">{c.case_id}</code></td>
                <td className={td + ' font-medium text-slate-900'}>{c.title}</td>
                <td className={td}><Badge status={c.test_type === 'security' ? 'manager_review' : 'draft'} label={titleCase(c.test_type)} /></td>
                <td className={td + ' capitalize'}>{c.priority}</td>
                <td className={td}><Badge status={c.last_status} /></td>
                <td className={td}>{c.execution_count}</td>
                <td className="px-4 py-3 text-emerald-600 text-xs font-semibold">Open</td>
              </tr>
            ))}
          </Table>}
      </Card>

      <CaseModal open={newCase} planId={id} onClose={() => setNewCase(false)} onDone={() => { setNewCase(false); reload() }} />
      <CaseDetail id={open} onClose={() => setOpen(null)} onChanged={reload} />
    </Page>
  )
}

function CaseModal({ open, planId, onClose, onDone }: { open: boolean; planId: number; onClose: () => void; onDone: () => void }) {
  const blank = { title: '', test_type: 'positive', priority: 'medium', preconditions: '', test_steps: '', expected_result: '' }
  const [f, setF] = useState(blank)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (open) { setF(blank); setError('') } }, [open])
  const save = async () => {
    setSaving(true); setError('')
    try { await qaApi.createCase(planId, f); onDone() } catch (e) { setError(apiError(e)) } finally { setSaving(false) }
  }
  return (
    <Modal open={open} onClose={onClose} title="New test case" wide
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={save} loading={saving}>Add case</Button></>}>
      {error && <Alert>{error}</Alert>}
      <Field label="Title"><Input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="What is being verified" /></Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Type"><Select value={f.test_type} onChange={(e) => setF({ ...f, test_type: e.target.value })}>
          {['positive', 'negative', 'boundary', 'security', 'regression'].map((t) => <option key={t} value={t}>{titleCase(t)}</option>)}</Select></Field>
        <Field label="Priority"><Select value={f.priority} onChange={(e) => setF({ ...f, priority: e.target.value })}>
          {['critical', 'high', 'medium', 'low'].map((t) => <option key={t} value={t}>{titleCase(t)}</option>)}</Select></Field>
      </div>
      <Field label="Preconditions"><Input value={f.preconditions} onChange={(e) => setF({ ...f, preconditions: e.target.value })} /></Field>
      <Field label="Steps"><TextArea rows={4} value={f.test_steps} onChange={(e) => setF({ ...f, test_steps: e.target.value })} placeholder={'1. …\n2. …'} /></Field>
      <Field label="Expected result"><TextArea rows={2} value={f.expected_result} onChange={(e) => setF({ ...f, expected_result: e.target.value })} /></Field>
    </Modal>
  )
}

type CaseFull = Awaited<ReturnType<typeof qaApi.testCase>>

function CaseDetail({ id, onClose, onChanged }: { id: number | null; onClose: () => void; onChanged: () => void }) {
  const [c, setC] = useState<CaseFull | null>(null)
  const [run, setRun] = useState({ status: 'passed', actual_result: '', build_version: '1.2.0' })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [logBug, setLogBug] = useState(false)
  const load = (cid: number) => qaApi.testCase(cid).then(setC).catch((e) => setError(apiError(e)))
  useEffect(() => { if (id) { setC(null); setError(''); setRun({ status: 'passed', actual_result: '', build_version: '1.2.0' }); load(id) } }, [id])

  const execute = async () => {
    if (!c) return
    setSaving(true); setError('')
    try {
      await qaApi.execute(c.id, run)
      await load(c.id); onChanged()
      if (run.status === 'failed') setLogBug(true)
    } catch (e) { setError(apiError(e)) } finally { setSaving(false) }
  }

  return (
    <>
      <Modal open={!!id && !logBug} onClose={onClose} wide title={c ? <span className="flex items-center gap-3"><code className="text-sm">{c.case_id}</code>{c.title}</span> : 'Test case'}
        footer={<Button variant="secondary" onClick={onClose}>Close</Button>}>
        {error && <Alert>{error}</Alert>}
        {!c ? !error && <Loading /> : <>
          <div className="grid sm:grid-cols-2 gap-4 text-sm">
            <div><div className="text-xs font-semibold text-slate-400 mb-1">Steps</div><pre className="whitespace-pre-wrap font-sans text-slate-700 bg-slate-50 rounded-lg p-3">{c.test_steps}</pre></div>
            <div className="space-y-3">
              <div><div className="text-xs font-semibold text-slate-400 mb-1">Expected</div><p className="text-slate-700">{c.expected_result}</p></div>
              {c.preconditions && <div><div className="text-xs font-semibold text-slate-400 mb-1">Preconditions</div><p className="text-slate-700">{c.preconditions}</p></div>}
            </div>
          </div>

          <div className="border border-slate-100 rounded-xl p-4 bg-slate-50/50">
            <div className="text-sm font-semibold text-slate-800 mb-3">Record a test run</div>
            <div className="grid sm:grid-cols-3 gap-3">
              <Field label="Result"><Select value={run.status} onChange={(e) => setRun({ ...run, status: e.target.value })}>
                {['passed', 'failed', 'blocked', 'skipped'].map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}</Select></Field>
              <Field label="Build"><Input value={run.build_version} onChange={(e) => setRun({ ...run, build_version: e.target.value })} /></Field>
              <div className="flex items-end"><Button icon={Play} onClick={execute} loading={saving} className="w-full">Save result</Button></div>
            </div>
            <Field label={run.status === 'failed' ? 'Actual result (required for a failure)' : 'Actual result / notes'}>
              <Input value={run.actual_result} onChange={(e) => setRun({ ...run, actual_result: e.target.value })} className="mt-1" />
            </Field>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-semibold text-slate-800">Run history</div>
              <Button variant="ghost" icon={Bug} onClick={() => setLogBug(true)} className="!py-1">Log defect</Button>
            </div>
            {!c.executions.length ? <p className="text-sm text-slate-400">Not run yet.</p> :
              <ul className="divide-y divide-slate-100 text-sm">
                {c.executions.map((e) => (
                  <li key={e.id} className="py-2 flex items-center gap-3">
                    <Badge status={e.status} />
                    <span className="text-slate-500">{fmtDateTime(e.executed_at)} · {e.executed_by} · build {e.build_version ?? '—'}</span>
                    {e.actual_result && <span className="text-slate-600 truncate">— {e.actual_result}</span>}
                  </li>
                ))}
              </ul>}
            {!!c.defects.length && <div className="mt-3 text-sm">
              <div className="text-xs font-semibold text-slate-400 mb-1">Linked defects</div>
              {c.defects.map((d) => <div key={d.id} className="flex items-center gap-2 py-1"><code className="text-xs">{d.defect_id}</code>{d.title}<Badge status={d.status} /></div>)}
            </div>}
          </div>
        </>}
      </Modal>
      <DefectModal open={logBug} testCaseId={c?.id} module={c?.module ?? undefined} onClose={() => setLogBug(false)}
        onDone={() => { setLogBug(false); if (c) load(c.id); onChanged() }} />
    </>
  )
}

