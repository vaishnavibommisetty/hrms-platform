import { useEffect, useMemo, useState } from 'react'
import { Check, Code2, Copy, Database, Download, Play, ShieldCheck, Timer } from 'lucide-react'
import clsx from 'clsx'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { reportsApi, type ReportMeta, type ReportResult } from '../../api/modules'
import { Alert, Button, Card, Empty, Loading, Page, PageHeader, apiError, titleCase, useLoad } from '../../components/ui/kit'

const SERIES = ['#10b981', '#6366f1', '#f59e0b', '#f43f5e', '#06b6d4']
const MONEY_COLS = /(ctc|pay|gross|net|deduction|payroll|cost|salary|difference|change)/i

const fmtCell = (col: string, v: string | number | null) => {
  if (v === null || v === '') return <span className="text-slate-300">—</span>
  if (typeof v === 'number') {
    if (MONEY_COLS.test(col) && !/pct|ratio/i.test(col)) return `₹${v.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
    return v.toLocaleString('en-IN', { maximumFractionDigits: 2 })
  }
  return v
}

/** Very small SQL highlighter: keywords, strings, comments, :params. */
function highlight(sql: string) {
  const kw = /\b(SELECT|FROM|WHERE|JOIN|LEFT|ON|AND|OR|NOT|IN|AS|GROUP|BY|ORDER|HAVING|WITH|CASE|WHEN|THEN|ELSE|END|LIMIT|UNION|ALL|DESC|ASC|IS|NULL|EXISTS|OVER|PARTITION|DISTINCT|INTERVAL|TRUE|FALSE)\b/g
  const fn = /\b(COUNT|SUM|AVG|MIN|MAX|ROUND|COALESCE|NULLIF|ROW_NUMBER|RANK|LAG|TO_CHAR|ABS|CURRENT_DATE)\b/g
  return sql
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/('[^']*')/g, '<span class="text-amber-300">$1</span>')
    .replace(kw, '<span class="text-sky-300 font-semibold">$1</span>')
    .replace(fn, '<span class="text-emerald-300">$1</span>')
    .replace(/(:company_id)/g, '<span class="text-rose-300">$1</span>')
}

export default function ReportsPage() {
  const list = useLoad(reportsApi.list)
  const [selected, setSelected] = useState<string>('')
  const [result, setResult] = useState<ReportResult | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [showSql, setShowSql] = useState(true)
  const [copied, setCopied] = useState(false)

  const groups = useMemo(() => {
    const g: Record<string, ReportMeta[]> = {}
    list.data?.forEach((r) => { (g[r.category] ??= []).push(r) })
    return g
  }, [list.data])

  const run = async (id: string) => {
    setSelected(id); setRunning(true); setError('')
    try { setResult(await reportsApi.run(id)) } catch (e) { setResult(null); setError(apiError(e)) } finally { setRunning(false) }
  }
  useEffect(() => { if (list.data?.length && !selected) run(list.data[0].id) }, [list.data]) // eslint-disable-line react-hooks/exhaustive-deps

  const exportCsv = () => {
    if (!result) return
    const esc = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`
    const csv = [result.columns.map(esc).join(','), ...result.rows.map((r) => r.map(esc).join(','))].join('\n')
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    a.download = `${result.id}.csv`
    a.click()
  }
  const copySql = async () => {
    if (!result) return
    await navigator.clipboard.writeText(result.sql)
    setCopied(true); setTimeout(() => setCopied(false), 1500)
  }

  const chartData = result?.chart ? result.rows.map((r) => Object.fromEntries(result.columns.map((c, i) => [c, r[i]]))) : []

  return (
    <Page>
      <PageHeader title="SQL Reports" subtitle="Live queries against the production database. Every query is scoped to your company with a :company_id parameter."
        actions={result && <Button variant="secondary" icon={Download} onClick={exportCsv}>Export CSV</Button>} />

      <div className="grid lg:grid-cols-[280px_1fr] gap-5">
        <Card padded={false} className="h-fit lg:sticky lg:top-4">
          {list.loading ? <Loading /> : Object.entries(groups).map(([cat, reps]) => (
            <div key={cat} className="py-2 border-b border-slate-50 last:border-0">
              <div className="px-4 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{cat}</div>
              {reps.map((r) => (
                <button key={r.id} onClick={() => run(r.id)}
                  className={clsx('w-full text-left px-4 py-2 text-sm transition-colors flex items-center gap-2',
                    selected === r.id ? 'bg-emerald-50 text-emerald-800 font-semibold' : 'text-slate-600 hover:bg-slate-50')}>
                  <Database className={clsx('w-3.5 h-3.5 flex-shrink-0', selected === r.id ? 'text-emerald-600' : 'text-slate-300')} />
                  <span className="truncate">{r.title}</span>
                </button>
              ))}
            </div>
          ))}
        </Card>

        <div className="space-y-5 min-w-0">
          {error && <Alert>{error}</Alert>}
          {running && !result ? <Card><Loading label="Running query…" /></Card> : result && (
            <>
              <Card>
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div>
                    <div className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">{result.category}</div>
                    <h2 className="text-lg font-bold text-slate-900">{result.title}</h2>
                    <p className="text-sm text-slate-500 mt-0.5">{result.description}</p>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500 whitespace-nowrap">
                    <span className="flex items-center gap-1"><Timer className="w-3.5 h-3.5" />{result.execution_ms} ms</span>
                    <span>{result.row_count} rows</span>
                    <Button variant="secondary" icon={Play} loading={running} onClick={() => run(result.id)} className="!py-1.5">Re-run</Button>
                  </div>
                </div>
              </Card>

              {result.chart && result.rows.length > 0 && (
                <Card>
                  <ResponsiveContainer width="100%" height={260}>
                    {result.chart.type === 'line' ? (
                      <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                        <XAxis dataKey={result.chart.x} tick={{ fontSize: 12, fill: '#64748b' }} />
                        <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} tickFormatter={(v) => Number(v) >= 100000 ? `${(v / 100000).toFixed(1)}L` : v} />
                        <Tooltip /><Legend formatter={titleCase} />
                        {result.chart.y.map((y, i) => <Line key={y} dataKey={y} stroke={SERIES[i]} strokeWidth={2.5} dot={{ r: 4 }} name={y} />)}
                      </LineChart>
                    ) : (
                      <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis dataKey={result.chart.x} tick={{ fontSize: 11, fill: '#64748b' }} interval={0} />
                        <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} tickFormatter={(v) => Number(v) >= 100000 ? `${(v / 100000).toFixed(1)}L` : v} />
                        <Tooltip /><Legend formatter={titleCase} />
                        {result.chart.y.map((y, i) => <Bar key={y} dataKey={y} fill={SERIES[i]} radius={[4, 4, 0, 0]} name={y}
                          stackId={result.chart!.y.length > 2 ? 'a' : undefined} />)}
                      </BarChart>
                    )}
                  </ResponsiveContainer>
                </Card>
              )}

              <Card padded={false}>
                {!result.rows.length ? <Empty title="The query returned no rows" hint={result.id === 'data_quality' ? 'No data problems found. Nice.' : undefined} /> :
                  <div className="overflow-x-auto max-h-[420px]">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-slate-50"><tr className="border-b border-slate-100">
                        {result.columns.map((c) => <th key={c} className="text-left text-xs font-semibold text-slate-500 px-4 py-3 whitespace-nowrap font-mono">{c}</th>)}
                      </tr></thead>
                      <tbody className="divide-y divide-slate-50">
                        {result.rows.map((r, i) => (
                          <tr key={i} className="hover:bg-slate-50/70">
                            {r.map((v, j) => <td key={j} className={clsx('px-4 py-2.5 whitespace-nowrap', typeof v === 'number' && 'tabular-nums')}>{fmtCell(result.columns[j], v)}</td>)}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>}
              </Card>

              <div className="rounded-2xl overflow-hidden border border-slate-800 bg-slate-900 shadow-sm">
                <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800">
                  <button onClick={() => setShowSql(!showSql)} className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                    <Code2 className="w-4 h-4 text-emerald-400" />{showSql ? 'Hide' : 'Show'} SQL
                  </button>
                  <div className="flex items-center gap-3">
                    <span className="hidden sm:flex items-center gap-1 text-xs text-slate-400"><ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />Parameterised · tenant-scoped</span>
                    <button onClick={copySql} className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-white px-2 py-1 rounded-md hover:bg-slate-800">
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}{copied ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                </div>
                {showSql && <pre className="p-4 text-[13px] leading-relaxed text-slate-300 overflow-x-auto font-mono"
                  dangerouslySetInnerHTML={{ __html: highlight(result.sql) }} />}
              </div>
            </>
          )}
        </div>
      </div>
    </Page>
  )
}
