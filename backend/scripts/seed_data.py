"""
Seed Data Script
================
Creates:
  - 1 Platform Admin
  - 2 Companies (ABC Technologies, XYZ Solutions)
  - 5 Departments + 3 Designations each per company
  - ~50 Employees per company (100 total)
  - Performance cycles + reviews
  - Compensation cycles + rules
  - Sample payroll run
  - QA test plans + 25 test cases + executions + defects
  - Approval workflows
  - Audit log entries

Run: python scripts/seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import random
from faker import Faker

from app.core.database import SessionLocal, create_tables
from app.core.security import hash_password
from app.models.company import Company
from app.models.user import User, UserRole
from app.models.employee import (Employee, Department, Designation,
                                  EmploymentStatus, EmploymentType, Gender)
from app.models.salary import (SalaryComponent, SalaryStructure,
                                SalaryStructureComponent, EmployeeSalaryAssignment,
                                ComponentType, CalculationType)
from app.models.compensation import (CompensationCycle, CompensationPlan,
                                     CompensationRule, CycleStatus, PlanStatus)
from app.models.performance import (PerformanceCycle, KPI, PerformanceReview,
                                    KPIScore, ReviewStatus)
from app.models.payroll import PayrollRun, Payslip, PayslipItem, PayrollStatus
from app.models.workflow import (WorkflowDefinition, ApprovalRequest, ApprovalAction,
                                 WorkflowEntityType, RequestStatus, ActionType)
from app.models.qa import (TestPlan, TestCase, TestExecution, Defect,
                           TestType, ExecutionStatus, DefectSeverity, DefectPriority, DefectStatus)
from app.models.audit import AuditLog

fake = Faker("en_IN")
random.seed(42)
Faker.seed(42)


def run():
    create_tables()
    db = SessionLocal()

    try:
        # --- PLATFORM ADMIN ---
        platform_admin = User(
            email="admin@hrmsplatform.com",
            hashed_password=hash_password("Admin@1234"),
            full_name="Platform Administrator",
            role=UserRole.PLATFORM_ADMIN,
            company_id=None,
        )
        db.add(platform_admin)
        db.flush()
        print("✅ Platform admin created: admin@hrmsplatform.com / Admin@1234")

        # --- COMPANIES ---
        companies_data = [
            {
                "name": "ABC Technologies Pvt Ltd",
                "code": "ABCT",
                "industry": "Information Technology",
                "address": "123 Tech Park, Whitefield, Bengaluru, Karnataka 560066",
                "phone": "+91-80-12345678",
                "email": "hr@abctech.com",
                "admin_name": "Priya Sharma",
                "admin_email": "admin@abctech.com",
                "admin_password": "Admin@1234",
                "departments": [
                    {"name": "Engineering", "code": "ENG", "salary_range": (35000, 90000)},
                    {"name": "Sales & Marketing", "code": "SALES", "salary_range": (25000, 65000)},
                    {"name": "Human Resources", "code": "HR", "salary_range": (28000, 55000)},
                    {"name": "Finance & Accounts", "code": "FIN", "salary_range": (30000, 70000)},
                    {"name": "Operations", "code": "OPS", "salary_range": (22000, 48000)},
                ],
            },
            {
                "name": "XYZ Solutions Ltd",
                "code": "XYZS",
                "industry": "Management Consulting",
                "address": "456 Business Hub, Andheri East, Mumbai, Maharashtra 400069",
                "phone": "+91-22-98765432",
                "email": "hr@xyzsolutions.com",
                "admin_name": "Rahul Mehta",
                "admin_email": "admin@xyzsolutions.com",
                "admin_password": "Admin@1234",
                "departments": [
                    {"name": "Consulting", "code": "CONS", "salary_range": (40000, 100000)},
                    {"name": "Data Analytics", "code": "DATA", "salary_range": (35000, 85000)},
                    {"name": "Business Development", "code": "BD", "salary_range": (30000, 70000)},
                    {"name": "Administration", "code": "ADMIN", "salary_range": (22000, 45000)},
                    {"name": "Customer Support", "code": "SUPP", "salary_range": (20000, 40000)},
                ],
            },
        ]

        DESIGNATIONS_BY_DEPT = {
            "ENG": ["Software Engineer", "Senior Software Engineer", "Tech Lead"],
            "SALES": ["Sales Executive", "Senior Sales Executive", "Sales Manager"],
            "HR": ["HR Executive", "Senior HR Executive", "HR Manager"],
            "FIN": ["Accounts Executive", "Senior Accountant", "Finance Manager"],
            "OPS": ["Operations Executive", "Senior Operations Exec", "Operations Manager"],
            "CONS": ["Consultant", "Senior Consultant", "Principal Consultant"],
            "DATA": ["Data Analyst", "Senior Data Analyst", "Lead Analyst"],
            "BD": ["BD Executive", "Senior BD Executive", "BD Manager"],
            "ADMIN": ["Admin Executive", "Senior Admin Executive", "Office Manager"],
            "SUPP": ["Support Executive", "Senior Support Exec", "Support Manager"],
        }

        all_company_data = []

        for co_data in companies_data:
            company = Company(
                name=co_data["name"],
                code=co_data["code"],
                industry=co_data["industry"],
                address=co_data["address"],
                phone=co_data["phone"],
                email=co_data["email"],
            )
            db.add(company)
            db.flush()

            # Company admin user
            admin_user = User(
                company_id=company.id,
                email=co_data["admin_email"],
                hashed_password=hash_password(co_data["admin_password"]),
                full_name=co_data["admin_name"],
                role=UserRole.COMPANY_ADMIN,
            )
            db.add(admin_user)
            db.flush()

            # --- SALARY COMPONENTS ---
            components = [
                SalaryComponent(company_id=company.id, name="Basic Salary", code="BASIC",
                                component_type=ComponentType.EARNING,
                                calculation_type=CalculationType.PERCENTAGE_OF_GROSS,
                                is_taxable=True, description="Base salary component"),
                SalaryComponent(company_id=company.id, name="House Rent Allowance", code="HRA",
                                component_type=ComponentType.EARNING,
                                calculation_type=CalculationType.PERCENTAGE_OF_BASIC,
                                is_taxable=False, description="HRA — 50% of basic in metro cities"),
                SalaryComponent(company_id=company.id, name="Special Allowance", code="SPEC_ALL",
                                component_type=ComponentType.EARNING,
                                calculation_type=CalculationType.PERCENTAGE_OF_GROSS,
                                is_taxable=True),
                SalaryComponent(company_id=company.id, name="Transport Allowance", code="TRANS",
                                component_type=ComponentType.EARNING,
                                calculation_type=CalculationType.FIXED,
                                is_taxable=False, description="Fixed ₹1,600/month"),
                SalaryComponent(company_id=company.id, name="Provident Fund", code="PF",
                                component_type=ComponentType.DEDUCTION,
                                calculation_type=CalculationType.PERCENTAGE_OF_BASIC,
                                is_taxable=False, description="12% of basic — employee contribution"),
                SalaryComponent(company_id=company.id, name="Professional Tax", code="PT",
                                component_type=ComponentType.DEDUCTION,
                                calculation_type=CalculationType.FIXED,
                                is_taxable=False, description="Fixed ₹200/month"),
                SalaryComponent(company_id=company.id, name="TDS", code="TDS",
                                component_type=ComponentType.DEDUCTION,
                                calculation_type=CalculationType.PERCENTAGE_OF_GROSS,
                                is_taxable=False, description="Tax Deducted at Source — illustrative"),
            ]
            for comp in components:
                db.add(comp)
            db.flush()
            comp_map = {c.code: c for c in components}

            # --- SALARY STRUCTURE ---
            structure = SalaryStructure(
                company_id=company.id,
                name="Standard CTC Structure",
                version=1,
                description="Standard salary structure for all employees",
                is_active=True,
                effective_date=datetime(2024, 4, 1, tzinfo=timezone.utc),
            )
            db.add(structure)
            db.flush()

            struct_components = [
                SalaryStructureComponent(structure_id=structure.id, component_id=comp_map["BASIC"].id,
                                         value=Decimal("50.00"), sequence=1),
                SalaryStructureComponent(structure_id=structure.id, component_id=comp_map["HRA"].id,
                                         value=Decimal("50.00"), sequence=2),  # 50% of basic
                SalaryStructureComponent(structure_id=structure.id, component_id=comp_map["SPEC_ALL"].id,
                                         value=Decimal("30.00"), sequence=3),
                SalaryStructureComponent(structure_id=structure.id, component_id=comp_map["TRANS"].id,
                                         value=Decimal("1600.00"), sequence=4),
                SalaryStructureComponent(structure_id=structure.id, component_id=comp_map["PF"].id,
                                         value=Decimal("12.00"), sequence=5),
                SalaryStructureComponent(structure_id=structure.id, component_id=comp_map["PT"].id,
                                         value=Decimal("200.00"), sequence=6),
                SalaryStructureComponent(structure_id=structure.id, component_id=comp_map["TDS"].id,
                                         value=Decimal("5.00"), sequence=7),
            ]
            for sc in struct_components:
                db.add(sc)
            db.flush()

            # --- DEPARTMENTS + DESIGNATIONS ---
            departments = []
            for dept_data in co_data["departments"]:
                dept = Department(
                    company_id=company.id,
                    name=dept_data["name"],
                    code=dept_data["code"],
                )
                db.add(dept)
                db.flush()

                desig_names = DESIGNATIONS_BY_DEPT.get(dept_data["code"], ["Executive", "Senior Executive", "Manager"])
                designations = []
                for level, dname in enumerate(desig_names, start=1):
                    desig = Designation(company_id=company.id, department_id=dept.id,
                                        name=dname, level=level)
                    db.add(desig)
                    db.flush()
                    designations.append(desig)
                departments.append((dept, designations, dept_data["salary_range"]))

            # --- USERS (HR, Finance, Dept Managers) ---
            hr_user = User(
                company_id=company.id,
                email=f"hr.manager@{company.code.lower()}.com",
                hashed_password=hash_password("Admin@1234"),
                full_name=f"{fake.first_name()} {fake.last_name()}",
                role=UserRole.HR_MANAGER,
            )
            finance_user = User(
                company_id=company.id,
                email=f"finance@{company.code.lower()}.com",
                hashed_password=hash_password("Admin@1234"),
                full_name=f"{fake.first_name()} {fake.last_name()}",
                role=UserRole.FINANCE_MANAGER,
            )
            db.add(hr_user)
            db.add(finance_user)
            db.flush()

            # --- EMPLOYEES (10 per department = 50 total per company) ---
            employees_created = []
            emp_counter = 0
            for dept, designations, salary_range in departments:
                dept_managers = []
                for i in range(10):
                    emp_counter += 1
                    gender = random.choice([Gender.MALE, Gender.FEMALE])
                    first = fake.first_name_male() if gender == Gender.MALE else fake.first_name_female()
                    last = fake.last_name()
                    joining = date(
                        random.randint(2020, 2024),
                        random.randint(1, 12),
                        random.randint(1, 28),
                    )
                    ctc = random.randint(salary_range[0] // 1000, salary_range[1] // 1000) * 1000
                    desig = designations[0] if i < 7 else (designations[1] if i < 9 else designations[2])

                    emp = Employee(
                        company_id=company.id,
                        employee_code=f"{company.code}-{emp_counter:04d}",
                        first_name=first,
                        last_name=last,
                        email=f"{first.lower()}.{last.lower()}{emp_counter}@{company.code.lower()}.com",
                        phone=fake.phone_number()[:15],
                        gender=gender,
                        date_of_birth=date(random.randint(1985, 2000), random.randint(1, 12), random.randint(1, 28)),
                        address=fake.address()[:200],
                        department_id=dept.id,
                        designation_id=desig.id,
                        joining_date=joining,
                        employment_type=EmploymentType.FULL_TIME,
                        status=EmploymentStatus.ACTIVE,
                        gross_ctc=Decimal(str(ctc)),
                    )
                    db.add(emp)
                    db.flush()

                    # Salary assignment
                    assignment = EmployeeSalaryAssignment(
                        employee_id=emp.id,
                        structure_id=structure.id,
                        gross_ctc=Decimal(str(ctc)),
                        effective_date=datetime(joining.year, joining.month, joining.day, tzinfo=timezone.utc),
                    )
                    db.add(assignment)

                    employees_created.append(emp)
                    if i == 9:
                        dept_managers.append(emp)

            # Assign managers (last employee in dept is manager)
            for idx, emp in enumerate(employees_created):
                dept_id = emp.department_id
                dept_manager = next(
                    (m for m in employees_created if m.department_id == dept_id and m != emp
                     and m.designation_id and m.designation and m.designation.level >= 2), None
                )
                if dept_manager and emp.id != dept_manager.id:
                    emp.manager_id = dept_manager.id

            db.flush()

            # --- PERFORMANCE CYCLE ---
            perf_cycle = PerformanceCycle(
                company_id=company.id,
                name="Annual Review FY 2024-25",
                year=2024,
                start_date=datetime(2024, 4, 1, tzinfo=timezone.utc),
                end_date=datetime(2025, 3, 31, tzinfo=timezone.utc),
                status=ReviewStatus.COMPLETED,
            )
            db.add(perf_cycle)
            db.flush()

            kpi_defs = [
                ("Technical Skills / Core Competency", Decimal("35.00")),
                ("Productivity & Goal Achievement", Decimal("30.00")),
                ("Communication & Teamwork", Decimal("20.00")),
                ("Attendance & Punctuality", Decimal("15.00")),
            ]
            kpis = []
            for seq, (kname, weight) in enumerate(kpi_defs, start=1):
                kpi = KPI(cycle_id=perf_cycle.id, company_id=company.id,
                          name=kname, weight_pct=weight, sequence=seq)
                db.add(kpi)
                db.flush()
                kpis.append(kpi)

            # Performance reviews for all employees
            for emp in employees_created:
                scores = [random.randint(55, 100) for _ in kpis]
                weighted = sum(s * float(k.weight_pct) / 100 for s, k in zip(scores, kpis))
                review = PerformanceReview(
                    employee_id=emp.id,
                    cycle_id=perf_cycle.id,
                    self_overall_score=Decimal(str(round(random.uniform(70, 95), 1))),
                    manager_overall_score=Decimal(str(round(weighted, 1))),
                    final_score=Decimal(str(round(weighted, 1))),
                    status=ReviewStatus.COMPLETED,
                    completed_at=datetime(2025, 2, 28, tzinfo=timezone.utc),
                )
                db.add(review)
                db.flush()
                for kpi, score in zip(kpis, scores):
                    ks = KPIScore(review_id=review.id, kpi_id=kpi.id,
                                  self_score=Decimal(str(score)),
                                  manager_score=Decimal(str(score)))
                    db.add(ks)

            # --- COMPENSATION CYCLE & RULES ---
            comp_cycle = CompensationCycle(
                company_id=company.id,
                name="Annual Increment FY 2025-26",
                year=2025,
                status=CycleStatus.ACTIVE,
                total_budget=Decimal("5000000.00"),  # ₹50 lakh budget
                start_date=datetime(2025, 4, 1, tzinfo=timezone.utc),
                end_date=datetime(2025, 6, 30, tzinfo=timezone.utc),
            )
            db.add(comp_cycle)
            db.flush()

            rules_data = [
                ("Outstanding (90–100)", Decimal("90"), Decimal("100"), Decimal("15.00")),
                ("Excellent (80–89)", Decimal("80"), Decimal("89.99"), Decimal("12.00")),
                ("Good (70–79)", Decimal("70"), Decimal("79.99"), Decimal("8.00")),
                ("Average (60–69)", Decimal("60"), Decimal("69.99"), Decimal("5.00")),
                ("Below Average (<60)", Decimal("0"), Decimal("59.99"), Decimal("3.00")),
            ]
            for rname, rmin, rmax, pct in rules_data:
                rule = CompensationRule(company_id=company.id, name=rname,
                                        min_score=rmin, max_score=rmax,
                                        recommended_increment_pct=pct)
                db.add(rule)

            # Compensation plans for employees (based on performance scores)
            for emp in employees_created[:20]:  # First 20 for demo
                review = db.query(PerformanceReview).filter(
                    PerformanceReview.employee_id == emp.id,
                    PerformanceReview.cycle_id == perf_cycle.id,
                ).first()
                score = float(review.final_score) if review and review.final_score else 75.0
                # Find applicable rule
                if score >= 90: pct = 15.0
                elif score >= 80: pct = 12.0
                elif score >= 70: pct = 8.0
                elif score >= 60: pct = 5.0
                else: pct = 3.0

                current_sal = float(emp.gross_ctc)
                new_sal = round(current_sal * (1 + pct / 100), 2)
                plan = CompensationPlan(
                    cycle_id=comp_cycle.id,
                    employee_id=emp.id,
                    current_salary=Decimal(str(current_sal)),
                    performance_score=Decimal(str(round(score, 1))),
                    system_recommended_pct=Decimal(str(pct)),
                    system_recommended_salary=Decimal(str(new_sal)),
                    manager_recommended_pct=Decimal(str(pct)),
                    manager_recommended_salary=Decimal(str(new_sal)),
                    final_increment_pct=Decimal(str(pct)),
                    final_new_salary=Decimal(str(new_sal)),
                    status=PlanStatus.APPROVED if random.random() > 0.3 else PlanStatus.PENDING,
                )
                db.add(plan)

            # --- PAYROLL RUN (March 2025) ---
            payroll_run = PayrollRun(
                company_id=company.id,
                month=3,
                year=2025,
                status=PayrollStatus.APPROVED,
                total_employees=len(employees_created),
                processed_at=datetime(2025, 3, 28, tzinfo=timezone.utc),
            )
            db.add(payroll_run)
            db.flush()

            total_gross = Decimal("0")
            total_ded = Decimal("0")
            total_net = Decimal("0")

            for emp in employees_created:
                gross = Decimal(str(emp.gross_ctc or 30000))
                basic = (gross * Decimal("50") / 100).quantize(Decimal("0.01"))
                hra = (basic * Decimal("50") / 100).quantize(Decimal("0.01"))
                transport = Decimal("1600")
                special = gross - basic - hra - transport
                pf_ded = (basic * Decimal("12") / 100).quantize(Decimal("0.01"))
                pt_ded = Decimal("200")
                tds_ded = (gross * Decimal("5") / 100).quantize(Decimal("0.01"))
                total_earnings = basic + hra + transport + special
                total_deductions = pf_ded + pt_ded + tds_ded
                net = total_earnings - total_deductions

                payslip = Payslip(
                    payroll_run_id=payroll_run.id,
                    employee_id=emp.id,
                    gross_salary=gross,
                    total_earnings=total_earnings,
                    total_deductions=total_deductions,
                    net_salary=net,
                    working_days=26,
                    paid_days=Decimal("26"),
                )
                db.add(payslip)
                db.flush()

                items = [
                    PayslipItem(payslip_id=payslip.id, component_name="Basic Salary",
                                component_type="earning", amount=basic, sequence=1),
                    PayslipItem(payslip_id=payslip.id, component_name="HRA",
                                component_type="earning", amount=hra, sequence=2),
                    PayslipItem(payslip_id=payslip.id, component_name="Transport Allowance",
                                component_type="earning", amount=transport, sequence=3),
                    PayslipItem(payslip_id=payslip.id, component_name="Special Allowance",
                                component_type="earning", amount=special, sequence=4),
                    PayslipItem(payslip_id=payslip.id, component_name="Provident Fund",
                                component_type="deduction", amount=pf_ded, sequence=5),
                    PayslipItem(payslip_id=payslip.id, component_name="Professional Tax",
                                component_type="deduction", amount=pt_ded, sequence=6),
                    PayslipItem(payslip_id=payslip.id, component_name="TDS",
                                component_type="deduction", amount=tds_ded, sequence=7),
                ]
                for item in items:
                    db.add(item)

                total_gross += total_earnings
                total_ded += total_deductions
                total_net += net

            payroll_run.total_gross = total_gross
            payroll_run.total_deductions = total_ded
            payroll_run.total_net = total_net

            # --- WORKFLOW DEFINITION ---
            workflow = WorkflowDefinition(
                company_id=company.id,
                name="Salary Increment Approval",
                entity_type=WorkflowEntityType.SALARY_INCREMENT,
                stages_config=[
                    {"stage": 1, "role": "department_manager", "label": "Manager Review"},
                    {"stage": 2, "role": "hr_manager", "label": "HR Review"},
                    {"stage": 3, "role": "finance_manager", "label": "Finance Approval"},
                ],
                is_active=True,
            )
            db.add(workflow)
            db.flush()

            # Sample approval requests
            for i, emp in enumerate(employees_created[:5]):
                req = ApprovalRequest(
                    company_id=company.id,
                    workflow_id=workflow.id,
                    entity_type=WorkflowEntityType.SALARY_INCREMENT,
                    entity_id=emp.id,
                    entity_ref=f"Salary Increment for {emp.full_name}",
                    current_stage=random.choice([1, 2, 3]),
                    total_stages=3,
                    status=random.choice([RequestStatus.IN_PROGRESS, RequestStatus.APPROVED]),
                    created_by_id=admin_user.id,
                )
                db.add(req)

            # --- QA TEST PLAN + 25 TEST CASES ---
            test_plan = TestPlan(
                company_id=company.id,
                name=f"HRMS Core Functionality Test Plan — {company.name}",
                module="Core HRMS",
                description="Comprehensive test coverage for HRMS modules",
                version="1.0",
            )
            db.add(test_plan)
            db.flush()

            test_cases_data = [
                # Positive tests
                ("TC-001", "Valid employee registration with all mandatory fields", TestType.POSITIVE,
                 "HR Manager is logged in; Company has a valid department",
                 "1. Navigate to Add Employee\n2. Fill all mandatory fields\n3. Click Save",
                 "Employee is created with a unique employee code (e.g. ABCT-0001)", "Employee Management"),
                ("TC-002", "Login with valid credentials", TestType.POSITIVE,
                 "User exists and is active",
                 "1. Open login page\n2. Enter valid email and password\n3. Click Login",
                 "User is redirected to dashboard. JWT token is returned.", "Authentication"),
                ("TC-003", "Assign salary structure to employee", TestType.POSITIVE,
                 "Active employee exists; Salary structure exists",
                 "1. Open employee profile\n2. Click Assign Salary Structure\n3. Select structure and enter CTC",
                 "Salary assignment is created. Payslip calculation reflects correct breakdown.", "Salary"),
                ("TC-004", "Create performance review cycle", TestType.POSITIVE,
                 "Company admin is logged in",
                 "1. Go to Performance > Cycles\n2. Create new cycle with KPIs summing to 100%\n3. Save",
                 "Cycle is created. KPI total validates to 100%.", "Performance"),
                ("TC-005", "Process monthly payroll", TestType.POSITIVE,
                 "Employees have salary assignments; No existing payroll for the month",
                 "1. Go to Payroll > Process\n2. Select month/year\n3. Click Process\n4. Review and approve",
                 "Payslips are generated for all active employees. Net = Gross − Deductions.", "Payroll"),
                # Negative tests
                ("TC-006", "Duplicate employee ID within same company", TestType.NEGATIVE,
                 "Employee code ABCT-0001 already exists",
                 "1. Try to create an employee\n2. Manually set employee_code to ABCT-0001\n3. Save",
                 "HTTP 400 error: 'Employee code already exists in this company'", "Employee Management"),
                ("TC-007", "Invalid salary configuration — components exceed 100% of gross", TestType.NEGATIVE,
                 "HR Admin is logged in",
                 "1. Create salary structure\n2. Set Basic=60%, Special=50% (total 110%)\n3. Save",
                 "Validation error: 'Earnings cannot exceed gross CTC'", "Salary"),
                ("TC-008", "Login with wrong password", TestType.NEGATIVE,
                 "User account exists",
                 "1. Open login\n2. Enter correct email and wrong password\n3. Click Login",
                 "HTTP 401: 'Invalid email or password'. No token returned.", "Authentication"),
                ("TC-009", "Create performance cycle with KPI weights not summing to 100%", TestType.NEGATIVE,
                 "Company admin is logged in",
                 "1. Create performance cycle\n2. Add KPIs: 40% + 35% + 20% = 95% (not 100%)\n3. Save",
                 "Validation error: 'KPI weights must sum to exactly 100%'", "Performance"),
                ("TC-010", "Process payroll for a month that is already processed", TestType.NEGATIVE,
                 "Payroll for March 2025 already exists and is APPROVED",
                 "1. Try to process payroll for March 2025 again",
                 "HTTP 400: 'Payroll for March 2025 already exists'", "Payroll"),
                # Boundary tests
                ("TC-011", "Employee with 0% increment recommendation (score = 0)", TestType.BOUNDARY,
                 "Compensation cycle is active; Employee has performance score of 0",
                 "1. Set employee performance score to 0\n2. Run compensation planning",
                 "System recommends minimum 3% increment (below-average rule applies)", "Compensation"),
                ("TC-012", "Salary structure with exactly 100% of gross", TestType.BOUNDARY,
                 "HR Admin is creating salary structure",
                 "1. Set Basic=50%, Special=30%, Transport=20% of gross\n2. Save",
                 "Structure saves successfully. No validation error.", "Salary"),
                ("TC-013", "Performance score exactly at boundary (80.00 — Excellent threshold)", TestType.BOUNDARY,
                 "Performance review completed with score 80.00",
                 "1. Set employee score to exactly 80.00\n2. Check compensation recommendation",
                 "System recommends 12% increment (Excellent band: 80–89)", "Compensation"),
                ("TC-014", "Pagination — request page beyond total pages", TestType.BOUNDARY,
                 "Company has 50 employees; page_size=20",
                 "1. GET /api/v1/employees?page=10&page_size=20",
                 "Returns empty items array; total and total_pages are still correct", "Employee Management"),
                ("TC-015", "Employee gross CTC of ₹1 (minimum boundary)", TestType.BOUNDARY,
                 "HR Manager is creating employee",
                 "1. Set gross_ctc to 1\n2. Save\n3. Process payroll",
                 "Employee saves. Payslip generates with net salary ≥ 0.", "Payroll"),
                # Security tests
                ("TC-016", "Cross-company data access — Company A user tries to access Company B employees", TestType.SECURITY,
                 "Two separate companies exist. User belongs to Company A.",
                 "1. Login as Company A admin\n2. GET /api/v1/employees with company_b_employee_id",
                 "HTTP 404 or 403. Company B data is NOT returned. Tenant isolation enforced.", "Security"),
                ("TC-017", "Access protected endpoint without JWT token", TestType.SECURITY,
                 "No authentication token",
                 "1. GET /api/v1/employees (no Authorization header)",
                 "HTTP 403: Unauthorized. No data returned.", "Security"),
                ("TC-018", "Employee role trying to view another employee's data", TestType.SECURITY,
                 "User has EMPLOYEE role",
                 "1. Login as Employee user\n2. GET /api/v1/employees/{another_employee_id}",
                 "HTTP 403: Access denied.", "Security"),
                ("TC-019", "Expired JWT token access", TestType.SECURITY,
                 "JWT token that has expired",
                 "1. Use an expired JWT token in Authorization header\n2. Call any protected endpoint",
                 "HTTP 401: 'Invalid or expired token'", "Security"),
                ("TC-020", "SQL injection in employee search parameter", TestType.SECURITY,
                 "Attacker sends malicious search string",
                 "1. GET /api/v1/employees?search='; DROP TABLE employees; --",
                 "Query executes safely. No SQL error. No data corruption. ORM prevents injection.", "Security"),
                # Calculation tests
                ("TC-021", "Verify net salary calculation formula", TestType.POSITIVE,
                 "Employee with known gross CTC of ₹40,000",
                 "1. Process payroll for employee with ₹40,000 CTC\n2. Check payslip",
                 "Basic=₹20,000; HRA=₹10,000; PF=₹2,400; PT=₹200; TDS=₹2,000; Net≈₹27,000", "Payroll"),
                ("TC-022", "Compensation increment calculation accuracy", TestType.POSITIVE,
                 "Employee current salary ₹40,000; Performance score 85 (12% increment)",
                 "1. Run compensation planning for the employee",
                 "New salary = ₹40,000 × 1.12 = ₹44,800. System shows ₹44,800.", "Compensation"),
                ("TC-023", "Weighted KPI score calculation", TestType.POSITIVE,
                 "KPIs: Technical(35%), Productivity(30%), Communication(20%), Attendance(15%)",
                 "1. Enter scores: Technical=90, Productivity=80, Communication=70, Attendance=100\n2. Submit",
                 "Final score = (90×0.35)+(80×0.30)+(70×0.20)+(100×0.15) = 83.5", "Performance"),
                ("TC-024", "Budget utilization warning when increments exceed budget", TestType.NEGATIVE,
                 "Department budget = ₹1,00,000; Total increments = ₹1,20,000",
                 "1. Plan increments that total ₹1,20,000 for a dept with ₹1,00,000 budget",
                 "System shows warning: 'Budget exceeded by ₹20,000'. Allows override with justification.", "Compensation"),
                ("TC-025", "Deactivated employee does not appear in payroll", TestType.NEGATIVE,
                 "Employee is deactivated before payroll processing",
                 "1. Deactivate an employee\n2. Process payroll for that month",
                 "Deactivated employee has no payslip in the payroll run.", "Payroll"),
            ]

            for tc_data in test_cases_data:
                tc = TestCase(
                    plan_id=test_plan.id,
                    case_id=tc_data[0],
                    title=tc_data[1],
                    test_type=tc_data[2],
                    preconditions=tc_data[3],
                    test_steps=tc_data[4],
                    expected_result=tc_data[5],
                    module=tc_data[6],
                )
                db.add(tc)
                db.flush()

                # Create execution records
                status_choices = [ExecutionStatus.PASSED, ExecutionStatus.PASSED,
                                  ExecutionStatus.PASSED, ExecutionStatus.FAILED]
                exec_status = random.choice(status_choices)
                execution = TestExecution(
                    test_case_id=tc.id,
                    executed_by_id=admin_user.id,
                    status=exec_status,
                    actual_result=tc_data[5] if exec_status == ExecutionStatus.PASSED
                    else "Unexpected error occurred",
                    build_version="1.0.0",
                    execution_time_ms=random.randint(50, 2000),
                )
                db.add(execution)
                db.flush()

                # Create defects for failed tests
                if exec_status == ExecutionStatus.FAILED:
                    defect = Defect(
                        company_id=company.id,
                        test_case_id=tc.id,
                        defect_id=f"BUG-{random.randint(100, 999)}",
                        title=f"[{tc_data[6]}] {tc_data[1]} — Actual result mismatch",
                        description=f"Test case {tc_data[0]} failed. Expected: {tc_data[5][:100]}",
                        severity=random.choice([DefectSeverity.HIGH, DefectSeverity.MEDIUM]),
                        priority=random.choice([DefectPriority.P1, DefectPriority.P2]),
                        status=random.choice([DefectStatus.OPEN, DefectStatus.IN_PROGRESS]),
                        module=tc_data[6],
                        reported_by_id=admin_user.id,
                    )
                    db.add(defect)

            # Audit log entries
            db.add(AuditLog(
                company_id=company.id,
                user_id=admin_user.id,
                user_email=admin_user.email,
                action="company.setup",
                entity_type="company",
                entity_id=company.id,
                entity_ref=company.name,
                new_values={"name": company.name, "code": company.code},
            ))

            all_company_data.append({
                "company": company,
                "admin": admin_user,
                "employees": employees_created,
            })

            print(f"✅ Company '{company.name}' created with {len(employees_created)} employees")

        db.commit()
        print("\n" + "="*60)
        print("🎉 Seed data created successfully!")
        print("="*60)
        print("\n📋 LOGIN CREDENTIALS:")
        print(f"  Platform Admin: admin@hrmsplatform.com / Admin@1234")
        print(f"  ABC Tech Admin: admin@abct.com / Admin@1234")
        print(f"  ABC Tech HR:    hr.manager@abct.com / Admin@1234")
        print(f"  XYZ Solutions Admin: admin@xyzs.com / Admin@1234")
        print(f"  XYZ Solutions HR:    hr.manager@xyzs.com / Admin@1234")
        print("\n🚀 Start the backend: uvicorn app.main:app --reload")
        print("📖 API Docs: http://localhost:8000/api/docs")

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    run()
