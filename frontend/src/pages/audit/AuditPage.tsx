import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, Search } from 'lucide-react'
import { auditApi, type AuditEntry } from '../../api/modules'
import {
  Card, Empty, ErrorState, Input, Loading, Page, PageHeader, Select, Table, fmtDateTime, td, titleCase, useLoad,
} from '../../components/ui/kit'

const ACTION_TONE = (a: string) =>
  /reject|cancel|deactivate|delete/.test(a) ? 'bg-rose-50 text-rose-700'
    : /approve|paid|complete|apply/.test(a) ? 'bg-emerald-50 text-emerald-700'
      : /login/.test(a) ? 'bg-slate-100 text-slate-500' : 'bg-sky-50 text-sky-700'

function Diff({ e }: { e: AuditEntry }) {
  if (!e.old_values && !e.new_values) return <span className="text-slate-300">—</span>
  const keys = Array.from(new Set([...Object.keys(e.old_values ?? {}), ...Object.keys(e.new_values ?? {})]))
  return (
    <div className="space-y-0.5 text-xs">
      {keys.map((k) => {
        const o = e.old_values?.[k]; const n = e.new_values?.[k]
        const show = (v: unknown) => typeof v === 'object' ? JSON.stringify(v) : String(v)
        return (
          <div key={k} className="truncate max-w-xs" title={`${k}: ${o !== undefined ? show(o) + ' → ' : ''}${show(n)}`}>
            <span className="text-slate-400">{k}:</span>{' '}
            {o !== undefined && o !== null && <><span className="line-through text-rose-500">{show(o)}</span>{' → '}</>}
            <span className="text-slate-700">{n === undefined ? '' : show(n)}</span>
          </div>
        )
      })}
    </div>
  )
}

export default function AuditPage() {
  const [page, setPage] = useState(1)
  const [entity, setEntity] = useState('')
  const [action, setAction] = useState('')
  const [search, setSearch] = useState('')
  const [term, setTerm] = useState('')
  const filters = useLoad(auditApi.filters)
  const { data, loading, error, reload } = useLoad(() => auditApi.list({ page, entity_type: entity, action, search: term }), [page, entity, action, term])
  useEffect(() => { const t = setTimeout(() => { setTerm(search); setPage(1) }, 350); return () => clearTimeout(t) }, [search])

  return (
    <Page>
      <PageHeader title="Audit Log" subtitle="Every important change, who made it and when. Entries are never edited or deleted." />
      <Card padded={false} title={data ? `${data.total.toLocaleString()} entries` : 'Entries'} actions={<>
        <Select value={entity} onChange={(e) => { setEntity(e.target.value); setPage(1) }} className="!py-1.5 !w-44">
          <option value="">All records</option>{filters.data?.entity_types.map((x) => <option key={x} value={x}>{titleCase(x)}</option>)}</Select>
        <Select value={action} onChange={(e) => { setAction(e.target.value); setPage(1) }} className="!py-1.5 !w-48">
          <option value="">All actions</option>{filters.data?.actions.map((x) => <option key={x} value={x}>{x}</option>)}</Select>
        <div className="relative"><Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="User or record…" className="!py-1.5 pl-9 !w-48" /></div>
      </>}>
        {loading && !data ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> :
          !data?.items.length ? <Empty title="No matching entries" /> : <>
            <Table minWidth={900} head={['When', 'User', 'Action', 'Record', 'Change']}>
              {data.items.map((e) => (
                <tr key={e.id} className="align-top hover:bg-slate-50/70">
                  <td className={td + ' whitespace-nowrap text-slate-500'}>{fmtDateTime(e.created_at)}</td>
                  <td className={td + ' whitespace-nowrap'}>{e.user_email}</td>
                  <td className={td}><span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${ACTION_TONE(e.action)}`}>{e.action}</span></td>
                  <td className={td}><div className="text-slate-800">{e.entity_ref ?? '—'}</div><div className="text-xs text-slate-400">{titleCase(e.entity_type)}{e.entity_id ? ` #${e.entity_id}` : ''}</div></td>
                  <td className={td}><Diff e={e} /></td>
                </tr>
              ))}
            </Table>
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
              <span>Page {data.page} of {Math.max(1, data.total_pages)}</span>
              <div className="flex gap-1">
                <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="p-1.5 rounded-lg hover:bg-slate-100 disabled:opacity-40"><ChevronLeft className="w-4 h-4" /></button>
                <button disabled={page >= data.total_pages} onClick={() => setPage(page + 1)} className="p-1.5 rounded-lg hover:bg-slate-100 disabled:opacity-40"><ChevronRight className="w-4 h-4" /></button>
              </div>
            </div>
          </>}
      </Card>
    </Page>
  )
}
