import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, CheckCircle2, Clock, GitBranch, Plus, Power, Trash2, X, XCircle } from 'lucide-react'
import clsx from 'clsx'
import { workflowApi, type ApprovalReq, type Stage, type WorkflowDef } from '../../api/modules'
import { useAuth } from '../../context/AuthContext'
import {
  Alert, Badge, Button, Card, Empty, ErrorState, Field, Input, Loading, Modal, Page, PageHeader, Select,
  Stat, StatGrid, Tabs, TextArea, apiError, fmtDateTime, titleCase, useLoad,
} from '../../components/ui/kit'

const ENTITY_LINK: Record<string, (id: number) => string> = {
  payroll_approval: (id) => `/payroll/${id}`,
}

export default function ApprovalsPage() {
  const { user } = useAuth()
  const [tab, setTab] = useState<'open' | 'closed' | 'setup'>('open')
  const open = useLoad(() => workflowApi.requests('open'))
  const closed = useLoad(() => workflowApi.requests('closed'))
  const defs = useLoad(workflowApi.definitions)
  const [acting, setActing] = useState<ApprovalReq | null>(null)
  const [viewing, setViewing] = useState<number | null>(null)
  const [newDef, setNewDef] = useState(false)
  const mine = open.data?.filter((r) => r.can_act).length ?? 0
  const refresh = () => { open.reload(); closed.reload() }

  return (
    <Page>
      <PageHeader title="Approvals" subtitle="Multi-stage approval workflows for payroll and increments"
        actions={['company_admin', 'platform_admin'].includes(user?.role ?? '') &&
          <Button icon={Plus} variant="secondary" onClick={() => { setTab('setup'); setNewDef(true) }}>New workflow</Button>} />

      <StatGrid>
        <Stat label="Waiting on you" value={mine} icon={Clock} tone="amber" />
        <Stat label="Open requests" value={open.data?.length ?? '—'} icon={GitBranch} tone="sky" />
        <Stat label="Approved" value={closed.data?.filter((r) => r.status === 'approved').length ?? '—'} icon={CheckCircle2} />
        <Stat label="Rejected" value={closed.data?.filter((r) => r.status === 'rejected').length ?? '—'} icon={XCircle} tone="rose" />
      </StatGrid>

      <Tabs value={tab} onChange={setTab} tabs={[
        { id: 'open', label: 'Open', count: open.data?.length },
        { id: 'closed', label: 'History', count: closed.data?.length },
        { id: 'setup', label: 'Workflow setup', count: defs.data?.length },
      ]} />

      {tab !== 'setup' && (() => {
        const src = tab === 'open' ? open : closed
        if (src.loading) return <Loading />
        if (src.error) return <ErrorState message={src.error} onRetry={src.reload} />
        if (!src.data?.length) return <Card><Empty title={tab === 'open' ? 'Nothing waiting for approval' : 'No history yet'}
          hint={tab === 'open' ? 'Processed payrolls and submitted increments appear here.' : undefined} /></Card>
        return (
          <div className="space-y-3">
            {src.data.map((r) => <RequestRow key={r.id} r={r} onAct={() => setActing(r)} onView={() => setViewing(r.id)} />)}
          </div>
        )
      })()}

      {tab === 'setup' && (
        defs.loading ? <Loading /> : !defs.data?.length ? <Card><Empty title="No workflows configured" /></Card> :
          <div className="grid md:grid-cols-2 gap-4">
            {defs.data.map((d) => <DefinitionCard key={d.id} d={d} canEdit={['company_admin', 'platform_admin'].includes(user?.role ?? '')} onChanged={defs.reload} />)}
          </div>
      )}

      <ActModal req={acting} onClose={() => setActing(null)} onDone={() => { setActing(null); refresh() }} />
      <DetailModal id={viewing} onClose={() => setViewing(null)} />
      <DefinitionModal open={newDef} onClose={() => setNewDef(false)} onDone={() => { setNewDef(false); defs.reload() }} />
    </Page>
  )
}

