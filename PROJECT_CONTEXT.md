# HRMS Platform — Project Context

## Purpose
Enterprise HR & Compensation Management SaaS platform built as a portfolio project
targeting an **Implementation Analyst / QA / SQL Reporting** role.

Demonstrates: multi-tenant architecture, configurable business logic, SQL proficiency,
QA methodology, and enterprise-grade implementation documentation.

---

## Architecture

| Layer | Stack |
|-------|-------|
| Frontend | React 18 + Vite 5 + TypeScript + Tailwind CSS + Recharts |
| Backend | Python 3.13 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| Database | SQLite (local dev) → PostgreSQL via DATABASE_URL (production) |
| Auth | JWT (python-jose) + bcrypt, 8-hour tokens, role embedded |
| Migrations | Alembic (configured; run `alembic upgrade head`) |

---

## Multi-Tenancy Model
- Every table (except Platform-level) has a `company_id` column
- Backend extracts `company_id` from JWT — never trusts frontend
- All queries filter by `company_id` at the **service layer**
- Platform Admin: company_id = NULL, sees all companies

---

## Roles (descending privilege)
1. `PLATFORM_ADMIN` — full access, all companies
2. `COMPANY_ADMIN` — full access within own company
3. `HR_MANAGER` — employee/salary/performance management
4. `DEPARTMENT_MANAGER` — own dept employees + performance reviews
5. `FINANCE_MANAGER` — payroll + compensation approval
6. `EMPLOYEE` — read-only own records

---

## Seed Data (pre-loaded)
| Credential | Email | Password |
|-----------|-------|----------|
| Platform Admin | admin@hrmsplatform.com | Admin@1234 |
| ABC Tech Admin | admin@abctech.com | Admin@1234 |
| ABC Tech HR | hr.manager@abct.com | Admin@1234 |
| XYZ Solutions Admin | admin@xyzsolutions.com | Admin@1234 |
| XYZ Solutions HR | hr.manager@xyzs.com | Admin@1234 |

Each company has 50 employees across 5 departments.

---

## Database Tables (27 total)
```
companies, users
departments, designations, employees
salary_components, salary_structures, salary_structure_components, employee_salary_assignments
performance_cycles, kpis, performance_reviews, kpi_scores
compensation_cycles, compensation_rules, compensation_plans
payroll_runs, payslips, payslip_items
workflow_definitions, approval_requests, approval_actions
test_plans, test_cases, test_executions, defects
audit_logs
```

---

## Key Business Logic

### Salary Calculation (Payslip)
```
Gross CTC = monthly gross
Basic      = Gross × 50%
HRA        = Basic × 50%   (metro city — FHEF exempt)
Transport  = ₹1,600 (fixed)
Special    = Gross − Basic − HRA − Transport
PF (ded)   = Basic × 12%  (employee contribution)
PT (ded)   = ₹200 (fixed)
TDS (ded)  = Gross × 5%   (illustrative)
Net        = Total Earnings − Total Deductions
```

### Performance Score (Weighted KPI)
```
Final Score = Σ (KPI_Score × KPI_Weight%)
Weights must sum to exactly 100% (DB CheckConstraint enforced)
```

### Compensation Increment Bands
| Score Range | Increment |
|-------------|-----------|
| 90–100 | 15% |
| 80–89.99 | 12% |
| 70–79.99 | 8% |
| 60–69.99 | 5% |
| < 60 | 3% |

### Approval Workflow
JSON-configured stages per entity type. Example:
```json
[
  {"stage": 1, "role": "department_manager", "label": "Manager Review"},
  {"stage": 2, "role": "hr_manager", "label": "HR Review"},
  {"stage": 3, "role": "finance_manager", "label": "Finance Approval"}
]
```

---

## QA Test Suite
25 test cases seeded per company covering:
- Positive cases (happy path)
- Negative cases (validation errors, duplicates)
- Boundary cases (exact threshold values, pagination edges)
- Security cases (cross-tenant access, unauthorized endpoints, SQL injection)
- Calculation verification (formula accuracy)

---

## Development Setup

### Backend
```bash
cd backend
pip install -r requirements.txt --break-system-packages
cp .env.example .env
# Edit .env — set SECRET_KEY
python scripts/seed_data.py
uvicorn app.main:app --reload
# API docs: http://localhost:8000/api/docs
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
# App: http://localhost:5173
```

---

## Deployment

| Service | Platform | Notes |
|---------|----------|-------|
| Backend | Render / Railway | Set DATABASE_URL to PostgreSQL |
| Frontend | Vercel | Set VITE_API_URL to backend URL |
| Database | Supabase / Railway | PostgreSQL |

---

## Implementation Status

### ✅ Phase 1 — Core Backend (Complete)
- 27-table schema, all models with relationships
- JWT auth, role-based access control
- Multi-tenant isolation (company_id enforcement)
- Employee CRUD with pagination/filtering
- Department/Designation management
- Dashboard metrics API (all from real DB queries)
- Audit logging

### ✅ Phase 2 — Seed Data (Complete)
- 2 companies, 100 employees
- Salary structures with component breakdown
- Performance cycles + KPI scores
- Compensation plans with increment rules
- Payroll run with payslips + line items
- Approval workflow definitions
- 25 QA test cases + executions + defects

### ✅ Phase 3 — Frontend (Complete)
- React 18 + Vite 5 + TypeScript + Tailwind CSS
- Login page with demo quick-login
- Dark sidebar navigation with role-aware menu
- Dashboard with KPI cards + Recharts visualizations
- Employee management: list, search, filter, paginate
- Add Employee modal with designation cascade
- Employee detail page

### 🔜 Phase 4 — Remaining Modules
- Salary structure management UI
- Performance appraisal workflow
- Compensation planning with budget tracking
- Payroll processing UI
- Approval workflow UI with stage tracking
- QA management dashboard
- SQL reports with Excel/PDF export
- Alembic migrations
- Pytest suite (auth, CRUD, tenant isolation)
