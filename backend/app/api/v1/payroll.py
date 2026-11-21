import calendar
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.v1._common import FINANCE_ROLES, HR_ROLES, company_id_of, jsonable, require, row
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.employee import Employee, EmploymentStatus
from app.models.payroll import PayrollRun, PayrollStatus, Payslip, PayslipItem
from app.models.salary import (EmployeeSalaryAssignment, SalaryStructure,
                               SalaryStructureComponent)
from app.models.user import User
from app.models.workflow import WorkflowEntityType
from app.services import workflow_service
from app.services.audit_service import log_action
from app.services.salary_engine import calculate_breakdown

router = APIRouter(prefix="/payroll", tags=["Payroll"])

PROCESS_ROLES = tuple(set(HR_ROLES) | set(FINANCE_ROLES))


class RunIn(BaseModel):
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)
    notes: Optional[str] = None


def _run_out(r: PayrollRun) -> dict:
    out = row(r, "id", "month", "year", "status", "total_employees", "total_gross",
              "total_deductions", "total_net", "processed_at", "approved_at", "notes", "created_at")
    out["period"] = f"{calendar.month_name[r.month]} {r.year}"
    return out


def _get_run(db: Session, cid: int, run_id: int) -> PayrollRun:
    run = db.query(PayrollRun).filter(PayrollRun.id == run_id, PayrollRun.company_id == cid).first()
    if not run:
        raise HTTPException(404, "Payroll run not found")
    return run


@router.get("/runs")
def list_runs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    runs = db.query(PayrollRun).filter(PayrollRun.company_id == cid) \
        .order_by(PayrollRun.year.desc(), PayrollRun.month.desc()).all()
    return [_run_out(r) for r in runs]