function Stepper({ stages, current, status }: { stages: Stage[]; current: number; status: string }) {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {stages.map((s, i) => {
        const done = status === 'approved' || s.stage < current
        const failed = status === 'rejected' && s.stage === current
        const active = !done && !failed && s.stage === current && ['pending', 'in_progress'].includes(status)
        return (
          <div key={s.stage} className="flex items-center gap-1">
            <div className={clsx('flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium',
              done && 'bg-emerald-50 text-emerald-700', failed && 'bg-rose-50 text-rose-700',
              active && 'bg-amber-50 text-amber-800 ring-1 ring-amber-200', !done && !failed && !active && 'bg-slate-50 text-slate-400')}>
              {done ? <Check className="w-3.5 h-3.5" /> : failed ? <X className="w-3.5 h-3.5" /> : <span className="w-3.5 text-center">{s.stage}</span>}
              {s.label}
            </div>
            {i < stages.length - 1 && <span className="w-3 h-px bg-slate-200" />}
          </div>
        )
      })}
    </div>
  )
}

function RequestRow({ r, onAct, onView }: { r: ApprovalReq; onAct: () => void; onView: () => void }) {
  const link = ENTITY_LINK[r.entity_type]?.(r.entity_id)
  return (
    <Card>
      <div className="flex flex-col lg:flex-row lg:items-center gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-slate-900 truncate">{r.entity_ref}</span>
            <Badge status={r.status} />
          </div>
          <div className="text-xs text-slate-400 mb-2.5">{r.workflow_name} · {titleCase(r.entity_type)} · raised {fmtDateTime(r.created_at)}
            {link && <> · <Link to={link} className="text-emerald-600 hover:underline">open record</Link></>}</div>
          <Stepper stages={r.stages} current={r.current_stage} status={r.status} />
        </div>
        <div className="flex items-center gap-2 lg:justify-end">
          {['pending', 'in_progress'].includes(r.status) && !r.can_act && r.current_stage_role &&
            <span className="text-xs text-slate-400">Waiting for {titleCase(r.current_stage_role)}</span>}
          <Button variant="secondary" onClick={onView}>History</Button>
          {r.can_act && <Button onClick={onAct}>Review</Button>}
        </div>
      </div>
    </Card>
  )
}

function ActModal({ req, onClose, onDone }: { req: ApprovalReq | null; onClose: () => void; onDone: () => void }) {
  const [comments, setComments] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  useEffect(() => { setComments(''); setError('') }, [req])
  if (!req) return null
  const act = async (approve: boolean) => {
    setBusy(approve ? 'a' : 'r'); setError('')
    try { await workflowApi.act(req.id, approve, comments); onDone() } catch (e) { setError(apiError(e)) } finally { setBusy('') }
  }
  return (
    <Modal open onClose={onClose} title={req.entity_ref}
      footer={<><Button variant="danger" loading={busy === 'r'} onClick={() => act(false)}>Reject</Button>
        <Button loading={busy === 'a'} onClick={() => act(true)}>Approve {req.current_stage < req.total_stages ? '& forward' : ''}</Button></>}>
      {error && <Alert>{error}</Alert>}
      <Stepper stages={req.stages} current={req.current_stage} status={req.status} />
      <p className="text-sm text-slate-600">You are acting on stage <b>{req.current_stage_label}</b> ({req.current_stage} of {req.total_stages}).
        {req.current_stage < req.total_stages ? ' Approving sends it to the next stage.' : ' This is the final stage: approving completes it.'}</p>
      <Field label="Comments" hint="Required when rejecting"><TextArea value={comments} onChange={(e) => setComments(e.target.value)} /></Field>
    </Modal>
  )
}

function DetailModal({ id, onClose }: { id: number | null; onClose: () => void }) {
  const [r, setR] = useState<ApprovalReq | null>(null)
  useEffect(() => { if (id) { setR(null); workflowApi.request(id).then(setR).catch(() => {}) } }, [id])
  return (
    <Modal open={!!id} onClose={onClose} title={r?.entity_ref ?? 'Approval history'} footer={<Button variant="secondary" onClick={onClose}>Close</Button>}>
      {!r ? <Loading /> : <>
        <Stepper stages={r.stages} current={r.current_stage} status={r.status} />
        {!r.actions?.length ? <p className="text-sm text-slate-400">No one has acted on this yet.</p> :
          <ol className="relative border-l border-slate-200 ml-2 space-y-4">
            {r.actions.map((a, i) => (
              <li key={i} className="ml-4">
                <span className={clsx('absolute -left-1.5 w-3 h-3 rounded-full', a.action === 'approved' ? 'bg-emerald-500' : 'bg-rose-500')} />
                <div className="text-sm"><b>{a.approver}</b> {a.action} <span className="text-slate-400">· {a.stage_label}</span></div>
                <div className="text-xs text-slate-400">{fmtDateTime(a.created_at)}</div>
                {a.comments && <div className="text-sm text-slate-600 mt-1 bg-slate-50 rounded-lg px-3 py-2">{a.comments}</div>}
              </li>
            ))}
          </ol>}
      </>}
    </Modal>
  )
}

