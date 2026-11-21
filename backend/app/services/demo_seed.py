"""
Demo data for the ZeroCode HR Demo company (code ZCDEMO).

Runs once on startup: if the demo company exists and has no employees yet, it is filled with
a realistic organisation so every module has something to show. It uses the same API functions
the app uses, so payroll totals, scores and audit entries are calculated the real way.
"""
import logging
import random
from datetime import date, datetime, timedelta, timezone

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.company import Company
from app.models.employee import Department, Designation, Employee, EmploymentStatus, EmploymentType, Gender
from app.models.qa import (Defect, DefectPriority, DefectSeverity, DefectStatus, ExecutionStatus,
                           TestCase, TestExecution, TestPlan, TestType)
from app.models.salary import (CalculationType, ComponentType, EmployeeSalaryAssignment,
                               SalaryComponent, SalaryStructure, SalaryStructureComponent)
from app.models.user import User, UserRole

log = logging.getLogger("demo_seed")
DEMO_CODE = "ZCDEMO"
DEMO_PASSWORD = "Admin@123"

DEPARTMENTS = [
    ("Engineering", "ENG", [("Software Engineer", 2), ("Senior Software Engineer", 4), ("Engineering Manager", 7)]),
    ("Product", "PRD", [("Product Analyst", 2), ("Product Manager", 5), ("Head of Product", 8)]),
    ("Sales", "SAL", [("Sales Executive", 2), ("Account Manager", 4), ("Sales Director", 8)]),
    ("Human Resources", "HR", [("HR Executive", 2), ("HR Business Partner", 5), ("HR Head", 8)]),
    ("Finance", "FIN", [("Accountant", 2), ("Finance Manager", 5), ("Finance Controller", 8)]),
    ("Customer Success", "CS", [("Support Specialist", 1), ("Implementation Analyst", 3), ("CS Manager", 6)]),
]

# first, last, gender, department code, designation index
PEOPLE = [
    ("Arjun", "Mehta", "M", "ENG", 2), ("Priya", "Iyer", "F", "ENG", 1), ("Rahul", "Verma", "M", "ENG", 1),
    ("Sneha", "Kulkarni", "F", "ENG", 0), ("Vikram", "Reddy", "M", "ENG", 0), ("Ananya", "Das", "F", "ENG", 1),
    ("Karthik", "Nair", "M", "ENG", 0), ("Divya", "Menon", "F", "ENG", 0), ("Rohan", "Gupta", "M", "ENG", 1),
    ("Meera", "Pillai", "F", "PRD", 2), ("Aditya", "Joshi", "M", "PRD", 1), ("Kavya", "Shetty", "F", "PRD", 0),
    ("Nikhil", "Bansal", "M", "PRD", 0),
    ("Sanjay", "Kapoor", "M", "SAL", 2), ("Pooja", "Agarwal", "F", "SAL", 1), ("Amit", "Saxena", "M", "SAL", 0),
    ("Neha", "Chopra", "F", "SAL", 0), ("Varun", "Malhotra", "M", "SAL", 1), ("Isha", "Bhatt", "F", "SAL", 0),
    ("Lakshmi", "Rao", "F", "HR", 2), ("Farhan", "Qureshi", "M", "HR", 1), ("Swati", "Deshpande", "F", "HR", 0),
    ("Ramesh", "Krishnan", "M", "FIN", 2), ("Anjali", "Sinha", "F", "FIN", 1), ("Deepak", "Yadav", "M", "FIN", 0),
    ("Shreya", "Banerjee", "F", "CS", 2), ("Manoj", "Tiwari", "M", "CS", 1), ("Ritu", "Jain", "F", "CS", 1),
    ("Siddharth", "Rao", "M", "CS", 0), ("Nandini", "Hegde", "F", "CS", 0), ("Gaurav", "Mishra", "M", "CS", 0),
    ("Tanvi", "Patil", "F", "ENG", 0), ("Harsh", "Vora", "M", "SAL", 0),
]
# Leavers (kept for attrition reporting)
LEAVERS = [("Kunal", "Sethi", "M", "ENG", 0, EmploymentStatus.RESIGNED),
           ("Preeti", "Arora", "F", "SAL", 0, EmploymentStatus.RESIGNED),
           ("Mohit", "Khanna", "M", "CS", 0, EmploymentStatus.TERMINATED)]

BASE_CTC = {1: 420000, 2: 600000, 3: 800000, 4: 1400000, 5: 1800000, 6: 2000000, 7: 3200000, 8: 3800000}


