from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.v1._common import ADMIN_ROLES, HR_ROLES, company_id_of, jsonable, require, row
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.compensation import (CompensationCycle, CompensationPlan, CompensationRule,
                                     CycleStatus, PlanStatus)
from app.models.employee import Employee
from app.models.performance import PerformanceReview, ReviewStatus
from app.models.salary import EmployeeSalaryAssignment
from app.models.user import User, UserRole
from app.models.workflow import WorkflowEntityType
from app.services import compensation_service as svc
from app.services import workflow_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/compensation", tags=["Compensation"])

PLANNER_ROLES = HR_ROLES + (UserRole.DEPARTMENT_MANAGER,)


class RuleIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    min_score: float = Field(ge=0, le=100)
    max_score: float = Field(ge=0, le=100)
    recommended_increment_pct: float = Field(ge=0, le=100)


class CycleIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    year: int = Field(ge=2000, le=2100)
    total_budget: float = Field(gt=0)
    start_date: datetime
    end_date: datetime


class PlanUpdate(BaseModel):
    manager_recommended_pct: Optional[float] = Field(default=None, ge=0, le=100)
    manager_notes: Optional[str] = None
    bonus_amount: Optional[float] = Field(default=None, ge=0)


class Decision(BaseModel):
    approve: bool
    reason: Optional[str] = None


def _get_cycle(db: Session, cid: int, cycle_id: int) -> CompensationCycle:
    c = db.query(CompensationCycle).options(
        joinedload(CompensationCycle.plans).joinedload(CompensationPlan.employee)
        .joinedload(Employee.department)
    ).filter(CompensationCycle.id == cycle_id, CompensationCycle.company_id == cid).first()
    if not c:
        raise HTTPException(404, "Compensation cycle not found")
    return c


def _get_plan(db: Session, cid: int, plan_id: int) -> CompensationPlan:
    p = db.query(CompensationPlan).join(CompensationCycle).filter(
        CompensationPlan.id == plan_id, CompensationCycle.company_id == cid).first()
    if not p:
        raise HTTPException(404, "Plan not found")
    return p


def _cycle_out(c: CompensationCycle) -> dict:
    out = row(c, "id", "name", "year", "status", "total_budget", "start_date", "end_date", "created_at")
    out["plan_count"] = len(c.plans)
    out["approved_count"] = len([p for p in c.plans if p.status == PlanStatus.APPROVED])
    out["budget"] = svc.budget_summary(c)
    return out


def _plan_out(p: CompensationPlan) -> dict:
    out = row(p, "id", "employee_id", "current_salary", "performance_score", "system_recommended_pct",
              "system_recommended_salary", "manager_recommended_pct", "manager_recommended_salary",
              "manager_notes", "final_increment_pct", "final_new_salary", "bonus_amount", "status",
              "rejection_reason")
    out["employee_name"] = p.employee.full_name
    out["employee_code"] = p.employee.employee_code
    out["department"] = p.employee.department.name if p.employee.department else None
    out["effective_pct"] = float(svc.plan_pct(p))
    out["annual_cost"] = float(svc.plan_cost(p))
    return out