@router.post("/runs", status_code=201)
def create_run(data: RunIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require(user, PROCESS_ROLES, "payroll")
    cid = company_id_of(user)
    if db.query(PayrollRun).filter(PayrollRun.company_id == cid, PayrollRun.month == data.month,
                                   PayrollRun.year == data.year).first():
        raise HTTPException(400, f"A payroll run for {calendar.month_name[data.month]} "
                                 f"{data.year} already exists")
    run = PayrollRun(company_id=cid, month=data.month, year=data.year,
                     status=PayrollStatus.DRAFT, notes=data.notes)
    db.add(run)
    db.flush()
    log_action(db, "payroll.create", "payroll_run", run.id, _run_out(run)["period"], user=user)
    db.commit()
    return _run_out(run)


@router.get("/runs/{run_id}")
def get_run(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    run = _get_run(db, cid, run_id)
    slips = db.query(Payslip).options(joinedload(Payslip.employee).joinedload(Employee.department)) \
        .filter(Payslip.payroll_run_id == run.id).all()
    out = _run_out(run)
    out["payslips"] = sorted([{
        "id": p.id,
        "employee_id": p.employee_id,
        "employee_code": p.employee.employee_code,
        "employee_name": p.employee.full_name,
        "department": p.employee.department.name if p.employee.department else None,
        "gross_salary": float(p.gross_salary),
        "total_earnings": float(p.total_earnings),
        "total_deductions": float(p.total_deductions),
        "net_salary": float(p.net_salary),
        "working_days": p.working_days,
        "paid_days": jsonable(p.paid_days),
    } for p in slips], key=lambda x: x["employee_name"])
    req = workflow_service.open_request_for(db, cid, WorkflowEntityType.PAYROLL_APPROVAL, run.id)
    out["approval_request_id"] = req.id if req else None
    return out


@router.post("/runs/{run_id}/process")
def process_run(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Calculate payslips for every active employee with a salary structure."""
    require(user, PROCESS_ROLES, "payroll processing")
    cid = company_id_of(user)
    run = _get_run(db, cid, run_id)
    if run.status not in (PayrollStatus.DRAFT, PayrollStatus.PENDING_APPROVAL):
        raise HTTPException(400, f"A {run.status.value.replace('_', ' ')} payroll cannot be reprocessed")

    days_in_month = calendar.monthrange(run.year, run.month)[1]
    month_start = date(run.year, run.month, 1)
    month_end = date(run.year, run.month, days_in_month)

    for old in list(run.payslips):
        db.delete(old)
    db.flush()

    rows = db.query(Employee, EmployeeSalaryAssignment).join(
        EmployeeSalaryAssignment, EmployeeSalaryAssignment.employee_id == Employee.id
    ).filter(Employee.company_id == cid, Employee.is_active == True,
             Employee.status.in_([EmploymentStatus.ACTIVE, EmploymentStatus.ON_LEAVE]),
             EmployeeSalaryAssignment.end_date.is_(None)).all()

    structures = {}
    created = 0
    skipped, totals = [], {"gross": Decimal("0"), "ded": Decimal("0"), "net": Decimal("0")}
    for emp, assignment in rows:
        if emp.joining_date and emp.joining_date > month_end:
            skipped.append(f"{emp.full_name} (joins after this month)")
            continue
        if assignment.structure_id not in structures:
            structures[assignment.structure_id] = db.query(SalaryStructure).options(
                joinedload(SalaryStructure.components).joinedload(SalaryStructureComponent.component)
            ).filter(SalaryStructure.id == assignment.structure_id).first()
        b = calculate_breakdown(structures[assignment.structure_id], assignment.gross_ctc)

        paid_days = days_in_month
        if emp.joining_date and emp.joining_date > month_start:
            paid_days = (month_end - emp.joining_date).days + 1
        ratio = Decimal(paid_days) / Decimal(days_in_month)

        def pr(v: Decimal) -> Decimal:
            return (v * ratio).quantize(Decimal("0.01"))

        earnings, deductions = pr(b["total_earnings"]), pr(b["total_deductions"])
        slip = Payslip(payroll_run_id=run.id, employee_id=emp.id, gross_salary=pr(b["monthly_gross"]),
                       total_earnings=earnings, total_deductions=deductions,
                       net_salary=earnings - deductions, bonus=0, working_days=days_in_month,
                       paid_days=paid_days)
        for i in b["items"]:
            slip.items.append(PayslipItem(component_id=i["component_id"], component_name=i["name"],
                                          component_type=i["type"], amount=pr(i["amount"]),
                                          sequence=i["sequence"]))
        db.add(slip)
        created += 1
        totals["gross"] += slip.gross_salary
        totals["ded"] += deductions
        totals["net"] += slip.net_salary

    assigned_ids = [e.id for e, _ in rows]
    unassigned_q = db.query(Employee).filter(Employee.company_id == cid, Employee.is_active == True)
    if assigned_ids:
        unassigned_q = unassigned_q.filter(~Employee.id.in_(assigned_ids))
    unassigned = unassigned_q.all()
    skipped += [f"{e.full_name} (no salary structure)" for e in unassigned]

    count = created
    run.total_employees = count
    run.total_gross = totals["gross"]
    run.total_deductions = totals["ded"]
    run.total_net = totals["net"]
    run.total_bonus = 0
    run.status = PayrollStatus.PENDING_APPROVAL
    run.processed_by_id = user.id
    run.processed_at = datetime.now(timezone.utc)
    period = _run_out(run)["period"]
    log_action(db, "payroll.process", "payroll_run", run.id, period, user=user,
               new_values={"employees": count, "total_net": float(totals["net"])})
    req = workflow_service.start_request(db, cid, WorkflowEntityType.PAYROLL_APPROVAL, run.id,
                                         f"Payroll {period}", user)
    db.commit()
    out = _run_out(run)
    out["skipped"] = skipped
    out["approval_request_id"] = req.id if req else None
    return out


@router.post("/runs/{run_id}/approve")
def approve_run(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require(user, FINANCE_ROLES, "payroll approval")
    cid = company_id_of(user)
    run = _get_run(db, cid, run_id)
    if run.status != PayrollStatus.PENDING_APPROVAL:
        raise HTTPException(400, "Only a processed payroll awaiting approval can be approved")
    req = workflow_service.open_request_for(db, cid, WorkflowEntityType.PAYROLL_APPROVAL, run.id)
    if req:
        raise HTTPException(400, "This payroll is going through the approval workflow. "
                                 "Approve it from the Approvals page.")
    run.status = PayrollStatus.APPROVED
    run.approved_by_id = user.id
    run.approved_at = datetime.now(timezone.utc)
    log_action(db, "payroll.approve", "payroll_run", run.id, _run_out(run)["period"], user=user)
    db.commit()
    return _run_out(run)


@router.post("/runs/{run_id}/mark-paid")
def mark_paid(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require(user, FINANCE_ROLES, "payroll disbursement")
    run = _get_run(db, company_id_of(user), run_id)
    if run.status != PayrollStatus.APPROVED:
        raise HTTPException(400, "Only an approved payroll can be marked as paid")
    run.status = PayrollStatus.PAID
    log_action(db, "payroll.paid", "payroll_run", run.id, _run_out(run)["period"], user=user)
    db.commit()
    return _run_out(run)


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require(user, PROCESS_ROLES, "payroll")
    cid = company_id_of(user)
    run = _get_run(db, cid, run_id)
    if run.status in (PayrollStatus.APPROVED, PayrollStatus.PAID):
        raise HTTPException(400, "An approved or paid payroll cannot be cancelled")
    run.status = PayrollStatus.CANCELLED
    req = workflow_service.open_request_for(db, cid, WorkflowEntityType.PAYROLL_APPROVAL, run.id)
    if req:
        from app.models.workflow import RequestStatus
        req.status = RequestStatus.CANCELLED
    log_action(db, "payroll.cancel", "payroll_run", run.id, _run_out(run)["period"], user=user)
    db.commit()
    return _run_out(run)


@router.get("/payslips/{payslip_id}")
def get_payslip(payslip_id: int, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    cid = company_id_of(user)
    p = db.query(Payslip).join(PayrollRun).filter(Payslip.id == payslip_id,
                                                  PayrollRun.company_id == cid).first()
    if not p:
        raise HTTPException(404, "Payslip not found")
    e = p.employee
    return {
        "id": p.id,
        "period": _run_out(p.payroll_run)["period"],
        "run_status": p.payroll_run.status.value,
        "employee": {
            "id": e.id, "code": e.employee_code, "name": e.full_name, "email": e.email,
            "department": e.department.name if e.department else None,
            "designation": e.designation.name if e.designation else None,
        },
        "working_days": p.working_days,
        "paid_days": jsonable(p.paid_days),
        "gross_salary": float(p.gross_salary),
        "total_earnings": float(p.total_earnings),
        "total_deductions": float(p.total_deductions),
        "net_salary": float(p.net_salary),
        "items": [{"name": i.component_name, "type": i.component_type, "amount": float(i.amount)}
                  for i in sorted(p.items, key=lambda x: x.sequence or 0)],
    }