def seed_demo_company() -> None:
    if not settings.SEED_DEMO_DATA:
        return
    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.code == DEMO_CODE).first()
        if not company:
            return
        if (db.query(Employee).filter(Employee.company_id == company.id).count() > 0
                or db.query(Department).filter(Department.company_id == company.id).count() > 0):
            return
        admin = db.query(User).filter(User.company_id == company.id,
                                      User.role == UserRole.COMPANY_ADMIN).first()
        if not admin:
            return
        log.warning("Seeding demo data for %s", company.name)
        _seed(db, company, admin)
        log.warning("Demo data ready")
    except Exception:
        db.rollback()
        log.exception("Demo seeding failed; the app will run without demo data")
    finally:
        db.close()


def _seed(db, company: Company, admin: User) -> None:
    rnd = random.Random(2026)
    today = date.today()
    cid = company.id

    # ── Users for each role ──────────────────────────────────────────────
    users = {"admin": admin}
    for key, email, name, role in [
        ("hr", "hr@zerocodehr.com", "Lakshmi Rao", UserRole.HR_MANAGER),
        ("finance", "finance@zerocodehr.com", "Ramesh Krishnan", UserRole.FINANCE_MANAGER),
        ("manager", "manager@zerocodehr.com", "Arjun Mehta", UserRole.DEPARTMENT_MANAGER),
    ]:
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(company_id=cid, email=email, full_name=name, role=role,
                     hashed_password=hash_password(DEMO_PASSWORD), is_active=True)
            db.add(u)
        users[key] = u
    db.flush()

    # ── Departments & designations ───────────────────────────────────────
    depts, desigs = {}, {}
    for name, code, titles in DEPARTMENTS:
        d = Department(company_id=cid, name=name, code=code, description=f"{name} team")
        db.add(d)
        db.flush()
        depts[code] = d
        desigs[code] = []
        for title, level in titles:
            g = Designation(company_id=cid, department_id=d.id, name=title, level=level)
            db.add(g)
            desigs[code].append(g)
    db.flush()

    # ── Salary components & structures ───────────────────────────────────
    comp_specs = [
        ("Basic Salary", "BASIC", ComponentType.EARNING, CalculationType.PERCENTAGE_OF_GROSS, True),
        ("House Rent Allowance", "HRA", ComponentType.EARNING, CalculationType.PERCENTAGE_OF_BASIC, True),
        ("Conveyance Allowance", "CONV", ComponentType.EARNING, CalculationType.FIXED, False),
        ("Provident Fund", "PF", ComponentType.DEDUCTION, CalculationType.PERCENTAGE_OF_BASIC, False),
        ("Professional Tax", "PT", ComponentType.DEDUCTION, CalculationType.FIXED, False),
        ("Income Tax (TDS)", "TDS", ComponentType.DEDUCTION, CalculationType.PERCENTAGE_OF_GROSS, False),
    ]
    comps = {}
    for name, code, ctype, calc, taxable in comp_specs:
        c = SalaryComponent(company_id=cid, name=name, code=code, component_type=ctype,
                            calculation_type=calc, is_taxable=taxable)
        db.add(c)
        comps[code] = c
    db.flush()

    def structure(name, desc, lines):
        s = SalaryStructure(company_id=cid, name=name, description=desc, version=1,
                            effective_date=datetime(today.year - 1, 4, 1, tzinfo=timezone.utc),
                            created_by_id=admin.id)
        for seq, (code, value) in enumerate(lines, start=1):
            s.components.append(SalaryStructureComponent(component_id=comps[code].id, value=value,
                                                         sequence=seq))
        db.add(s)
        return s

    standard = structure("Standard Staff", "Default structure for individual contributors",
                         [("BASIC", 40), ("HRA", 50), ("CONV", 1600), ("PF", 12), ("PT", 200), ("TDS", 5)])
    senior = structure("Senior Leadership", "Managers and above",
                       [("BASIC", 50), ("HRA", 50), ("CONV", 1600), ("PF", 12), ("PT", 200), ("TDS", 12)])
    db.flush()

    # ── Employees ────────────────────────────────────────────────────────
    gender_map = {"M": Gender.MALE, "F": Gender.FEMALE}
    emp_users = {"Lakshmi Rao": users["hr"], "Ramesh Krishnan": users["finance"],
                 "Arjun Mehta": users["manager"]}
    employees, n = [], 0
    heads = {}

    def make(first, last, g, dcode, didx, status=EmploymentStatus.ACTIVE, joined=None, leaving=None):
        nonlocal n
        n += 1
        desig = desigs[dcode][didx]
        level = desig.level
        ctc = round(BASE_CTC.get(level, 600000) * rnd.uniform(0.9, 1.15) / 1000) * 1000
        e = Employee(company_id=cid, department_id=depts[dcode].id, designation_id=desig.id,
                     employee_code=f"{DEMO_CODE}-{n:04d}", first_name=first, last_name=last,
                     email=f"{first.lower()}.{last.lower()}@zerocodehr.com",
                     phone=f"+91 9{rnd.randint(100000000, 999999999)}", gender=gender_map[g],
                     date_of_birth=date(rnd.randint(1980, 2001), rnd.randint(1, 12), rnd.randint(1, 28)),
                     joining_date=joined or (today - timedelta(days=rnd.randint(120, 2100))),
                     leaving_date=leaving, employment_type=EmploymentType.FULL_TIME,
                     status=status, gross_ctc=ctc,
                     is_active=status not in (EmploymentStatus.RESIGNED, EmploymentStatus.TERMINATED))
        u = emp_users.get(f"{first} {last}")
        if u:
            e.user_id = u.id
        db.add(e)
        return e

    for first, last, g, dcode, didx in PEOPLE:
        e = make(first, last, g, dcode, didx)
        employees.append(e)
        if didx == 2:
            heads[dcode] = e
    # an intern-style contract hire and someone on leave
    employees[7].employment_type = EmploymentType.CONTRACT
    employees[16].status = EmploymentStatus.ON_LEAVE
    for first, last, g, dcode, didx, status in LEAVERS:
        joined = today - timedelta(days=rnd.randint(200, 900))
        make(first, last, g, dcode, didx, status=status, joined=joined,
             leaving=today - timedelta(days=rnd.randint(30, 150)))
    db.flush()
    for e in employees:
        head = heads.get(next(c for c, d in depts.items() if d.id == e.department_id))
        if head and head.id != e.id:
            e.manager_id = head.id

    # Salary structure assignments (one deliberately left out -> shows in data-quality report)
    start = datetime(today.year - 1, 4, 1, tzinfo=timezone.utc)
    for e in employees[:-1]:
        level = next(g.level for g in desigs[[c for c, d in depts.items() if d.id == e.department_id][0]]
                     if g.id == e.designation_id)
        s = senior if level >= 6 else standard
        db.add(EmployeeSalaryAssignment(employee_id=e.id, structure_id=s.id, gross_ctc=e.gross_ctc,
                                        effective_date=start, created_by_id=admin.id))
    employees[-1].designation_id = None  # missing designation -> data-quality report
    db.commit()

    # ── Payroll: three past months, last one with a joiner and a raise ───
    from app.api.v1 import compensation as comp_api
    from app.api.v1 import payroll as payroll_api
    from app.api.v1 import performance as perf_api
    from app.api.v1 import workflows as wf_api

    def month_back(k):
        y, m = today.year, today.month - k
        while m <= 0:
            m += 12
            y -= 1
        return y, m

    for k, final_status in ((3, "paid"), (2, "paid"), (1, "approved")):
        y, m = month_back(k)
        if k == 1:
            # mid-month joiner and a promotion show up in the variance report
            joiner = make("Aisha", "Khan", "F", "ENG", 0, joined=date(y, m, 15))
            db.flush()
            db.add(EmployeeSalaryAssignment(employee_id=joiner.id, structure_id=standard.id,
                                            gross_ctc=joiner.gross_ctc,
                                            effective_date=datetime(y, m, 15, tzinfo=timezone.utc),
                                            created_by_id=admin.id))
            promoted = employees[2]
            old = db.query(EmployeeSalaryAssignment).filter(
                EmployeeSalaryAssignment.employee_id == promoted.id,
                EmployeeSalaryAssignment.end_date.is_(None)).first()
            old.end_date = datetime(y, m, 1, tzinfo=timezone.utc)
            promoted.gross_ctc = round(float(promoted.gross_ctc) * 1.18, -3)
            db.add(EmployeeSalaryAssignment(employee_id=promoted.id, structure_id=standard.id,
                                            gross_ctc=promoted.gross_ctc,
                                            effective_date=datetime(y, m, 1, tzinfo=timezone.utc),
                                            created_by_id=admin.id))
            db.commit()
        run = payroll_api.create_run(payroll_api.RunIn(month=m, year=y), user=users["hr"], db=db)
        payroll_api.process_run(run["id"], user=users["hr"], db=db)
        payroll_api.approve_run(run["id"], user=users["finance"], db=db)
        if final_status == "paid":
            payroll_api.mark_paid(run["id"], user=users["finance"], db=db)

    # ── Performance: last year's cycle completed, this year's in progress ─
    kpis = [perf_api.KPIIn(name="Delivery & quality", weight_pct=40,
                           description="Commitments met at the agreed quality"),
            perf_api.KPIIn(name="Ownership", weight_pct=25, description="Takes problems end to end"),
            perf_api.KPIIn(name="Collaboration", weight_pct=20, description="Works well across teams"),
            perf_api.KPIIn(name="Learning & growth", weight_pct=15, description="Builds new skills")]
    last_year = perf_api.create_cycle(perf_api.CycleIn(
        name=f"Annual Review {today.year - 1}", year=today.year - 1,
        start_date=datetime(today.year - 1, 4, 1), end_date=datetime(today.year, 3, 31), kpis=kpis),
        user=users["hr"], db=db)
    perf_api.launch_cycle(last_year["id"], user=users["hr"], db=db)
    detail = perf_api.get_cycle(last_year["id"], user=users["hr"], db=db)
    kpi_ids = [k["id"] for k in detail["kpis"]]
    for r in detail["reviews"]:
        talent = rnd.choice([92, 85, 80, 76, 72, 68, 64, 58, 48])
        scores = []
        for kid in kpi_ids:
            self_s = min(100, max(30, talent + rnd.randint(-4, 10)))
            mgr_s = min(100, max(25, talent + rnd.randint(-8, 6)))
            scores.append(perf_api.ScoreIn(kpi_id=kid, self_score=self_s, manager_score=mgr_s))
        perf_api.update_review(r["id"], perf_api.ReviewUpdate(
            scores=scores, self_comments="Delivered my goals for the year.",
            manager_comments="Solid year. See KPI notes.", submit="manager"),
            user=users["hr"], db=db)
    perf_api.close_cycle(last_year["id"], user=users["hr"], db=db)

    current = perf_api.create_cycle(perf_api.CycleIn(
        name=f"Mid-Year Review {today.year}", year=today.year,
        start_date=datetime(today.year, 4, 1), end_date=datetime(today.year, 9, 30), kpis=kpis),
        user=users["hr"], db=db)
    perf_api.launch_cycle(current["id"], user=users["hr"], db=db)
    detail = perf_api.get_cycle(current["id"], user=users["hr"], db=db)
    for i, r in enumerate(detail["reviews"][:12]):
        scores = [perf_api.ScoreIn(kpi_id=k["id"], self_score=rnd.randint(65, 92)) for k in detail["kpis"]]
        perf_api.update_review(r["id"], perf_api.ReviewUpdate(
            scores=scores, self_comments="On track for the half.", submit="self"),
            user=users["hr"], db=db)

    # ── Compensation: rules, an active cycle with mixed decisions ─────────
    for name, lo, hi, pct in [("Outstanding", 90, 100, 15), ("Exceeds expectations", 75, 89.99, 10),
                              ("Meets expectations", 60, 74.99, 7), ("Needs improvement", 40, 59.99, 3),
                              ("Unsatisfactory", 0, 39.99, 0)]:
        comp_api.create_rule(comp_api.RuleIn(name=name, min_score=lo, max_score=hi,
                                             recommended_increment_pct=pct), user=users["hr"], db=db)
    cycle = comp_api.create_cycle(comp_api.CycleIn(
        name=f"FY {today.year}-{str(today.year + 1)[-2:]} Increments", year=today.year,
        total_budget=4500000, start_date=datetime(today.year, 4, 1),
        end_date=datetime(today.year + 1, 3, 31)), user=users["hr"], db=db)
    comp_api.generate_plans(cycle["id"], user=users["hr"], db=db)
    plans = comp_api.get_cycle(cycle["id"], user=users["hr"], db=db)["plans"]
    for p in plans[:10]:
        comp_api.decide_plan(p["id"], comp_api.Decision(approve=True), user=users["hr"], db=db)
    comp_api.update_plan(plans[10]["id"], comp_api.PlanUpdate(
        manager_recommended_pct=12, manager_notes="Took on team lead duties mid-year"),
        user=users["manager"], db=db)
    comp_api.update_plan(plans[11]["id"], comp_api.PlanUpdate(
        bonus_amount=50000, manager_notes="Closed the largest deal of the year"),
        user=users["manager"], db=db)
    comp_api.decide_plan(plans[12]["id"], comp_api.Decision(
        approve=False, reason="Already received an off-cycle raise this year"), user=users["hr"], db=db)

    # ── Approval workflows, then items waiting in them ───────────────────
    wf_api.create_definition(wf_api.DefinitionIn(
        name="Payroll sign-off", entity_type="payroll_approval",
        stages=[wf_api.StageIn(role="hr_manager", label="HR verification"),
                wf_api.StageIn(role="finance_manager", label="Finance approval")]),
        user=admin, db=db)
    wf_api.create_definition(wf_api.DefinitionIn(
        name="Increment approval", entity_type="compensation_plan",
        stages=[wf_api.StageIn(role="hr_manager", label="HR review"),
                wf_api.StageIn(role="company_admin", label="Final approval")]),
        user=admin, db=db)
    run = payroll_api.create_run(payroll_api.RunIn(month=today.month, year=today.year),
                                 user=users["hr"], db=db)
    payroll_api.process_run(run["id"], user=users["hr"], db=db)  # waits for HR then Finance
    comp_api.submit_plan(plans[10]["id"], user=users["manager"], db=db)
    sub = comp_api.submit_plan(plans[11]["id"], user=users["manager"], db=db)
    wf_api.act_on_request(sub["approval_request_id"], wf_api.ActionIn(
        approve=True, comments="Bonus justified by deal size"), user=users["hr"], db=db)

    _seed_qa(db, cid, users, rnd)


