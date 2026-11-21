import { useEffect, useState } from 'react'
import { Calculator, Layers, Plus, Puzzle, Trash2, UserPlus, Users, Wallet } from 'lucide-react'
import { salaryApi, type Breakdown, type SalaryComponent, type SalaryStructure } from '../../api/modules'
import { employeesApi } from '../../api/employees'
import type { Employee } from '../../types'
import {
  Alert, Badge, Button, Card, Empty, ErrorState, Field, Input, Loading, Modal, Page, PageHeader, Select,
  Stat, StatGrid, Table, Tabs, apiError, inr, lakhs, td, tdNum, titleCase, useLoad,
} from '../../components/ui/kit'

const calcLabel = (c: { calculation_type: string; value?: number; component_type?: string }) =>
  c.calculation_type === 'fixed' ? `${inr(c.value)} / month`
    : c.calculation_type === 'percentage_of_gross' ? `${c.value}% of gross` : `${c.value}% of basic`

export default function SalaryPage() {
  const [tab, setTab] = useState<'structures' | 'assignments' | 'components'>('structures')
  const structures = useLoad(salaryApi.structures)
  const components = useLoad(salaryApi.components)
  const assignments = useLoad(salaryApi.assignments)
  const [newStructure, setNewStructure] = useState(false)
  const [newComponent, setNewComponent] = useState(false)
  const [assign, setAssign] = useState(false)

  const avgCtc = assignments.data?.length
    ? assignments.data.reduce((s, a) => s + a.gross_ctc, 0) / assignments.data.length : null
  const annual = assignments.data?.reduce((s, a) => s + a.gross_ctc, 0)

  return (
    <Page>
      <PageHeader title="Salary Structures"
        subtitle="Define pay components, build structures and assign them to employees"
        actions={<>
          <Button variant="secondary" icon={UserPlus} onClick={() => setAssign(true)}>Assign salary</Button>
          <Button icon={Plus} onClick={() => setNewStructure(true)}>New structure</Button>
        </>} />

      <StatGrid>
        <Stat label="Salary structures" value={structures.data?.length ?? '—'} icon={Layers} />
        <Stat label="Pay components" value={components.data?.length ?? '—'} icon={Puzzle} tone="indigo" />
        <Stat label="Employees on payroll" value={assignments.data?.length ?? '—'} icon={Users} tone="sky" />
        <Stat label="Annual CTC (all staff)" value={lakhs(annual)} icon={Wallet} tone="amber" hint={`Average ${lakhs(avgCtc)}`} />
      </StatGrid>

      <Tabs value={tab} onChange={setTab} tabs={[
        { id: 'structures', label: 'Structures', count: structures.data?.length },
        { id: 'assignments', label: 'Employee salaries', count: assignments.data?.length },
        { id: 'components', label: 'Components', count: components.data?.length },
      ]} />

      {tab === 'structures' && (
        structures.loading ? <Loading /> : structures.error ? <ErrorState message={structures.error} onRetry={structures.reload} /> :
          !structures.data?.length ? <Card><Empty title="No salary structures yet" action={<Button icon={Plus} onClick={() => setNewStructure(true)}>Create one</Button>} /></Card> :
            <div className="grid xl:grid-cols-2 gap-5">
              {structures.data.map((s) => <StructureCard key={s.id} s={s} />)}
            </div>
      )}

      {tab === 'assignments' && (
        <Card padded={false}>
          {assignments.loading ? <Loading /> : assignments.error ? <ErrorState message={assignments.error} /> :
            !assignments.data?.length ? <Empty title="No salaries assigned yet" /> :
              <Table head={['Employee', 'Department', 'Structure', 'Annual CTC', 'Monthly gross']}>
                {assignments.data.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50/70">
                    <td className={td}><div className="font-semibold text-slate-900">{a.employee_name}</div><div className="text-xs text-slate-400">{a.employee_code}</div></td>
                    <td className={td}>{a.department}</td>
                    <td className={td}>{a.structure_name}</td>
                    <td className={tdNum + ' text-left'}>{inr(a.gross_ctc)}</td>
                    <td className={tdNum + ' text-left'}>{inr(a.monthly_gross)}</td>
                  </tr>
                ))}
              </Table>}
        </Card>
      )}

      {tab === 'components' && (
        <Card padded={false} title="Pay components" actions={<Button variant="secondary" icon={Plus} onClick={() => setNewComponent(true)}>Add component</Button>}>
          {components.loading ? <Loading /> :
            <Table head={['Code', 'Name', 'Type', 'Calculated as', 'Taxable']}>
              {components.data?.map((c) => (
                <tr key={c.id}>
                  <td className={td}><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{c.code}</code></td>
                  <td className={td + ' font-medium'}>{c.name}</td>
                  <td className={td}><Badge status={c.component_type === 'earning' ? 'active' : 'pending'} label={titleCase(c.component_type)} /></td>
                  <td className={td}>{titleCase(c.calculation_type)}</td>
                  <td className={td}>{c.is_taxable ? 'Yes' : 'No'}</td>
                </tr>
              ))}
            </Table>}
        </Card>
      )}

      <StructureModal open={newStructure} components={components.data ?? []} onClose={() => setNewStructure(false)}
        onDone={() => { setNewStructure(false); structures.reload() }} />
      <ComponentModal open={newComponent} onClose={() => setNewComponent(false)}
        onDone={() => { setNewComponent(false); components.reload() }} />
      <AssignModal open={assign} structures={structures.data ?? []} onClose={() => setAssign(false)}
        onDone={() => { setAssign(false); assignments.reload(); structures.reload() }} />
    </Page>
  )
}