# ── Rules ────────────────────────────────────────────────────────────────
@router.get("/rules")
def list_rules(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    rules = db.query(CompensationRule).filter(CompensationRule.company_id == cid,
                                              CompensationRule.is_active == True) \
        .order_by(CompensationRule.min_score.desc()).all()
    return [row(r, "id", "name", "min_score", "max_score", "recommended_increment_pct") for r in rules]


@router.post("/rules", status_code=201)
def create_rule(data: RuleIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require(user, HR_ROLES, "compensation setup")
    cid = company_id_of(user)
    if data.min_score >= data.max_score:
        raise HTTPException(400, "Minimum score must be lower than maximum score")
    for r in db.query(CompensationRule).filter(CompensationRule.company_id == cid,
                                               CompensationRule.is_active == True):
        if data.min_score <= float(r.max_score) and data.max_score >= float(r.min_score):
            raise HTTPException(400, f"Score range overlaps with rule '{r.name}' "
                                     f"({float(r.min_score):g}–{float(r.max_score):g})")
    rule = CompensationRule(company_id=cid, **data.model_dump())
    db.add(rule)
    db.flush()
    log_action(db, "compensation_rule.create", "compensation_rule", rule.id, rule.name, user=user)
    db.commit()
    return row(rule, "id", "name", "min_score", "max_score", "recommended_increment_pct")


# ── Cycles ───────────────────────────────────────────────────────────────
@router.get("/cycles")
def list_cycles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    cycles = db.query(CompensationCycle).options(joinedload(CompensationCycle.plans)) \
        .filter(CompensationCycle.company_id == cid).order_by(CompensationCycle.year.desc(),
                                                              CompensationCycle.id.desc()).all()
    return [_cycle_out(c) for c in cycles]


@router.post("/cycles", status_code=201)
def create_cycle(data: CycleIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require(user, HR_ROLES, "compensation setup")
    cid = company_id_of(user)
    if data.end_date <= data.start_date:
        raise HTTPException(400, "End date must be after start date")
    c = CompensationCycle(company_id=cid, created_by_id=user.id, status=CycleStatus.DRAFT,
                          **data.model_dump())
    db.add(c)
    db.flush()
    log_action(db, "compensation_cycle.create", "compensation_cycle", c.id, c.name, user=user)
    db.commit()
    return _cycle_out(c)


@router.get("/cycles/{cycle_id}")
def get_cycle(cycle_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _get_cycle(db, company_id_of(user), cycle_id)
    out = _cycle_out(c)
    out["plans"] = sorted([_plan_out(p) for p in c.plans], key=lambda x: x["employee_name"])
    return out


@router.post("/cycles/{cycle_id}/generate")
def generate_plans(cycle_id: int, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """Create a plan per employee, recommending an increment from their latest review score."""
    require(user, HR_ROLES, "compensation planning")
    cid = company_id_of(user)
    c = _get_cycle(db, cid, cycle_id)
    if c.status in (CycleStatus.COMPLETED, CycleStatus.CANCELLED):
        raise HTTPException(400, f"This cycle is {c.status.value}")
    rules = db.query(CompensationRule).filter(CompensationRule.company_id == cid,
                                              CompensationRule.is_active == True).all()
    if not rules:
        raise HTTPException(400, "Add at least one compensation rule first")
    existing = {p.employee_id for p in c.plans}
    emps = db.query(Employee).filter(Employee.company_id == cid, Employee.is_active == True,
                                     Employee.gross_ctc.isnot(None)).all()
    created = no_score = 0
    for e in emps:
        if e.id in existing:
            continue
        review = db.query(PerformanceReview).filter(
            PerformanceReview.employee_id == e.id, PerformanceReview.status == ReviewStatus.COMPLETED
        ).order_by(PerformanceReview.completed_at.desc()).first()
        score = review.final_score if review else None
        rule = svc.match_rule(rules, score)
        pct = rule.recommended_increment_pct if rule else 0
        if score is None:
            no_score += 1
        current = float(e.gross_ctc)
        db.add(CompensationPlan(cycle_id=c.id, employee_id=e.id, current_salary=current,
                                performance_score=score, system_recommended_pct=pct,
                                system_recommended_salary=round(current * (1 + float(pct) / 100), 2),
                                status=PlanStatus.PENDING))
        created += 1
    c.status = CycleStatus.ACTIVE
    log_action(db, "compensation_cycle.generate", "compensation_cycle", c.id, c.name, user=user,
               new_values={"plans_created": created})
    db.commit()
    return {"created": created, "without_review_score": no_score}


@router.post("/cycles/{cycle_id}/apply")
def apply_cycle(cycle_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Write approved increments into employees' salaries and close the cycle."""
    require(user, ADMIN_ROLES, "applying salary changes")
    cid = company_id_of(user)
    c = _get_cycle(db, cid, cycle_id)
    if c.status != CycleStatus.ACTIVE:
        raise HTTPException(400, "Only an active cycle can be applied")
    open_plans = [p for p in c.plans if p.status not in (PlanStatus.APPROVED, PlanStatus.REJECTED)]
    if open_plans:
        raise HTTPException(400, f"{len(open_plans)} plan(s) still need a decision")
    applied = 0
    now = svc.now()
    for p in c.plans:
        if p.status != PlanStatus.APPROVED:
            continue
        e = p.employee
        current = db.query(EmployeeSalaryAssignment).filter(
            EmployeeSalaryAssignment.employee_id == e.id, EmployeeSalaryAssignment.end_date.is_(None)
        ).first()
        if current:
            current.end_date = now
            db.add(EmployeeSalaryAssignment(employee_id=e.id, structure_id=current.structure_id,
                                            gross_ctc=p.final_new_salary, effective_date=now,
                                            created_by_id=user.id))
        e.gross_ctc = p.final_new_salary
        applied += 1
    c.status = CycleStatus.COMPLETED
    log_action(db, "compensation_cycle.apply", "compensation_cycle", c.id, c.name, user=user,
               new_values={"employees_updated": applied})
    db.commit()
    return {"applied": applied, "status": c.status.value}


# ── Plans ────────────────────────────────────────────────────────────────
@router.put("/plans/{plan_id}")
def update_plan(plan_id: int, data: PlanUpdate, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    require(user, PLANNER_ROLES, "compensation planning")
    p = _get_plan(db, company_id_of(user), plan_id)
    if p.status not in (PlanStatus.PENDING, PlanStatus.MANAGER_REVIEW):
        raise HTTPException(400, "This plan is already submitted or decided")
    if data.manager_recommended_pct is not None:
        p.manager_recommended_pct = data.manager_recommended_pct
        p.manager_recommended_salary = round(float(p.current_salary) *
                                             (1 + data.manager_recommended_pct / 100), 2)
        p.manager_reviewed_by = user.id
        p.manager_reviewed_at = svc.now()
    if data.manager_notes is not None:
        p.manager_notes = data.manager_notes
    if data.bonus_amount is not None:
        p.bonus_amount = data.bonus_amount
    p.status = PlanStatus.MANAGER_REVIEW
    db.commit()
    return _plan_out(p)


@router.post("/plans/{plan_id}/submit")
def submit_plan(plan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Send a plan for approval (via workflow if the company has one)."""
    require(user, PLANNER_ROLES, "compensation planning")
    cid = company_id_of(user)
    p = _get_plan(db, cid, plan_id)
    if p.status not in (PlanStatus.PENDING, PlanStatus.MANAGER_REVIEW):
        raise HTTPException(400, "This plan is already submitted or decided")
    req = workflow_service.start_request(db, cid, WorkflowEntityType.COMPENSATION_PLAN, p.id,
                                         f"Increment: {p.employee.full_name} "
                                         f"({float(svc.plan_pct(p)):g}%)", user)
    p.status = PlanStatus.HR_REVIEW
    db.commit()
    out = _plan_out(p)
    out["approval_request_id"] = req.id if req else None
    return out


@router.post("/plans/{plan_id}/decide")
def decide_plan(plan_id: int, data: Decision, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """Direct approve/reject for companies without a compensation workflow."""
    require(user, HR_ROLES, "compensation approval")
    cid = company_id_of(user)
    p = _get_plan(db, cid, plan_id)
    if workflow_service.open_request_for(db, cid, WorkflowEntityType.COMPENSATION_PLAN, p.id):
        raise HTTPException(400, "This plan is in the approval workflow. Decide it from Approvals.")
    if not data.approve and not (data.reason or "").strip():
        raise HTTPException(400, "Give a reason for rejecting")
    svc.finalize_plan(db, p.id, data.approve, user, data.reason)
    db.commit()
    return _plan_out(p)


@router.get("/employees/{employee_id}")
def employee_history(employee_id: int, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    cid = company_id_of(user)
    plans = db.query(CompensationPlan).join(CompensationCycle).filter(
        CompensationPlan.employee_id == employee_id, CompensationCycle.company_id == cid
    ).order_by(CompensationCycle.year.desc()).all()
    return [{"cycle": p.cycle.name, **_plan_out(p), "updated_at": jsonable(p.updated_at)} for p in plans]
