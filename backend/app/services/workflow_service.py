"""
Approval workflow engine.

A WorkflowDefinition holds ordered stages: [{"stage": 1, "role": "hr_manager", "label": "HR Review"}, ...]
An ApprovalRequest walks through those stages. Each stage must be actioned by a user with
that stage's role (company admins may act on any stage). Rejection at any stage ends it.
When the last stage approves, the linked entity (payroll run, compensation plan) is updated.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.workflow import (ActionType, ApprovalAction, ApprovalRequest, RequestStatus,
                                 WorkflowDefinition, WorkflowEntityType)
from app.services.audit_service import log_action

OPEN_STATUSES = (RequestStatus.PENDING, RequestStatus.IN_PROGRESS)


def active_definition(db: Session, company_id: int,
                      entity_type: WorkflowEntityType) -> Optional[WorkflowDefinition]:
    return db.query(WorkflowDefinition).filter(
        WorkflowDefinition.company_id == company_id,
        WorkflowDefinition.entity_type == entity_type,
        WorkflowDefinition.is_active == True,
    ).order_by(WorkflowDefinition.id.desc()).first()


def open_request_for(db: Session, company_id: int, entity_type: WorkflowEntityType,
                     entity_id: int) -> Optional[ApprovalRequest]:
    return db.query(ApprovalRequest).filter(
        ApprovalRequest.company_id == company_id,
        ApprovalRequest.entity_type == entity_type,
        ApprovalRequest.entity_id == entity_id,
        ApprovalRequest.status.in_(OPEN_STATUSES),
    ).first()


def start_request(db: Session, company_id: int, entity_type: WorkflowEntityType, entity_id: int,
                  entity_ref: str, user: User) -> Optional[ApprovalRequest]:
    """Create an approval request if the company has a workflow for this entity type."""
    definition = active_definition(db, company_id, entity_type)
    if not definition:
        return None
    existing = open_request_for(db, company_id, entity_type, entity_id)
    if existing:
        return existing
    req = ApprovalRequest(company_id=company_id, workflow_id=definition.id,
                          entity_type=entity_type, entity_id=entity_id, entity_ref=entity_ref,
                          current_stage=1, total_stages=len(definition.stages_config),
                          status=RequestStatus.PENDING, created_by_id=user.id)
    db.add(req)
    db.flush()
    log_action(db, "approval.submit", entity_type.value, entity_id, entity_ref, user=user,
               company_id=company_id)
    return req


def stage_info(req: ApprovalRequest) -> dict:
    stages = sorted(req.workflow.stages_config, key=lambda s: s["stage"])
    current = next((s for s in stages if s["stage"] == req.current_stage), None)
    return {"stages": stages, "current": current}


def can_act(user: User, req: ApprovalRequest) -> bool:
    if req.status not in OPEN_STATUSES:
        return False
    if user.role in (UserRole.COMPANY_ADMIN, UserRole.PLATFORM_ADMIN):
        return True
    current = stage_info(req)["current"]
    return bool(current and current.get("role") == user.role.value)


def act(db: Session, req: ApprovalRequest, user: User, approve: bool,
        comments: Optional[str]) -> ApprovalRequest:
    if req.status not in OPEN_STATUSES:
        raise HTTPException(400, f"This request is already {req.status.value}")
    if not can_act(user, req):
        role = (stage_info(req)["current"] or {}).get("role", "another role")
        raise HTTPException(403, f"This stage must be actioned by: {role.replace('_', ' ')}")
    if not approve and not (comments or "").strip():
        raise HTTPException(400, "A comment is required when rejecting")

    current = stage_info(req)["current"] or {}
    db.add(ApprovalAction(request_id=req.id, stage_number=req.current_stage,
                          stage_label=current.get("label"), approver_id=user.id,
                          action=ActionType.APPROVED if approve else ActionType.REJECTED,
                          comments=comments))
    now = datetime.now(timezone.utc)
    if not approve:
        req.status = RequestStatus.REJECTED
        req.completed_at = now
        _on_rejected(db, req, user, comments)
    elif req.current_stage >= req.total_stages:
        req.status = RequestStatus.APPROVED
        req.completed_at = now
        _on_approved(db, req, user)
    else:
        req.current_stage += 1
        req.status = RequestStatus.IN_PROGRESS
    log_action(db, "approval.approve" if approve else "approval.reject", req.entity_type.value,
               req.entity_id, req.entity_ref, user=user,
               new_values={"stage": current.get("label"), "comments": comments})
    return req


def _on_approved(db: Session, req: ApprovalRequest, user: User) -> None:
    if req.entity_type == WorkflowEntityType.PAYROLL_APPROVAL:
        from app.models.payroll import PayrollRun, PayrollStatus
        run = db.get(PayrollRun, req.entity_id)
        if run and run.status == PayrollStatus.PENDING_APPROVAL:
            run.status = PayrollStatus.APPROVED
            run.approved_by_id = user.id
            run.approved_at = datetime.now(timezone.utc)
    elif req.entity_type == WorkflowEntityType.COMPENSATION_PLAN:
        from app.services.compensation_service import finalize_plan
        finalize_plan(db, req.entity_id, approved=True, user=user)


def _on_rejected(db: Session, req: ApprovalRequest, user: User, comments: Optional[str]) -> None:
    if req.entity_type == WorkflowEntityType.PAYROLL_APPROVAL:
        from app.models.payroll import PayrollRun, PayrollStatus
        run = db.get(PayrollRun, req.entity_id)
        if run and run.status == PayrollStatus.PENDING_APPROVAL:
            run.status = PayrollStatus.DRAFT
            run.notes = f"Rejected: {comments}"
    elif req.entity_type == WorkflowEntityType.COMPENSATION_PLAN:
        from app.services.compensation_service import finalize_plan
        finalize_plan(db, req.entity_id, approved=False, user=user, reason=comments)