function StructureCard({ s }: { s: SalaryStructure }) {
  const [ctc, setCtc] = useState('1200000')
  const [b, setB] = useState<Breakdown | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    const value = Number(ctc)
    if (!value || value <= 0) { setB(null); return }
    const t = setTimeout(() => {
      salaryApi.preview(s.id, value).then((r) => { setB(r); setErr('') }).catch((e) => setErr(apiError(e)))
    }, 300)
    return () => clearTimeout(t)
  }, [ctc, s.id])

  return (
    <Card title={<span>{s.name} <span className="text-slate-400 font-normal">v{s.version}</span></span>}
      actions={<span className="text-xs text-slate-400">{s.employee_count} employees</span>}>
      {s.description && <p className="text-sm text-slate-500 -mt-1 mb-4">{s.description}</p>}
      <div className="grid sm:grid-cols-2 gap-5">
        <div>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Components</div>
          <ul className="space-y-1.5">
            {s.components.map((c) => (
              <li key={c.id} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full ${c.component_type === 'earning' ? 'bg-emerald-500' : 'bg-rose-400'}`} />
                  {c.name}
                </span>
                <span className="text-slate-500 text-xs">{calcLabel(c)}</span>
              </li>
            ))}
            <li className="flex items-center justify-between text-sm text-slate-400">
              <span className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-emerald-200" />Special allowance</span>
              <span className="text-xs">balance to gross</span>
            </li>
          </ul>
        </div>
        <div className="bg-slate-50 rounded-xl p-3.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 mb-2"><Calculator className="w-3.5 h-3.5" />Monthly breakdown for annual CTC</div>
          <Input type="number" value={ctc} onChange={(e) => setCtc(e.target.value)} className="mb-3" />
          {err && <p className="text-xs text-rose-600">{err}</p>}
          {b && (
            <div className="text-sm space-y-1">
              {b.items.map((i) => (
                <div key={i.code} className="flex justify-between">
                  <span className="text-slate-500">{i.name}</span>
                  <span className={`tabular-nums ${i.type === 'deduction' ? 'text-rose-600' : 'text-slate-800'}`}>
                    {i.type === 'deduction' ? '−' : ''}{inr(i.amount)}
                  </span>
                </div>
              ))}
              <div className="flex justify-between border-t border-slate-200 pt-1.5 mt-1.5 font-bold">
                <span>Take-home</span><span className="text-emerald-700 tabular-nums">{inr(b.net_pay)}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}

function StructureModal({ open, components, onClose, onDone }: {
  open: boolean; components: SalaryComponent[]; onClose: () => void; onDone: () => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [lines, setLines] = useState<{ component_id: string; value: string }[]>([{ component_id: '', value: '' }])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => { if (open) { setName(''); setDescription(''); setLines([{ component_id: '', value: '' }]); setError('') } }, [open])

  const save = async () => {
    setError('')
    const filled = lines.filter((l) => l.component_id)
    if (!name.trim() || !filled.length) { setError('Give the structure a name and at least one component'); return }
    setSaving(true)
    try {
      await salaryApi.createStructure({
        name, description: description || undefined,
        components: filled.map((l, i) => ({ component_id: Number(l.component_id), value: Number(l.value || 0), sequence: i + 1 })),
      })
      onDone()
    } catch (e) { setError(apiError(e)) } finally { setSaving(false) }
  }

  return (
    <Modal open={open} onClose={onClose} title="New salary structure" wide
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={save} loading={saving}>Create structure</Button></>}>
      {error && <Alert>{error}</Alert>}
      <div className="grid sm:grid-cols-2 gap-4">
        <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Sales Incentive Plan" /></Field>
        <Field label="Description"><Input value={description} onChange={(e) => setDescription(e.target.value)} /></Field>
      </div>
      <div>
        <div className="text-xs font-semibold text-slate-600 mb-1.5">Components (calculated top to bottom; put Basic first)</div>
        <div className="space-y-2">
          {lines.map((l, i) => {
            const comp = components.find((c) => c.id === Number(l.component_id))
            return (
              <div key={i} className="flex gap-2 items-center">
                <Select value={l.component_id} onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, component_id: e.target.value } : x))}>
                  <option value="">Choose component…</option>
                  {components.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.code})</option>)}
                </Select>
                <Input type="number" className="!w-40" value={l.value} placeholder={comp?.calculation_type === 'fixed' ? '₹ per month' : '%'}
                  onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, value: e.target.value } : x))} />
                <span className="text-xs text-slate-400 w-28">{comp ? titleCase(comp.calculation_type) : ''}</span>
                <button onClick={() => setLines(lines.filter((_, j) => j !== i))} className="p-2 text-slate-400 hover:text-rose-500"><Trash2 className="w-4 h-4" /></button>
              </div>
            )
          })}
        </div>
        <Button variant="ghost" icon={Plus} className="mt-2" onClick={() => setLines([...lines, { component_id: '', value: '' }])}>Add line</Button>
      </div>
      <p className="text-xs text-slate-400">Saving a structure with an existing name creates a new version, so past payslips keep their original rules.</p>
    </Modal>
  )
}

function ComponentModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const [f, setF] = useState({ name: '', code: '', component_type: 'earning', calculation_type: 'fixed', is_taxable: true })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (open) { setF({ name: '', code: '', component_type: 'earning', calculation_type: 'fixed', is_taxable: true }); setError('') } }, [open])
  const save = async () => {
    setSaving(true); setError('')
    try { await salaryApi.createComponent(f as Partial<SalaryComponent>); onDone() } catch (e) { setError(apiError(e)) } finally { setSaving(false) }
  }
  return (
    <Modal open={open} onClose={onClose} title="Add pay component"
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={save} loading={saving}>Add</Button></>}>
      {error && <Alert>{error}</Alert>}
      <div className="grid grid-cols-2 gap-4">
        <Field label="Name"><Input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Meal Allowance" /></Field>
        <Field label="Code"><Input value={f.code} onChange={(e) => setF({ ...f, code: e.target.value.toUpperCase() })} placeholder="MEAL" /></Field>
        <Field label="Type"><Select value={f.component_type} onChange={(e) => setF({ ...f, component_type: e.target.value })}>
          <option value="earning">Earning</option><option value="deduction">Deduction</option></Select></Field>
        <Field label="Calculated as"><Select value={f.calculation_type} onChange={(e) => setF({ ...f, calculation_type: e.target.value })}>
          <option value="fixed">Fixed amount</option><option value="percentage_of_gross">% of gross</option><option value="percentage_of_basic">% of basic</option></Select></Field>
      </div>
      <label className="flex items-center gap-2 text-sm text-slate-600">
        <input type="checkbox" checked={f.is_taxable} onChange={(e) => setF({ ...f, is_taxable: e.target.checked })} className="accent-emerald-600" /> Taxable
      </label>
    </Modal>
  )
}

function AssignModal({ open, structures, onClose, onDone }: {
  open: boolean; structures: SalaryStructure[]; onClose: () => void; onDone: () => void
}) {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [f, setF] = useState({ employee_id: '', structure_id: '', gross_ctc: '' })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => {
    if (!open) return
    setF({ employee_id: '', structure_id: '', gross_ctc: '' }); setError('')
    employeesApi.list({ page_size: 100, sort_by: 'first_name', sort_dir: 'asc' }).then((r) => setEmployees(r.items)).catch(() => {})
  }, [open])
  const pick = (id: string) => {
    const e = employees.find((x) => x.id === Number(id))
    setF({ ...f, employee_id: id, gross_ctc: e?.gross_ctc ? String(e.gross_ctc) : f.gross_ctc })
  }
  const save = async () => {
    if (!f.employee_id || !f.structure_id || !Number(f.gross_ctc)) { setError('Choose an employee, a structure and an annual CTC'); return }
    setSaving(true); setError('')
    try {
      await salaryApi.assign({ employee_id: Number(f.employee_id), structure_id: Number(f.structure_id), gross_ctc: Number(f.gross_ctc) })
      onDone()
    } catch (e) { setError(apiError(e)) } finally { setSaving(false) }
  }
  return (
    <Modal open={open} onClose={onClose} title="Assign salary to employee"
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={save} loading={saving}>Assign</Button></>}>
      {error && <Alert>{error}</Alert>}
      <Field label="Employee"><Select value={f.employee_id} onChange={(e) => pick(e.target.value)}>
        <option value="">Choose employee…</option>
        {employees.map((e) => <option key={e.id} value={e.id}>{e.full_name} ({e.employee_code})</option>)}
      </Select></Field>
      <Field label="Salary structure"><Select value={f.structure_id} onChange={(e) => setF({ ...f, structure_id: e.target.value })}>
        <option value="">Choose structure…</option>
        {structures.map((s) => <option key={s.id} value={s.id}>{s.name} v{s.version}</option>)}
      </Select></Field>
      <Field label="Annual CTC (₹)" hint={Number(f.gross_ctc) ? `${inr(Number(f.gross_ctc) / 12)} per month` : undefined}>
        <Input type="number" value={f.gross_ctc} onChange={(e) => setF({ ...f, gross_ctc: e.target.value })} />
      </Field>
      <p className="text-xs text-slate-400">The previous salary record is kept as history and the change is written to the audit log.</p>
    </Modal>
  )
}
