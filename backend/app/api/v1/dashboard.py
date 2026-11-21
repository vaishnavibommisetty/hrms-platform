from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.employee import Employee
from app.models.company import Company
from app.models.payroll import PayrollRun, Payslip, PayrollStatus
from app.models.compensation import CompensationCycle, CycleStatus
from app.models.performance import PerformanceReview, ReviewStatus
from app.models.workflow import ApprovalRequest, RequestStatus
from app.models.qa import TestExecution, ExecutionStatus, Defect, DefectStatus

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/metrics")
def get_dashboard_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all KPI metrics for the dashboard.
    Every metric comes from actual database queries — no fake data.
    """
    company_id = current_user.company_id

    # --- EMPLOYEE METRICS ---
    employee_query = db.query(Employee).filter(Employee.is_active == True)
    if company_id:
        employee_query = employee_query.filter(Employee.company_id == company_id)
    total_employees = employee_query.count()

    # --- COMPANY METRICS (platform admin only) ---
    total_companies = None
    if current_user.role == UserRole.PLATFORM_ADMIN:
        total_companies = db.query(Company).filter(Company.is_active == True).count()

    # --- PAYROLL METRICS ---
    payroll_query = db.query(PayrollRun).filter(
        PayrollRun.status.in_([PayrollStatus.APPROVED, PayrollStatus.PAID])
    )
    if company_id:
        payroll_query = payroll_query.filter(PayrollRun.company_id == company_id)
    latest_payroll = payroll_query.order_by(
        PayrollRun.year.desc(), PayrollRun.month.desc()
    ).first()

    monthly_payroll = float(latest_payroll.total_net) if latest_payroll and latest_payroll.total_net else 0.0

    # --- COMPENSATION BUDGET UTILIZATION ---
    comp_cycle = None
    if company_id:
        comp_cycle = db.query(CompensationCycle).filter(
            CompensationCycle.company_id == company_id,
            CompensationCycle.status == CycleStatus.ACTIVE,
        ).first()

    budget_utilization = None
    if comp_cycle and comp_cycle.total_budget:
        from app.models.compensation import CompensationPlan, PlanStatus
        approved_plans = db.query(CompensationPlan).filter(
            CompensationPlan.cycle_id == comp_cycle.id,
            CompensationPlan.status == PlanStatus.APPROVED,
        ).all()
        total_increment_cost = sum(
            (float(p.final_new_salary or 0) - float(p.current_salary or 0)) * 12
            for p in approved_plans
        )
        budget_utilization = round(
            (total_increment_cost / float(comp_cycle.total_budget)) * 100, 1
        ) if comp_cycle.total_budget > 0 else 0.0

    # --- AVERAGE PERFORMANCE SCORE ---
    perf_query = db.query(func.avg(PerformanceReview.final_score)).filter(
        PerformanceReview.status == ReviewStatus.COMPLETED,
        PerformanceReview.final_score.isnot(None),
    )
    if company_id:
        from app.models.employee import Employee as Emp
        perf_query = perf_query.join(Emp, PerformanceReview.employee_id == Emp.id).filter(
            Emp.company_id == company_id
        )
    avg_score_result = perf_query.scalar()
    avg_performance = round(float(avg_score_result), 1) if avg_score_result else None

    # --- PENDING APPROVALS ---
    approval_query = db.query(ApprovalRequest).filter(
        ApprovalRequest.status == RequestStatus.IN_PROGRESS
    )
    if company_id:
        approval_query = approval_query.filter(ApprovalRequest.company_id == company_id)
    pending_approvals = approval_query.count()

    # --- QA METRICS ---
    exec_query = db.query(TestExecution)
    if company_id:
        from app.models.qa import TestCase, TestPlan
        exec_query = exec_query.join(TestCase).join(TestPlan).filter(
            TestPlan.company_id == company_id
        )
    total_executions = exec_query.count()
    passed_executions = exec_query.filter(
        TestExecution.status == ExecutionStatus.PASSED
    ).count()
    qa_pass_pct = round((passed_executions / total_executions * 100), 1) if total_executions > 0 else 0.0

    defect_query = db.query(Defect).filter(
        Defect.status.in_([DefectStatus.OPEN, DefectStatus.IN_PROGRESS, DefectStatus.REOPENED])
    )
    if company_id:
        defect_query = defect_query.filter(Defect.company_id == company_id)
    open_defects = defect_query.count()

    # --- DEPARTMENT BREAKDOWN (chart data) ---
    from app.models.employee import Department
    dept_data = []
    if company_id:
        depts = db.query(Department).filter(
            Department.company_id == company_id,
            Department.is_active == True,
        ).all()
        for dept in depts:
            count = db.query(Employee).filter(
                Employee.department_id == dept.id,
                Employee.is_active == True,
            ).count()
            dept_data.append({"name": dept.name, "count": count})

    # --- RECENT EMPLOYEES ---
    recent_emp_q = db.query(Employee).filter(Employee.is_active == True)
    if company_id:
        recent_emp_q = recent_emp_q.filter(Employee.company_id == company_id)
    recent_employees = recent_emp_q.order_by(Employee.created_at.desc()).limit(5).all()
    recent_emp_data = [
        {
            "id": e.id,
            "name": e.full_name,
            "employee_code": e.employee_code,
            "department": e.department.name if e.department else None,
            "joining_date": e.joining_date.isoformat() if e.joining_date else None,
        }
        for e in recent_employees
    ]

    return {
        "total_employees": total_employees,
        "total_companies": total_companies,
        "monthly_payroll": monthly_payroll,
        "budget_utilization_pct": budget_utilization,
        "avg_performance_score": avg_performance,
        "pending_approvals": pending_approvals,
        "qa_pass_pct": qa_pass_pct,
        "open_defects": open_defects,
        "department_breakdown": dept_data,
        "recent_employees": recent_emp_data,
    }
