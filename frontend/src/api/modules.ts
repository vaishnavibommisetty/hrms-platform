import { apiClient } from './client'

const get = async <T,>(url: string) => (await apiClient.get<T>(url)).data
const post = async <T,>(url: string, body?: unknown) => (await apiClient.post<T>(url, body)).data
const put = async <T,>(url: string, body?: unknown) => (await apiClient.put<T>(url, body)).data

// ─── Salary ──────────────────────────────────────────────────────────────
export interface SalaryComponent {
  id: number; name: string; code: string; component_type: 'earning' | 'deduction'
  calculation_type: 'fixed' | 'percentage_of_basic' | 'percentage_of_gross'; is_taxable: boolean
  description: string | null
}
export interface StructureLine {
  id: number; component_id: number; code: string; name: string; component_type: string
  calculation_type: string; value: number; sequence: number
}
export interface SalaryStructure {
  id: number; name: string; version: number; description: string | null; is_active: boolean
  effective_date: string; employee_count: number; components: StructureLine[]
}
export interface BreakdownItem { code: string; name: string; type: string; calculation: string; rate: number; amount: number }
export interface Breakdown { monthly_gross: number; total_earnings: number; total_deductions: number; net_pay: number; items: BreakdownItem[] }
export interface Assignment {
  id: number; employee_id: number; employee_code: string; employee_name: string; department: string | null
  structure_id: number; structure_name: string; gross_ctc: number; monthly_gross: number; effective_date: string
}

export const salaryApi = {
  components: () => get<SalaryComponent[]>('/salary/components'),
  createComponent: (b: Partial<SalaryComponent>) => post<SalaryComponent>('/salary/components', b),
  structures: () => get<SalaryStructure[]>('/salary/structures'),
  createStructure: (b: { name: string; description?: string; components: { component_id: number; value: number; sequence: number }[] }) =>
    post<SalaryStructure>('/salary/structures', b),
  preview: (id: number, ctc: number) => get<Breakdown>(`/salary/structures/${id}/preview?ctc=${ctc}`),
  assignments: () => get<Assignment[]>('/salary/assignments'),
  assign: (b: { employee_id: number; structure_id: number; gross_ctc: number }) => post('/salary/assignments', b),
  employee: (id: number) => get<{
    current: { structure_name: string; gross_ctc: number; effective_date: string } | null
    breakdown: Breakdown | null
    history: { structure_name: string; gross_ctc: number; effective_date: string; end_date: string | null }[]
  }>(`/salary/employees/${id}`),
}

// ─── Payroll ─────────────────────────────────────────────────────────────
export interface PayrollRun {
  id: number; month: number; year: number; period: string; status: string; total_employees: number | null
  total_gross: number | null; total_deductions: number | null; total_net: number | null
  processed_at: string | null; approved_at: string | null; notes: string | null; created_at: string
}
export interface PayslipRow {
  id: number; employee_id: number; employee_code: string; employee_name: string; department: string | null
  gross_salary: number; total_earnings: number; total_deductions: number; net_salary: number
  working_days: number; paid_days: number
}
export interface Payslip {
  id: number; period: string; run_status: string
  employee: { id: number; code: string; name: string; email: string; department: string | null; designation: string | null }
  working_days: number; paid_days: number; gross_salary: number; total_earnings: number; total_deductions: number
  net_salary: number; items: { name: string; type: string; amount: number }[]
}

export const payrollApi = {
  runs: () => get<PayrollRun[]>('/payroll/runs'),
  create: (month: number, year: number) => post<PayrollRun>('/payroll/runs', { month, year }),
  run: (id: number) => get<PayrollRun & { payslips: PayslipRow[]; approval_request_id: number | null }>(`/payroll/runs/${id}`),
  process: (id: number) => post<PayrollRun & { skipped: string[]; approval_request_id: number | null }>(`/payroll/runs/${id}/process`),
  approve: (id: number) => post<PayrollRun>(`/payroll/runs/${id}/approve`),
  markPaid: (id: number) => post<PayrollRun>(`/payroll/runs/${id}/mark-paid`),
  cancel: (id: number) => post<PayrollRun>(`/payroll/runs/${id}/cancel`),
  payslip: (id: number) => get<Payslip>(`/payroll/payslips/${id}`),
}

