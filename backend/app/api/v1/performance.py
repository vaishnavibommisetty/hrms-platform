from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.v1._common import HR_ROLES, company_id_of, jsonable, require, row
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.employee import Employee, EmploymentStatus
from app.models.performance import KPI, KPIScore, PerformanceCycle, PerformanceReview, ReviewStatus
from app.models.user import User, UserRole
from app.services.audit_service import log_action

router = APIRouter(prefix="/performance", tags=["Performance"])

REVIEWER_ROLES = HR_ROLES + (UserRole.DEPARTMENT_MANAGER,)


def rating_label(score) -> Optional[str]:
    if score is None:
        return None
    s = float(score)
    if s >= 90:
        return "Outstanding"
    if s >= 75:
        return "Exceeds Expectations"
    if s >= 60:
        return "Meets Expectations"
    if s >= 40:
        return "Needs Improvement"
    return "Unsatisfactory"


class KPIIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None
    weight_pct: float = Field(gt=0, le=100)


class CycleIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    year: int = Field(ge=2000, le=2100)
    start_date: datetime
    end_date: datetime
    kpis: List[KPIIn] = Field(min_length=1)


class ScoreIn(BaseModel):
    kpi_id: int
    self_score: Optional[float] = Field(default=None, ge=0, le=100)
    manager_score: Optional[float] = Field(default=None, ge=0, le=100)


class ReviewUpdate(BaseModel):
    scores: List[ScoreIn] = []
    self_comments: Optional[str] = None
    manager_comments: Optional[str] = None
    submit: Optional[Literal["self", "manager"]] = None


def _get_cycle(db: Session, cid: int, cycle_id: int) -> PerformanceCycle:
    c = db.query(PerformanceCycle).filter(PerformanceCycle.id == cycle_id,
                                          PerformanceCycle.company_id == cid).first()
    if not c:
        raise HTTPException(404, "Performance cycle not found")
    return c


def _get_review(db: Session, cid: int, review_id: int) -> PerformanceReview:
    r = db.query(PerformanceReview).join(Employee).options(
        joinedload(PerformanceReview.kpi_scores),
        joinedload(PerformanceReview.cycle).joinedload(PerformanceCycle.kpis),
    ).filter(PerformanceReview.id == review_id, Employee.company_id == cid).first()
    if not r:
        raise HTTPException(404, "Review not found")
    return r


def _cycle_summary(c: PerformanceCycle) -> dict:
    out = row(c, "id", "name", "year", "start_date", "end_date", "status", "created_at")
    done = [r for r in c.reviews if r.status == ReviewStatus.COMPLETED]
    out["total_reviews"] = len(c.reviews)
    out["completed_reviews"] = len(done)
    scores = [float(r.final_score) for r in done if r.final_score is not None]
    out["average_score"] = round(sum(scores) / len(scores), 1) if scores else None
    out["kpi_count"] = len(c.kpis)
    return out


def _weighted(kpis: List[KPI], scores: dict, attr: str) -> Optional[Decimal]:
    values = [(k, getattr(scores.get(k.id), attr, None) if scores.get(k.id) else None) for k in kpis]
    if any(v is None for _, v in values):
        return None
    total = sum(Decimal(str(v)) * Decimal(str(k.weight_pct)) for k, v in values) / 100
    return total.quantize(Decimal("0.01"))


@router.get("/cycles")
def list_cycles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    cycles = db.query(PerformanceCycle).options(
        joinedload(PerformanceCycle.reviews), joinedload(PerformanceCycle.kpis)
    ).filter(PerformanceCycle.company_id == cid).order_by(PerformanceCycle.start_date.desc()).all()
    return [_cycle_summary(c) for c in cycles]


