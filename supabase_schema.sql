-- ============================================================
-- HRMS Platform — Supabase PostgreSQL Schema
-- Run this in Supabase SQL Editor (supabase.com → SQL Editor)
-- ============================================================

-- Enable UUID extension (optional, for future use)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- ENUMS
-- ============================================================
DO $$ BEGIN
  CREATE TYPE userrole AS ENUM ('PLATFORM_ADMIN','COMPANY_ADMIN','HR_MANAGER','DEPARTMENT_MANAGER','FINANCE_MANAGER','EMPLOYEE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE gender AS ENUM ('MALE','FEMALE','OTHER','PREFER_NOT_TO_SAY');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE employmenttype AS ENUM ('FULL_TIME','PART_TIME','CONTRACT','INTERN');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE employmentstatus AS ENUM ('ACTIVE','INACTIVE','RESIGNED','TERMINATED','ON_LEAVE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE componenttype AS ENUM ('EARNING','DEDUCTION');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE calculationtype AS ENUM ('FIXED','PERCENTAGE_OF_BASIC','PERCENTAGE_OF_GROSS');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE payrollstatus AS ENUM ('DRAFT','PROCESSING','PENDING_APPROVAL','APPROVED','PAID','CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE reviewstatus AS ENUM ('DRAFT','SELF_REVIEW','MANAGER_REVIEW','COMPLETED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE cyclestatus AS ENUM ('DRAFT','ACTIVE','COMPLETED','CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE planstatus AS ENUM ('PENDING','MANAGER_REVIEW','HR_REVIEW','FINANCE_REVIEW','APPROVED','REJECTED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE workflowentitytype AS ENUM ('SALARY_INCREMENT','PAYROLL_APPROVAL','COMPENSATION_PLAN','EMPLOYEE_CREATION','LEAVE_REQUEST');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE requeststatus AS ENUM ('PENDING','IN_PROGRESS','APPROVED','REJECTED','CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE actiontype AS ENUM ('APPROVED','REJECTED','MODIFICATION_REQUESTED','FORWARDED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE testtype AS ENUM ('POSITIVE','NEGATIVE','BOUNDARY','SECURITY','REGRESSION');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE defectseverity AS ENUM ('CRITICAL','HIGH','MEDIUM','LOW');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE defectpriority AS ENUM ('P1','P2','P3','P4');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE defectstatus AS ENUM ('OPEN','IN_PROGRESS','FIXED','VERIFIED','CLOSED','REOPENED','WONT_FIX');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ============================================================
-- TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    industry VARCHAR(100),
    address TEXT,
    phone VARCHAR(20),
    email VARCHAR(200),
    website VARCHAR(200),
    logo_url VARCHAR(500),
    subscription_plan VARCHAR(50) DEFAULT 'BASIC',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_companies_code ON companies(code);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    email VARCHAR(200) NOT NULL UNIQUE,
    hashed_password VARCHAR(500) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    role userrole NOT NULL DEFAULT 'EMPLOYEE',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_company_id ON users(company_id);

CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    UNIQUE(company_id, code)
);
CREATE INDEX IF NOT EXISTS ix_departments_company_id ON departments(company_id);

CREATE TABLE IF NOT EXISTS designations (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    department_id INTEGER NOT NULL REFERENCES departments(id),
    name VARCHAR(100) NOT NULL,
    level INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_designations_company_id ON designations(company_id);
CREATE INDEX IF NOT EXISTS ix_designations_department_id ON designations(department_id);

CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    user_id INTEGER UNIQUE REFERENCES users(id),
    department_id INTEGER NOT NULL REFERENCES departments(id),
    designation_id INTEGER REFERENCES designations(id),
    manager_id INTEGER REFERENCES employees(id),
    employee_code VARCHAR(20) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(200) NOT NULL,
    phone VARCHAR(20),
    gender gender,
    date_of_birth DATE,
    address TEXT,
    emergency_contact VARCHAR(200),
    joining_date DATE NOT NULL,
    leaving_date DATE,
    employment_type employmenttype DEFAULT 'FULL_TIME',
    status employmentstatus NOT NULL DEFAULT 'ACTIVE',
    gross_ctc NUMERIC(12,2),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    UNIQUE(company_id, employee_code)
);
CREATE INDEX IF NOT EXISTS ix_employees_company_id ON employees(company_id);
CREATE INDEX IF NOT EXISTS ix_employees_department_id ON employees(department_id);

CREATE TABLE IF NOT EXISTS salary_components (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) NOT NULL,
    component_type componenttype NOT NULL,
    calculation_type calculationtype NOT NULL,
    is_taxable BOOLEAN DEFAULT TRUE,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, code)
);
CREATE INDEX IF NOT EXISTS ix_salary_components_company_id ON salary_components(company_id);

CREATE TABLE IF NOT EXISTS salary_structures (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name VARCHAR(200) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    effective_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by_id INTEGER REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS ix_salary_structures_company_id ON salary_structures(company_id);

CREATE TABLE IF NOT EXISTS salary_structure_components (
    id SERIAL PRIMARY KEY,
    structure_id INTEGER NOT NULL REFERENCES salary_structures(id),
    component_id INTEGER NOT NULL REFERENCES salary_components(id),
    value NUMERIC(8,4) NOT NULL CHECK (value >= 0),
    sequence INTEGER DEFAULT 1,
    UNIQUE(structure_id, component_id)
);
CREATE INDEX IF NOT EXISTS ix_salary_structure_components_structure_id ON salary_structure_components(structure_id);

CREATE TABLE IF NOT EXISTS employee_salary_assignments (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    structure_id INTEGER NOT NULL REFERENCES salary_structures(id),
    gross_ctc NUMERIC(12,2) NOT NULL,
    effective_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by_id INTEGER REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS ix_employee_salary_assignments_employee_id ON employee_salary_assignments(employee_id);

CREATE TABLE IF NOT EXISTS payroll_runs (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    status payrollstatus DEFAULT 'DRAFT',
    total_employees INTEGER DEFAULT 0,
    total_gross NUMERIC(15,2) DEFAULT 0,
    total_deductions NUMERIC(15,2) DEFAULT 0,
    total_net NUMERIC(15,2) DEFAULT 0,
    total_bonus NUMERIC(15,2) DEFAULT 0,
    processed_by_id INTEGER REFERENCES users(id),
    processed_at TIMESTAMP,
    approved_by_id INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, month, year)
);
CREATE INDEX IF NOT EXISTS ix_payroll_runs_company_id ON payroll_runs(company_id);

CREATE TABLE IF NOT EXISTS payslips (
    id SERIAL PRIMARY KEY,
    payroll_run_id INTEGER NOT NULL REFERENCES payroll_runs(id),
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    gross_salary NUMERIC(12,2) NOT NULL,
    total_earnings NUMERIC(12,2) NOT NULL,
    total_deductions NUMERIC(12,2) NOT NULL,
    net_salary NUMERIC(12,2) NOT NULL,
    bonus NUMERIC(12,2) DEFAULT 0,
    unpaid_leave_days NUMERIC(5,2) DEFAULT 0,
    unpaid_leave_deduction NUMERIC(12,2) DEFAULT 0,
    working_days INTEGER DEFAULT 26,
    paid_days NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(payroll_run_id, employee_id)
);
CREATE INDEX IF NOT EXISTS ix_payslips_payroll_run_id ON payslips(payroll_run_id);
CREATE INDEX IF NOT EXISTS ix_payslips_employee_id ON payslips(employee_id);

CREATE TABLE IF NOT EXISTS performance_cycles (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name VARCHAR(200) NOT NULL,
    year INTEGER NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    status reviewstatus DEFAULT 'DRAFT',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_performance_cycles_company_id ON performance_cycles(company_id);

CREATE TABLE IF NOT EXISTS kpis (
    id SERIAL PRIMARY KEY,
    cycle_id INTEGER NOT NULL REFERENCES performance_cycles(id),
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    weight_pct NUMERIC(5,2) NOT NULL CHECK (weight_pct > 0 AND weight_pct <= 100),
    sequence INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS ix_kpis_cycle_id ON kpis(cycle_id);
CREATE INDEX IF NOT EXISTS ix_kpis_company_id ON kpis(company_id);

CREATE TABLE IF NOT EXISTS performance_reviews (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    cycle_id INTEGER NOT NULL REFERENCES performance_cycles(id),
    reviewer_id INTEGER REFERENCES users(id),
    self_overall_score NUMERIC(5,2),
    manager_overall_score NUMERIC(5,2),
    final_score NUMERIC(5,2),
    self_comments TEXT,
    manager_comments TEXT,
    status reviewstatus DEFAULT 'DRAFT',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_performance_reviews_employee_id ON performance_reviews(employee_id);
CREATE INDEX IF NOT EXISTS ix_performance_reviews_cycle_id ON performance_reviews(cycle_id);

CREATE TABLE IF NOT EXISTS compensation_rules (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name VARCHAR(200) NOT NULL,
    min_score NUMERIC(5,2) NOT NULL,
    max_score NUMERIC(5,2) NOT NULL,
    recommended_increment_pct NUMERIC(5,2) NOT NULL CHECK (recommended_increment_pct >= 0),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    CHECK (min_score < max_score),
    CHECK (min_score >= 0 AND max_score <= 100)
);
CREATE INDEX IF NOT EXISTS ix_compensation_rules_company_id ON compensation_rules(company_id);

CREATE TABLE IF NOT EXISTS compensation_cycles (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name VARCHAR(200) NOT NULL,
    year INTEGER NOT NULL,
    status cyclestatus DEFAULT 'DRAFT',
    total_budget NUMERIC(15,2),
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by_id INTEGER REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS ix_compensation_cycles_company_id ON compensation_cycles(company_id);

CREATE TABLE IF NOT EXISTS compensation_plans (
    id SERIAL PRIMARY KEY,
    cycle_id INTEGER NOT NULL REFERENCES compensation_cycles(id),
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    current_salary NUMERIC(12,2) NOT NULL,
    performance_score NUMERIC(5,2),
    system_recommended_pct NUMERIC(5,2),
    system_recommended_salary NUMERIC(12,2),
    manager_recommended_pct NUMERIC(5,2),
    manager_recommended_salary NUMERIC(12,2),
    manager_notes TEXT,
    manager_reviewed_by INTEGER REFERENCES users(id),
    manager_reviewed_at TIMESTAMP,
    final_increment_pct NUMERIC(5,2),
    final_new_salary NUMERIC(12,2),
    bonus_amount NUMERIC(12,2),
    status planstatus DEFAULT 'PENDING',
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_compensation_plans_cycle_id ON compensation_plans(cycle_id);
CREATE INDEX IF NOT EXISTS ix_compensation_plans_employee_id ON compensation_plans(employee_id);

CREATE TABLE IF NOT EXISTS workflow_definitions (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name VARCHAR(200) NOT NULL,
    entity_type workflowentitytype NOT NULL,
    stages_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by_id INTEGER REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS ix_workflow_definitions_company_id ON workflow_definitions(company_id);

CREATE TABLE IF NOT EXISTS approval_requests (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    workflow_id INTEGER NOT NULL REFERENCES workflow_definitions(id),
    entity_type workflowentitytype NOT NULL,
    entity_id INTEGER NOT NULL,
    entity_ref VARCHAR(200),
    current_stage INTEGER DEFAULT 1,
    total_stages INTEGER NOT NULL,
    status requeststatus DEFAULT 'PENDING',
    created_by_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_approval_requests_company_id ON approval_requests(company_id);

CREATE TABLE IF NOT EXISTS approval_actions (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES approval_requests(id),
    stage_number INTEGER NOT NULL,
    stage_label VARCHAR(100),
    approver_id INTEGER NOT NULL REFERENCES users(id),
    action actiontype NOT NULL,
    comments TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_approval_actions_request_id ON approval_actions(request_id);

CREATE TABLE IF NOT EXISTS test_plans (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name VARCHAR(200) NOT NULL,
    module VARCHAR(100) NOT NULL,
    description TEXT,
    version VARCHAR(20) DEFAULT '1.0',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by_id INTEGER REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS ix_test_plans_company_id ON test_plans(company_id);

CREATE TABLE IF NOT EXISTS test_cases (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES test_plans(id),
    case_id VARCHAR(20) NOT NULL,
    title VARCHAR(500) NOT NULL,
    test_type testtype NOT NULL,
    preconditions TEXT,
    test_steps TEXT NOT NULL,
    expected_result TEXT NOT NULL,
    module VARCHAR(100),
    priority VARCHAR(20) DEFAULT 'MEDIUM',
    is_automated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_test_cases_plan_id ON test_cases(plan_id);

CREATE TABLE IF NOT EXISTS defects (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    test_case_id INTEGER REFERENCES test_cases(id),
    defect_id VARCHAR(20) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    steps_to_reproduce TEXT,
    expected_behaviour TEXT,
    actual_behaviour TEXT,
    severity defectseverity NOT NULL,
    priority defectpriority NOT NULL,
    status defectstatus DEFAULT 'OPEN',
    module VARCHAR(100),
    reported_by_id INTEGER NOT NULL REFERENCES users(id),
    assigned_to_id INTEGER REFERENCES users(id),
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_defects_company_id ON defects(company_id);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    user_id INTEGER REFERENCES users(id),
    user_email VARCHAR(200),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id INTEGER,
    entity_ref VARCHAR(200),
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_audit_logs_company_id ON audit_logs(company_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS ix_audit_logs_entity_type ON audit_logs(entity_type);

-- ============================================================
-- SEED DATA — Demo company + admin user
-- Password: Admin@123 (bcrypt hashed)
-- ============================================================
INSERT INTO companies (name, code, industry, subscription_plan, is_active, created_at)
VALUES ('ZeroCode HR Demo', 'ZCDEMO', 'Technology', 'ENTERPRISE', TRUE, NOW())
ON CONFLICT (code) DO NOTHING;

INSERT INTO users (company_id, email, hashed_password, full_name, role, is_active, created_at)
SELECT
    c.id,
    'admin@zerocodehr.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TiGKfXFmvdGhYt5IXNJ0Y.vgLw2',
    'Admin User',
    'COMPANY_ADMIN',
    TRUE,
    NOW()
FROM companies c WHERE c.code = 'ZCDEMO'
ON CONFLICT (email) DO NOTHING;

-- ============================================================
-- Done! Connection string is in Supabase → Settings → Database
-- ============================================================