// ─── Performance ─────────────────────────────────────────────────────────
export interface PerfCycle {
  id: number; name: string; year: number; start_date: string; end_date: string; status: string
  total_reviews: number; completed_reviews: number; average_score: number | null; kpi_count: number
}
export interface ReviewRow {
  id: number; employee_id: number; employee_name: string; employee_code: string; department: string | null
  status: string; self_overall_score: number | null; manager_overall_score: number | null
  final_score: number | null; rating: string | null
}
export interface Review {
  id: number; cycle_id: number; cycle_name: string; employee_id: number; employee_name: string; status: string
  self_comments: string | null; manager_comments: string | null; self_overall_score: number | null
  manager_overall_score: number | null; final_score: number | null; rating: string | null
  kpis: { kpi_id: number; name: string; description: string | null; weight_pct: number; self_score: number | null; manager_score: number | null }[]
}

export const performanceApi = {
  cycles: () => get<PerfCycle[]>('/performance/cycles'),
  create: (b: unknown) => post<PerfCycle>('/performance/cycles', b),
  cycle: (id: number) => get<PerfCycle & {
    kpis: { id: number; name: string; description: string | null; weight_pct: number }[]
    reviews: ReviewRow[]; rating_distribution: Record<string, number>
  }>(`/performance/cycles/${id}`),
  launch: (id: number) => post<{ created: number }>(`/performance/cycles/${id}/launch`),
  close: (id: number) => post(`/performance/cycles/${id}/close`),
  review: (id: number) => get<Review>(`/performance/reviews/${id}`),
  updateReview: (id: number, b: unknown) => put<Review>(`/performance/reviews/${id}`, b),
}

// ─── Compensation ────────────────────────────────────────────────────────
export interface Budget {
  total_budget: number; approved_cost: number; projected_cost: number; remaining: number
  utilization_pct: number | null; projected_utilization_pct: number | null
}
export interface CompCycle {
  id: number; name: string; year: number; status: string; total_budget: number; start_date: string
  end_date: string; plan_count: number; approved_count: number; budget: Budget
}
export interface CompPlan {
  id: number; employee_id: number; employee_name: string; employee_code: string; department: string | null
  current_salary: number; performance_score: number | null; system_recommended_pct: number | null
  manager_recommended_pct: number | null; manager_notes: string | null; final_increment_pct: number | null
  final_new_salary: number | null; bonus_amount: number | null; status: string; rejection_reason: string | null
  effective_pct: number; annual_cost: number
}
export interface CompRule { id: number; name: string; min_score: number; max_score: number; recommended_increment_pct: number }

export const compensationApi = {
  rules: () => get<CompRule[]>('/compensation/rules'),
  createRule: (b: Omit<CompRule, 'id'>) => post<CompRule>('/compensation/rules', b),
  cycles: () => get<CompCycle[]>('/compensation/cycles'),
  createCycle: (b: unknown) => post<CompCycle>('/compensation/cycles', b),
  cycle: (id: number) => get<CompCycle & { plans: CompPlan[] }>(`/compensation/cycles/${id}`),
  generate: (id: number) => post<{ created: number; without_review_score: number }>(`/compensation/cycles/${id}/generate`),
  apply: (id: number) => post<{ applied: number }>(`/compensation/cycles/${id}/apply`),
  updatePlan: (id: number, b: { manager_recommended_pct?: number; manager_notes?: string; bonus_amount?: number }) =>
    put<CompPlan>(`/compensation/plans/${id}`, b),
  submit: (id: number) => post<CompPlan & { approval_request_id: number | null }>(`/compensation/plans/${id}/submit`),
  decide: (id: number, approve: boolean, reason?: string) => post<CompPlan>(`/compensation/plans/${id}/decide`, { approve, reason }),
}

// ─── Workflows ───────────────────────────────────────────────────────────
export interface Stage { stage: number; role: string; label: string }
export interface WorkflowDef { id: number; name: string; entity_type: string; is_active: boolean; stages: Stage[]; created_at: string }
export interface ApprovalReq {
  id: number; entity_type: string; entity_id: number; entity_ref: string; current_stage: number; total_stages: number
  status: string; created_at: string; completed_at: string | null; workflow_name: string; stages: Stage[]
  current_stage_label: string | null; current_stage_role: string | null; can_act: boolean
  actions?: { stage_number: number; stage_label: string; action: string; comments: string | null; approver: string | null; created_at: string }[]
}