@router.post("/cycles", status_code=201)
def create_cycle(data: CycleIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require(user, HR_ROLES, "performance setup")
    cid = company_id_of(user)
    if data.end_date <= data.start_date:
        raise HTTPException(400, "End date must be after start date")
    total = round(sum(k.weight_pct for k in data.kpis), 2)
    if total != 100:
        raise HTTPException(400, f"KPI weights must add up to 100% (currently {total}%)")
    c = PerformanceCycle(company_id=cid, name=data.name.strip(), year=data.year,
                         start_date=data.start_date, end_date=data.end_date, status=ReviewStatus.DRAFT)
    for i, k in enumerate(data.kpis, start=1):
        c.kpis.append(KPI(company_id=cid, name=k.name.strip(), description=k.description,
                          weight_pct=k.weight_pct, sequence=i))
    db.add(c)
    db.flush()
    log_action(db, "performance_cycle.create", "performance_cycle", c.id, c.name, user=user)
    db.commit()
    return _cycle_summary(c)


@router.get("/cycles/{cycle_id}")
def get_cycle(cycle_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    c = _get_cycle(db, cid, cycle_id)
    out = _cycle_summary(c)
    out["kpis"] = [row(k, "id", "name", "description", "weight_pct", "sequence")
                   for k in sorted(c.kpis, key=lambda k: k.sequence or 0)]
    reviews = db.query(PerformanceReview).options(
        joinedload(PerformanceReview.employee).joinedload(Employee.department)
    ).filter(PerformanceReview.cycle_id == c.id).all()
    out["reviews"] = sorted([{
        "id": r.id,
        "employee_id": r.employee_id,
        "employee_name": r.employee.full_name,
        "employee_code": r.employee.employee_code,
        "department": r.employee.department.name if r.employee.department else None,
        "status": r.status.value,
        "self_overall_score": jsonable(r.self_overall_score),
        "manager_overall_score": jsonable(r.manager_overall_score),
        "final_score": jsonable(r.final_score),
        "rating": rating_label(r.final_score),
    } for r in reviews], key=lambda x: x["employee_name"])
    dist = {}
    for r in out["reviews"]:
        if r["rating"]:
            dist[r["rating"]] = dist.get(r["rating"], 0) + 1
    out["rating_distribution"] = dist
    return out


@router.post("/cycles/{cycle_id}/launch")
def launch_cycle(cycle_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Open the cycle and create a review for every active employee."""
    require(user, HR_ROLES, "performance setup")
    cid = company_id_of(user)
    c = _get_cycle(db, cid, cycle_id)
    if c.status == ReviewStatus.COMPLETED:
        raise HTTPException(400, "This cycle is already closed")
    existing = {r.employee_id for r in c.reviews}
    emps = db.query(Employee).filter(Employee.company_id == cid, Employee.is_active == True,
                                     Employee.status != EmploymentStatus.TERMINATED).all()
    created = 0
    for e in emps:
        if e.id in existing:
            continue
        db.add(PerformanceReview(employee_id=e.id, cycle_id=c.id, status=ReviewStatus.SELF_REVIEW))
        created += 1
    c.status = ReviewStatus.SELF_REVIEW
    log_action(db, "performance_cycle.launch", "performance_cycle", c.id, c.name, user=user,
               new_values={"reviews_created": created})
    db.commit()
    return {"created": created, "status": c.status.value}


@router.post("/cycles/{cycle_id}/close")
def close_cycle(cycle_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require(user, HR_ROLES, "performance setup")
    c = _get_cycle(db, company_id_of(user), cycle_id)
    pending = [r for r in c.reviews if r.status != ReviewStatus.COMPLETED]
    if pending:
        raise HTTPException(400, f"{len(pending)} review(s) are still open. Complete them first.")
    c.status = ReviewStatus.COMPLETED
    log_action(db, "performance_cycle.close", "performance_cycle", c.id, c.name, user=user)
    db.commit()
    return {"status": c.status.value}


@router.get("/reviews/{review_id}")
def get_review(review_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _get_review(db, company_id_of(user), review_id)
    scores = {s.kpi_id: s for s in r.kpi_scores}
    return {
        "id": r.id,
        "cycle_id": r.cycle_id,
        "cycle_name": r.cycle.name,
        "employee_id": r.employee_id,
        "employee_name": r.employee.full_name,
        "status": r.status.value,
        "self_comments": r.self_comments,
        "manager_comments": r.manager_comments,
        "self_overall_score": jsonable(r.self_overall_score),
        "manager_overall_score": jsonable(r.manager_overall_score),
        "final_score": jsonable(r.final_score),
        "rating": rating_label(r.final_score),
        "kpis": [{
            "kpi_id": k.id, "name": k.name, "description": k.description,
            "weight_pct": float(k.weight_pct),
            "self_score": jsonable(scores[k.id].self_score) if k.id in scores else None,
            "manager_score": jsonable(scores[k.id].manager_score) if k.id in scores else None,
        } for k in sorted(r.cycle.kpis, key=lambda k: k.sequence or 0)],
    }


@router.put("/reviews/{review_id}")
def update_review(review_id: int, data: ReviewUpdate, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    cid = company_id_of(user)
    r = _get_review(db, cid, review_id)
    if r.status == ReviewStatus.COMPLETED:
        raise HTTPException(400, "This review is already completed")
    is_reviewer = user.role in REVIEWER_ROLES
    is_self = r.employee.user_id == user.id
    if not (is_reviewer or is_self):
        raise HTTPException(403, "You can only edit your own review")

    kpi_ids = {k.id for k in r.cycle.kpis}
    existing = {s.kpi_id: s for s in r.kpi_scores}
    for s in data.scores:
        if s.kpi_id not in kpi_ids:
            raise HTTPException(400, f"KPI {s.kpi_id} is not part of this cycle")
        score = existing.get(s.kpi_id)
        if not score:
            score = KPIScore(kpi_id=s.kpi_id)
            r.kpi_scores.append(score)
            existing[s.kpi_id] = score
        if s.self_score is not None:
            score.self_score = s.self_score
        if s.manager_score is not None:
            if not is_reviewer:
                raise HTTPException(403, "Only a manager or HR can give manager scores")
            score.manager_score = s.manager_score
    if data.self_comments is not None:
        r.self_comments = data.self_comments
    if data.manager_comments is not None:
        r.manager_comments = data.manager_comments

    kpis = list(r.cycle.kpis)
    r.self_overall_score = _weighted(kpis, existing, "self_score")
    r.manager_overall_score = _weighted(kpis, existing, "manager_score")

    if data.submit == "self":
        if r.self_overall_score is None:
            raise HTTPException(400, "Score every KPI before submitting the self review")
        r.status = ReviewStatus.MANAGER_REVIEW
    elif data.submit == "manager":
        if not is_reviewer:
            raise HTTPException(403, "Only a manager or HR can complete a review")
        if r.manager_overall_score is None:
            raise HTTPException(400, "Give a manager score for every KPI before completing")
        r.final_score = r.manager_overall_score
        r.status = ReviewStatus.COMPLETED
        r.reviewer_id = user.id
        r.completed_at = datetime.now(timezone.utc)
        log_action(db, "performance_review.complete", "performance_review", r.id,
                   r.employee.full_name, user=user, new_values={"final_score": float(r.final_score)})
    db.commit()
    return get_review(review_id, user, db)