def _seed_qa(db, cid: int, users: dict, rnd: random.Random) -> None:
    hr = users["hr"]
    plans = {
        "Employee Management": [
            ("Create employee with all mandatory fields", TestType.POSITIVE,
             "1. Open Employees\n2. Click Add Employee\n3. Fill name, email, department, joining date\n4. Save",
             "Employee is created with the next sequential code and appears in the list", "passed"),
            ("Reject duplicate employee email in the same company", TestType.NEGATIVE,
             "1. Add an employee with an email that already exists\n2. Save",
             "Error 'email already exists' is shown and no record is created", "passed"),
            ("Search employees by partial name", TestType.POSITIVE,
             "1. Type 'pri' in the search box", "Only matching employees are listed", "passed"),
            ("Deactivate employee removes them from active list", TestType.POSITIVE,
             "1. Deactivate an employee\n2. Reload the list", "Employee no longer shows in the active list", "passed"),
            ("Joining date far in the future", TestType.BOUNDARY,
             "1. Add employee with joining date 5 years ahead", "A validation warning is shown", "failed"),
        ],
        "Salary & Payroll": [
            ("Monthly breakdown adds up to monthly gross", TestType.POSITIVE,
             "1. Preview Standard Staff structure at ₹12,00,000 CTC",
             "Total earnings equal ₹1,00,000 per month", "passed"),
            ("Percentage component cannot exceed 100", TestType.BOUNDARY,
             "1. Create structure with Basic = 120%", "Validation error is shown", "passed"),
            ("Mid-month joiner is pro-rated", TestType.POSITIVE,
             "1. Process payroll for a month where an employee joined on the 15th",
             "Paid days and amounts are pro-rated", "passed"),
            ("Reprocess payroll after approval is blocked", TestType.NEGATIVE,
             "1. Approve a payroll run\n2. Try to reprocess it", "Error: approved payroll cannot be reprocessed", "passed"),
            ("Payroll with zero employees", TestType.BOUNDARY,
             "1. Process payroll for a company with no salary assignments",
             "Run completes with zero totals and lists skipped employees", "not_run"),
            ("Payslip PDF download", TestType.POSITIVE,
             "1. Open a payslip\n2. Click Download", "PDF payslip downloads", "blocked"),
        ],
        "Approval Workflows": [
            ("Payroll moves HR -> Finance -> Approved", TestType.POSITIVE,
             "1. Process payroll\n2. Approve as HR\n3. Approve as Finance", "Payroll status becomes Approved", "passed"),
            ("Wrong role cannot approve a stage", TestType.SECURITY,
             "1. Log in as Finance\n2. Try to approve a request at the HR stage", "403 error: stage must be actioned by HR", "passed"),
            ("Rejection requires a comment", TestType.NEGATIVE,
             "1. Reject a request with an empty comment", "Validation error is shown", "passed"),
            ("Rejected payroll returns to draft", TestType.REGRESSION,
             "1. Reject a payroll approval", "Payroll status goes back to Draft", "failed"),
        ],
        "Multi-tenant Security": [
            ("Company A cannot read Company B employees", TestType.SECURITY,
             "1. Log in as Company A admin\n2. Call GET /employees/{id of a Company B employee}", "404 Not Found", "passed"),
            ("SQL reports are scoped to the caller's company", TestType.SECURITY,
             "1. Run any report as Company A", "Only Company A rows are returned", "passed"),
            ("Expired token is rejected", TestType.SECURITY,
             "1. Call any API with a token older than 8 hours", "401 Unauthorized", "passed"),
            ("Employee role cannot open the audit log", TestType.SECURITY,
             "1. Log in as an employee\n2. Open /audit", "403 Forbidden", "passed"),
        ],
    }
    case_refs = {}
    n = 0
    now = datetime.now(timezone.utc)
    for module, cases in plans.items():
        plan = TestPlan(company_id=cid, name=f"{module} test plan", module=module, version="1.0",
                        description=f"Functional and negative tests for {module.lower()}",
                        created_by_id=hr.id)
        db.add(plan)
        db.flush()
        for title, ttype, steps, expected, result in cases:
            n += 1
            tc = TestCase(plan_id=plan.id, case_id=f"TC-{n:03d}", title=title, test_type=ttype,
                          test_steps=steps, expected_result=expected, module=module,
                          priority="high" if ttype == TestType.SECURITY else "medium",
                          preconditions="Logged in as an HR user")
            db.add(tc)
            db.flush()
            case_refs[title] = tc
            if result == "not_run":
                continue
            if result in ("failed", "passed") and rnd.random() < 0.4:
                db.add(TestExecution(test_case_id=tc.id, executed_by_id=hr.id,
                                     status=ExecutionStatus.FAILED, build_version="1.0.0",
                                     actual_result="Failed in the first build",
                                     executed_at=now - timedelta(days=12)))
            db.add(TestExecution(test_case_id=tc.id, executed_by_id=hr.id,
                                 status=ExecutionStatus(result), build_version="1.1.0",
                                 actual_result=None if result == "passed" else
                                 ("Blocked: PDF generation not built yet" if result == "blocked"
                                  else "Behaviour did not match the expected result"),
                                 executed_at=now - timedelta(days=rnd.randint(1, 6))))
    defects = [
        ("No warning for joining date 5 years in the future", "Employee Management", DefectSeverity.MEDIUM,
         DefectPriority.P3, DefectStatus.OPEN, "Joining date far in the future"),
        ("Rejected payroll keeps old totals on screen until refresh", "Approval Workflows", DefectSeverity.HIGH,
         DefectPriority.P2, DefectStatus.IN_PROGRESS, "Rejected payroll returns to draft"),
        ("Payslip PDF download not implemented", "Salary & Payroll", DefectSeverity.MEDIUM,
         DefectPriority.P3, DefectStatus.OPEN, "Payslip PDF download"),
        ("Rounding difference of ₹0.01 on HRA for odd CTCs", "Salary & Payroll", DefectSeverity.LOW,
         DefectPriority.P4, DefectStatus.FIXED, None),
        ("Department filter resets when changing page", "Employee Management", DefectSeverity.LOW,
         DefectPriority.P4, DefectStatus.CLOSED, None),
        ("Report query failed on PostgreSQL for tenure bands", "Reports", DefectSeverity.CRITICAL,
         DefectPriority.P1, DefectStatus.VERIFIED, None),
        ("Finance user could see HR-stage approve button", "Approval Workflows", DefectSeverity.HIGH,
         DefectPriority.P1, DefectStatus.CLOSED, None),
    ]
    for i, (title, module, sev, pri, status, case_title) in enumerate(defects, start=1):
        d = Defect(company_id=cid, defect_id=f"BUG-{i:03d}", title=title, module=module,
                   description=title, severity=sev, priority=pri, status=status,
                   steps_to_reproduce="See linked test case" if case_title else "Reported during exploratory testing",
                   expected_behaviour="Works as specified", actual_behaviour=title,
                   test_case_id=case_refs[case_title].id if case_title else None,
                   reported_by_id=hr.id,
                   resolved_at=now if status in (DefectStatus.CLOSED, DefectStatus.VERIFIED) else None)
        db.add(d)
    db.commit()