export const workflowApi = {
  roles: () => get<string[]>('/workflows/roles'),
  definitions: () => get<WorkflowDef[]>('/workflows/definitions'),
  createDefinition: (b: { name: string; entity_type: string; stages: { role: string; label: string }[] }) =>
    post<WorkflowDef>('/workflows/definitions', b),
  toggle: (id: number) => post<WorkflowDef>(`/workflows/definitions/${id}/toggle`),
  requests: (status: 'open' | 'closed' | 'all') => get<ApprovalReq[]>(`/workflows/requests?status=${status}`),
  request: (id: number) => get<ApprovalReq>(`/workflows/requests/${id}`),
  act: (id: number, approve: boolean, comments: string) => post<ApprovalReq>(`/workflows/requests/${id}/action`, { approve, comments }),
}

// ─── QA ──────────────────────────────────────────────────────────────────
export interface TestPlan {
  id: number; name: string; module: string; description: string | null; version: string
  case_count: number; status_counts: Record<string, number>; pass_rate: number | null
}
export interface TestCase {
  id: number; plan_id: number; case_id: string; title: string; test_type: string; preconditions: string | null
  test_steps: string; expected_result: string; module: string | null; priority: string
  last_status: string; last_executed_at: string | null; execution_count: number
}
export interface Defect {
  id: number; defect_id: string; title: string; description: string; steps_to_reproduce: string | null
  expected_behaviour: string | null; actual_behaviour: string | null; severity: string; priority: string
  status: string; module: string | null; test_case_id: number | null; test_case_ref: string | null
  created_at: string; next_statuses: string[]
}
export interface QASummary {
  plans: number; test_cases: number; executed: number; execution_coverage: number | null; pass_rate: number | null
  status_counts: Record<string, number>; cases_by_type: Record<string, number>; defects_total: number
  defects_open: number; open_by_severity: Record<string, number>; defects_by_status: Record<string, number>
}

export const qaApi = {
  summary: () => get<QASummary>('/qa/summary'),
  plans: () => get<TestPlan[]>('/qa/plans'),
  createPlan: (b: { name: string; module: string; description?: string }) => post<TestPlan>('/qa/plans', b),
  plan: (id: number) => get<TestPlan & { cases: TestCase[] }>(`/qa/plans/${id}`),
  createCase: (planId: number, b: unknown) => post<TestCase>(`/qa/plans/${planId}/cases`, b),
  testCase: (id: number) => get<TestCase & {
    plan_name: string; defects: Defect[]
    executions: { id: number; status: string; actual_result: string | null; notes: string | null; build_version: string | null; executed_at: string; executed_by: string | null }[]
  }>(`/qa/cases/${id}`),
  execute: (id: number, b: { status: string; actual_result?: string; notes?: string; build_version?: string }) =>
    post<TestCase>(`/qa/cases/${id}/execute`, b),
  defects: (status = '') => get<Defect[]>(`/qa/defects${status ? `?status=${status}` : ''}`),
  createDefect: (b: unknown) => post<Defect>('/qa/defects', b),
  moveDefect: (id: number, status: string, comment?: string) => put<Defect>(`/qa/defects/${id}`, { status, comment }),
}

// ─── Reports & audit ─────────────────────────────────────────────────────
export interface ReportMeta {
  id: string; title: string; category: string; description: string
  chart: { type: 'bar' | 'line'; x: string; y: string[] } | null
}
export interface ReportResult extends ReportMeta {
  sql: string; columns: string[]; rows: (string | number | null)[][]; row_count: number; execution_ms: number
}
export const reportsApi = {
  list: () => get<ReportMeta[]>('/reports'),
  run: (id: string) => get<ReportResult>(`/reports/${id}`),
}

export interface AuditEntry {
  id: number; user_email: string | null; action: string; entity_type: string; entity_id: number | null
  entity_ref: string | null; old_values: Record<string, unknown> | null; new_values: Record<string, unknown> | null
  created_at: string
}
export const auditApi = {
  list: (p: { page: number; entity_type?: string; action?: string; search?: string }) => {
    const q = new URLSearchParams({ page: String(p.page), page_size: '25' })
    if (p.entity_type) q.set('entity_type', p.entity_type)
    if (p.action) q.set('action', p.action)
    if (p.search) q.set('search', p.search)
    return get<{ items: AuditEntry[]; total: number; page: number; total_pages: number }>(`/audit?${q}`)
  },
  filters: () => get<{ entity_types: string[]; actions: string[] }>('/audit/filters'),
}
