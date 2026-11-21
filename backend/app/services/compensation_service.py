"""Compensation planning rules: recommendation, budget tracking and final approval."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.compensation import (CompensationCycle, CompensationPlan, CompensationRule,
                                     PlanStatus)
from app.models.user import User
from app.services.audit_service import log_action

TWO = Decimal("0.01")


def match_rule(rules: List[CompensationRule], score) -> Optional[CompensationRule]:
    if score is None:
        return None
    s = Decimal(str(score))
    for r in sorted(rules, key=lambda r: r.min_score, reverse=True):
        if Decimal(str(r.min_score)) <= s <= Decimal(str(r.max_score)):
            return r
    return None


def plan_pct(p: CompensationPlan) -> Decimal:
    """The increment that would apply right now: manager's override, else the system's."""
    if p.manager_recommended_pct is not None:
        return Decimal(str(p.manager_recommended_pct))
    return Decimal(str(p.system_recommended_pct or 0))


def plan_cost(p: CompensationPlan) -> Decimal:
    """Annual cost of a plan = salary increase + one-time bonus."""
    if p.status == PlanStatus.APPROVED and p.final_new_salary is not None:
        raise_amt = Decimal(str(p.final_new_salary)) - Decimal(str(p.current_salary))
    elif p.status == PlanStatus.REJECTED:
        return Decimal("0")
    else:
        raise_amt = Decimal(str(p.current_salary)) * plan_pct(p) / 100
    return (raise_amt + Decimal(str(p.bonus_amount or 0))).quantize(TWO)


def budget_summary(cycle: CompensationCycle) -> dict:
    approved = sum((plan_cost(p) for p in cycle.plans if p.status == PlanStatus.APPROVED), Decimal("0"))
    projected = sum((plan_cost(p) for p in cycle.plans), Decimal("0"))
    budget = Decimal(str(cycle.total_budget or 0))
    return {
        "total_budget": float(budget),
        "approved_cost": float(approved),
        "projected_cost": float(projected),
        "remaining": float(budget - approved),
        "utilization_pct": round(float(approved / budget * 100), 1) if budget else None,
        "projected_utilization_pct": round(float(projected / budget * 100), 1) if budget else None,
    }


def finalize_plan(db: Session, plan_id: int, approved: bool, user: User,
                  reason: Optional[str] = None) -> CompensationPlan:
    p = db.get(CompensationPlan, plan_id)
    if not p:
        raise HTTPException(404, "Plan not found")
    if p.status in (PlanStatus.APPROVED, PlanStatus.REJECTED):
        raise HTTPException(400, f"This plan is already {p.status.value}")
    if approved:
        pct = plan_pct(p)
        new_salary = (Decimal(str(p.current_salary)) * (1 + pct / 100)).quantize(TWO)
        cycle = p.cycle
        if cycle.total_budget:
            others = sum((plan_cost(x) for x in cycle.plans
                          if x.status == PlanStatus.APPROVED and x.id != p.id), Decimal("0"))
            this_cost = new_salary - Decimal(str(p.current_salary)) + Decimal(str(p.bonus_amount or 0))
            if others + this_cost > Decimal(str(cycle.total_budget)):
                raise HTTPException(400, "Approving this plan would exceed the cycle budget "
                                         f"(₹{float(cycle.total_budget):,.0f})")
        p.final_increment_pct = pct
        p.final_new_salary = new_salary
        p.status = PlanStatus.APPROVED
    else:
        p.status = PlanStatus.REJECTED
        p.rejection_reason = reason
    log_action(db, "compensation_plan.approve" if approved else "compensation_plan.reject",
               "compensation_plan", p.id, p.employee.full_name, user=user,
               new_values={"increment_pct": float(p.final_increment_pct or 0), "reason": reason},
               company_id=p.cycle.company_id)
    return p


def now() -> datetime:
    return datetime.now(timezone.utc)
