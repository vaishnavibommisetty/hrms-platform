from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.v1._common import company_id_of, jsonable, row
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.qa import (Defect, DefectPriority, DefectSeverity, DefectStatus, ExecutionStatus,
                           TestCase, TestExecution, TestPlan, TestType)
from app.models.user import User
from app.services.audit_service import log_action

router = APIRouter(prefix="/qa", tags=["QA Management"])

# Allowed defect life-cycle moves
TRANSITIONS = {
    DefectStatus.OPEN: {DefectStatus.IN_PROGRESS, DefectStatus.WONT_FIX},
    DefectStatus.IN_PROGRESS: {DefectStatus.FIXED, DefectStatus.WONT_FIX, DefectStatus.OPEN},
    DefectStatus.FIXED: {DefectStatus.VERIFIED, DefectStatus.REOPENED},
    DefectStatus.VERIFIED: {DefectStatus.CLOSED, DefectStatus.REOPENED},
    DefectStatus.CLOSED: {DefectStatus.REOPENED},
    DefectStatus.REOPENED: {DefectStatus.IN_PROGRESS},
    DefectStatus.WONT_FIX: {DefectStatus.REOPENED},
}
OPEN_DEFECTS = (DefectStatus.OPEN, DefectStatus.IN_PROGRESS, DefectStatus.REOPENED)


class PlanIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    module: str = Field(min_length=2, max_length=100)
    description: Optional[str] = None
    version: str = "1.0"


