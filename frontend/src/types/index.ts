// ─── Auth Types ───────────────────────────────────────────────────
export interface TokenResponse {
  access_token: string
  token_type: string
  user_id: number
  email: string
  full_name: string
  role: UserRole
  company_id: number | null
  company_name: string | null
}

export type UserRole =
  | 'platform_admin'
  | 'company_admin'
  | 'hr_manager'
  | 'department_manager'
  | 'finance_manager'
  | 'employee'

export interface AuthUser {
  id: number
  email: string
  full_name: string
  role: UserRole
  company_id: number | null
  company_name: string | null
}

// ─── Dashboard Types ──────────────────────────────────────────────
export interface DashboardMetrics {
  total_employees: number
  total_companies: number | null
  monthly_payroll: number | null
  budget_utilization_pct: number | null
  avg_performance_score: number | null
  pending_approvals: number
  qa_pass_pct: number | null
  open_defects: number
  department_breakdown: { name: string; count: number }[]
  recent_employees: RecentEmployee[]
}

export interface RecentEmployee {
  id: number
  name: string
  department: string
  joining_date: string
  status: string
}

// ─── Employee Types ───────────────────────────────────────────────
export type EmploymentStatus = 'active' | 'inactive' | 'terminated' | 'on_leave'
export type EmploymentType = 'full_time' | 'part_time' | 'contract' | 'intern'
export type Gender = 'male' | 'female' | 'other' | 'prefer_not_to_say'

export interface Employee {
  id: number
  employee_code: string
  first_name: string
  last_name: string
  full_name: string
  email: string
  phone: string | null
  gender: Gender | null
  date_of_birth: string | null
  department_id: number
  department_name: string | null
  designation_id: number | null
  designation_name: string | null
  manager_id: number | null
  manager_name: string | null
  joining_date: string
  employment_type: EmploymentType
  status: EmploymentStatus
  gross_ctc: number | null
  address: string | null
}

export interface EmployeeCreate {
  first_name: string
  last_name: string
  email: string
  phone?: string
  gender?: Gender
  date_of_birth?: string
  department_id: number
  designation_id?: number
  manager_id?: number
  joining_date: string
  employment_type: EmploymentType
  gross_ctc?: number
  address?: string
  create_login?: boolean
  login_password?: string
}

// ─── Department Types ─────────────────────────────────────────────
export interface Department {
  id: number
  name: string
  code: string
  company_id: number
  employee_count?: number
}

export interface Designation {
  id: number
  name: string
  level: number
  department_id: number
  company_id: number
}

// ─── Paginated ────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