function DefinitionCard({ d, canEdit, onChanged }: { d: WorkflowDef; canEdit: boolean; onChanged: () => void }) {
  const [busy, setBusy] = useState(false)
  return (
    <Card className={d.is_active ? '' : 'opacity-60'}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="font-semibold text-slate-900">{d.name}</div>
          <div className="text-xs text-slate-400">For {titleCase(d.entity_type)}</div>
        </div>
        <div className="flex items-center gap-2">
          <Badge status={d.is_active ? 'active' : 'inactive'} />
          {canEdit && <button disabled={busy} title={d.is_active ? 'Deactivate' : 'Activate'} onClick={async () => { setBusy(true); try { await workflowApi.toggle(d.id); onChanged() } finally { setBusy(false) } }}
            className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-600 hover:bg-emerald-50"><Power className="w-4 h-4" /></button>}
        </div>
      </div>
      <ol className="space-y-2">
        {d.stages.map((s) => (
          <li key={s.stage} className="flex items-center gap-3 text-sm">
            <span className="w-6 h-6 rounded-full bg-emerald-50 text-emerald-700 text-xs font-bold flex items-center justify-center">{s.stage}</span>
            <span className="font-medium text-slate-800">{s.label}</span>
            <span className="text-xs text-slate-400">by {titleCase(s.role)}</span>
          </li>
        ))}
      </ol>
    </Card>
  )
}

function DefinitionModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const [roles, setRoles] = useState<string[]>([])
  const [name, setName] = useState('')
  const [entity, setEntity] = useState('payroll_approval')
  const [stages, setStages] = useState([{ role: 'hr_manager', label: 'HR review' }])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => {
    if (!open) return
    setName(''); setEntity('payroll_approval'); setStages([{ role: 'hr_manager', label: 'HR review' }]); setError('')
    workflowApi.roles().then(setRoles).catch(() => {})
  }, [open])
  const save = async () => {
    setSaving(true); setError('')
    try { await workflowApi.createDefinition({ name, entity_type: entity, stages }); onDone() } catch (e) { setError(apiError(e)) } finally { setSaving(false) }
  }
  return (
    <Modal open={open} onClose={onClose} title="New approval workflow"
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={save} loading={saving}>Save workflow</Button></>}>
      {error && <Alert>{error}</Alert>}
      <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Payroll sign-off" /></Field>
      <Field label="Applies to"><Select value={entity} onChange={(e) => setEntity(e.target.value)}>
        <option value="payroll_approval">Payroll runs</option><option value="compensation_plan">Increment plans</option></Select></Field>
      <div>
        <div className="text-xs font-semibold text-slate-600 mb-1.5">Stages, in order</div>
        <div className="space-y-2">
          {stages.map((s, i) => (
            <div key={i} className="flex gap-2 items-center">
              <span className="w-6 text-sm text-slate-400 text-center">{i + 1}</span>
              <Input value={s.label} onChange={(e) => setStages(stages.map((x, j) => j === i ? { ...x, label: e.target.value } : x))} placeholder="Stage name" />
              <Select value={s.role} onChange={(e) => setStages(stages.map((x, j) => j === i ? { ...x, role: e.target.value } : x))} className="!w-48">
                {roles.map((r) => <option key={r} value={r}>{titleCase(r)}</option>)}</Select>
              <button onClick={() => setStages(stages.filter((_, j) => j !== i))} className="p-2 text-slate-400 hover:text-rose-500"><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
        <Button variant="ghost" icon={Plus} className="mt-2" onClick={() => setStages([...stages, { role: 'finance_manager', label: '' }])}>Add stage</Button>
      </div>
      <p className="text-xs text-slate-400">Saving replaces the currently active workflow for the same record type. Requests already in progress keep their original stages.</p>
    </Modal>
  )
}