class CaseIn(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    test_type: TestType
    preconditions: Optional[str] = None
    test_steps: str = Field(min_length=3)
    expected_result: str = Field(min_length=3)
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


class ExecutionIn(BaseModel):
    status: ExecutionStatus
    actual_result: Optional[str] = None
    notes: Optional[str] = None
    build_version: Optional[str] = None


class DefectIn(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    description: str = Field(min_length=3)
    steps_to_reproduce: Optional[str] = None
    expected_behaviour: Optional[str] = None
    actual_behaviour: Optional[str] = None
    severity: DefectSeverity
    priority: DefectPriority
    module: Optional[str] = None
    test_case_id: Optional[int] = None


class DefectUpdate(BaseModel):
    status: DefectStatus
    comment: Optional[str] = None


def _latest(case: TestCase) -> Optional[TestExecution]:
    return max(case.executions, key=lambda e: (e.executed_at, e.id), default=None)


def _case_out(c: TestCase) -> dict:
    out = row(c, "id", "plan_id", "case_id", "title", "test_type", "preconditions", "test_steps",
              "expected_result", "module", "priority", "is_automated", "created_at")
    last = _latest(c)
    out["last_status"] = last.status.value if last else ExecutionStatus.NOT_RUN.value
    out["last_executed_at"] = jsonable(last.executed_at) if last else None
    out["execution_count"] = len(c.executions)
    return out


def _plan_out(p: TestPlan) -> dict:
    out = row(p, "id", "name", "module", "description", "version", "is_active", "created_at")
    counts = {s.value: 0 for s in ExecutionStatus}
    for c in p.test_cases:
        last = _latest(c)
        counts[last.status.value if last else "not_run"] += 1
    executed = len(p.test_cases) - counts["not_run"]
    out["case_count"] = len(p.test_cases)
    out["status_counts"] = counts
    out["pass_rate"] = round(counts["passed"] / executed * 100, 1) if executed else None
    return out


def _defect_out(d: Defect) -> dict:
    out = row(d, "id", "defect_id", "title", "description", "steps_to_reproduce",
              "expected_behaviour", "actual_behaviour", "severity", "priority", "status", "module",
              "test_case_id", "resolved_at", "created_at", "updated_at")
    out["test_case_ref"] = d.test_case.case_id if d.test_case else None
    out["next_statuses"] = sorted(s.value for s in TRANSITIONS.get(d.status, set()))
    return out


def _get_plan(db: Session, cid: int, plan_id: int) -> TestPlan:
    p = db.query(TestPlan).options(joinedload(TestPlan.test_cases).joinedload(TestCase.executions)) \
        .filter(TestPlan.id == plan_id, TestPlan.company_id == cid).first()
    if not p:
        raise HTTPException(404, "Test plan not found")
    return p


def _get_case(db: Session, cid: int, case_id: int) -> TestCase:
    c = db.query(TestCase).join(TestPlan).filter(TestCase.id == case_id,
                                                 TestPlan.company_id == cid).first()
    if not c:
        raise HTTPException(404, "Test case not found")
    return c


def _next_ref(existing, prefix: str) -> str:
    nums = [int(x.split("-")[-1]) for x in existing if x and x.split("-")[-1].isdigit()]
    return f"{prefix}-{(max(nums) + 1) if nums else 1:03d}"


@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    plans = db.query(TestPlan).options(joinedload(TestPlan.test_cases).joinedload(TestCase.executions)) \
        .filter(TestPlan.company_id == cid).all()
    counts = {s.value: 0 for s in ExecutionStatus}
    by_type = {}
    for p in plans:
        for c in p.test_cases:
            last = _latest(c)
            counts[last.status.value if last else "not_run"] += 1
            by_type[c.test_type.value] = by_type.get(c.test_type.value, 0) + 1
    total = sum(counts.values())
    executed = total - counts["not_run"]
    defects = db.query(Defect).filter(Defect.company_id == cid).all()
    by_sev, by_status = {}, {}
    for d in defects:
        by_status[d.status.value] = by_status.get(d.status.value, 0) + 1
        if d.status in OPEN_DEFECTS:
            by_sev[d.severity.value] = by_sev.get(d.severity.value, 0) + 1
    return {
        "plans": len(plans),
        "test_cases": total,
        "executed": executed,
        "execution_coverage": round(executed / total * 100, 1) if total else None,
        "pass_rate": round(counts["passed"] / executed * 100, 1) if executed else None,
        "status_counts": counts,
        "cases_by_type": by_type,
        "defects_total": len(defects),
        "defects_open": len([d for d in defects if d.status in OPEN_DEFECTS]),
        "open_by_severity": by_sev,
        "defects_by_status": by_status,
    }


@router.get("/plans")
def list_plans(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    plans = db.query(TestPlan).options(joinedload(TestPlan.test_cases).joinedload(TestCase.executions)) \
        .filter(TestPlan.company_id == cid).order_by(TestPlan.module, TestPlan.name).all()
    return [_plan_out(p) for p in plans]


@router.post("/plans", status_code=201)
def create_plan(data: PlanIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    p = TestPlan(company_id=cid, created_by_id=user.id, **data.model_dump())
    db.add(p)
    db.flush()
    log_action(db, "test_plan.create", "test_plan", p.id, p.name, user=user)
    db.commit()
    return _plan_out(p)


@router.get("/plans/{plan_id}")
def get_plan(plan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _get_plan(db, company_id_of(user), plan_id)
    out = _plan_out(p)
    out["cases"] = [_case_out(c) for c in sorted(p.test_cases, key=lambda c: c.case_id)]
    return out


@router.post("/plans/{plan_id}/cases", status_code=201)
def create_case(plan_id: int, data: CaseIn, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    cid = company_id_of(user)
    p = _get_plan(db, cid, plan_id)
    refs = [r for (r,) in db.query(TestCase.case_id).join(TestPlan).filter(TestPlan.company_id == cid)]
    c = TestCase(plan_id=p.id, case_id=_next_ref(refs, "TC"), module=p.module, **data.model_dump())
    db.add(c)
    db.flush()
    log_action(db, "test_case.create", "test_case", c.id, c.case_id, user=user)
    db.commit()
    return _case_out(c)


@router.get("/cases/{case_id}")
def get_case(case_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _get_case(db, company_id_of(user), case_id)
    testers = {u.id: u.full_name for u in db.query(User).filter(
        User.id.in_([e.executed_by_id for e in c.executions] or [0]))}
    out = _case_out(c)
    out["plan_name"] = c.plan.name
    out["executions"] = [{
        **row(e, "id", "status", "actual_result", "notes", "build_version", "executed_at"),
        "executed_by": testers.get(e.executed_by_id),
    } for e in sorted(c.executions, key=lambda e: e.executed_at, reverse=True)]
    out["defects"] = [_defect_out(d) for d in c.defects]
    return out


@router.post("/cases/{case_id}/execute", status_code=201)
def execute_case(case_id: int, data: ExecutionIn, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    c = _get_case(db, company_id_of(user), case_id)
    if data.status == ExecutionStatus.NOT_RUN:
        raise HTTPException(400, "Choose a result: passed, failed, blocked or skipped")
    if data.status == ExecutionStatus.FAILED and not (data.actual_result or "").strip():
        raise HTTPException(400, "Describe the actual result when a test fails")
    e = TestExecution(test_case_id=c.id, executed_by_id=user.id, **data.model_dump())
    db.add(e)
    db.flush()
    log_action(db, "test_case.execute", "test_case", c.id, c.case_id, user=user,
               new_values={"status": data.status.value})
    db.commit()
    return _case_out(c)


@router.get("/defects")
def list_defects(status: Optional[str] = Query(None), severity: Optional[DefectSeverity] = Query(None),
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    q = db.query(Defect).options(joinedload(Defect.test_case)).filter(Defect.company_id == cid)
    if status == "open":
        q = q.filter(Defect.status.in_(OPEN_DEFECTS))
    elif status:
        try:
            q = q.filter(Defect.status == DefectStatus(status))
        except ValueError:
            raise HTTPException(400, f"Unknown status '{status}'")
    if severity:
        q = q.filter(Defect.severity == severity)
    return [_defect_out(d) for d in q.order_by(Defect.created_at.desc()).all()]


@router.post("/defects", status_code=201)
def create_defect(data: DefectIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    if data.test_case_id:
        _get_case(db, cid, data.test_case_id)
    refs = [r for (r,) in db.query(Defect.defect_id).filter(Defect.company_id == cid)]
    d = Defect(company_id=cid, defect_id=_next_ref(refs, "BUG"), reported_by_id=user.id,
               status=DefectStatus.OPEN, **data.model_dump())
    db.add(d)
    db.flush()
    log_action(db, "defect.create", "defect", d.id, d.defect_id, user=user,
               new_values={"severity": d.severity.value})
    db.commit()
    return _defect_out(d)


@router.put("/defects/{defect_id}")
def update_defect(defect_id: int, data: DefectUpdate, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    cid = company_id_of(user)
    d = db.query(Defect).filter(Defect.id == defect_id, Defect.company_id == cid).first()
    if not d:
        raise HTTPException(404, "Defect not found")
    if data.status not in TRANSITIONS.get(d.status, set()):
        raise HTTPException(400, f"A defect cannot move from {d.status.value.replace('_', ' ')} "
                                 f"to {data.status.value.replace('_', ' ')}")
    old = d.status.value
    d.status = data.status
    if data.status in (DefectStatus.CLOSED, DefectStatus.WONT_FIX, DefectStatus.VERIFIED):
        d.resolved_at = datetime.now(timezone.utc)
    elif data.status == DefectStatus.REOPENED:
        d.resolved_at = None
    log_action(db, "defect.status", "defect", d.id, d.defect_id, user=user,
               old_values={"status": old}, new_values={"status": data.status.value,
                                                       "comment": data.comment})
    db.commit()
    return _defect_out(d)
