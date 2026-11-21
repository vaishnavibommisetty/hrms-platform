from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.v1._common import ADMIN_ROLES, company_id_of, jsonable, require, row
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.workflow import (ApprovalAction, ApprovalRequest, RequestStatus, WorkflowDefinition,
                                 WorkflowEntityType)
from app.services import workflow_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/workflows", tags=["Approval Workflows"])

STAGE_ROLES = [r.value for r in UserRole if r not in (UserRole.PLATFORM_ADMIN, UserRole.EMPLOYEE)]


class StageIn(BaseModel):
    role: str
    label: str = Field(min_length=2, max_length=100)


class DefinitionIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    entity_type: WorkflowEntityType
    stages: List[StageIn] = Field(min_length=1, max_length=6)


class ActionIn(BaseModel):
    approve: bool
    comments: Optional[str] = None


def _definition_out(d: WorkflowDefinition) -> dict:
    out = row(d, "id", "name", "entity_type", "is_active", "created_at")
    out["stages"] = sorted(d.stages_config, key=lambda s: s["stage"])
    return out


def _request_out(r: ApprovalRequest, user: User) -> dict:
    out = row(r, "id", "entity_type", "entity_id", "entity_ref", "current_stage", "total_stages",
              "status", "created_at", "completed_at")
    info = workflow_service.stage_info(r)
    out["workflow_name"] = r.workflow.name
    out["stages"] = info["stages"]
    out["current_stage_label"] = (info["current"] or {}).get("label")
    out["current_stage_role"] = (info["current"] or {}).get("role")
    out["can_act"] = workflow_service.can_act(user, r)
    return out


@router.get("/roles")
def stage_roles():
    return STAGE_ROLES


@router.get("/definitions")
def list_definitions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    defs = db.query(WorkflowDefinition).filter(WorkflowDefinition.company_id == cid) \
        .order_by(WorkflowDefinition.is_active.desc(), WorkflowDefinition.id.desc()).all()
    return [_definition_out(d) for d in defs]


@router.post("/definitions", status_code=201)
def create_definition(data: DefinitionIn, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    require(user, ADMIN_ROLES, "workflow configuration")
    cid = company_id_of(user)
    for s in data.stages:
        if s.role not in STAGE_ROLES:
            raise HTTPException(400, f"Unknown role '{s.role}'")
    db.query(WorkflowDefinition).filter(WorkflowDefinition.company_id == cid,
                                        WorkflowDefinition.entity_type == data.entity_type,
                                        WorkflowDefinition.is_active == True) \
        .update({"is_active": False})
    d = WorkflowDefinition(company_id=cid, name=data.name.strip(), entity_type=data.entity_type,
                           created_by_id=user.id, is_active=True,
                           stages_config=[{"stage": i, "role": s.role, "label": s.label.strip()}
                                          for i, s in enumerate(data.stages, start=1)])
    db.add(d)
    db.flush()
    log_action(db, "workflow.create", "workflow_definition", d.id, d.name, user=user,
               new_values={"stages": d.stages_config})
    db.commit()
    return _definition_out(d)


@router.post("/definitions/{definition_id}/toggle")
def toggle_definition(definition_id: int, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    require(user, ADMIN_ROLES, "workflow configuration")
    cid = company_id_of(user)
    d = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == definition_id,
                                            WorkflowDefinition.company_id == cid).first()
    if not d:
        raise HTTPException(404, "Workflow not found")
    if not d.is_active:
        db.query(WorkflowDefinition).filter(WorkflowDefinition.company_id == cid,
                                            WorkflowDefinition.entity_type == d.entity_type) \
            .update({"is_active": False})
    d.is_active = not d.is_active
    db.commit()
    return _definition_out(d)


@router.get("/requests")
def list_requests(status: Optional[str] = Query(None, description="open | closed | all"),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    q = db.query(ApprovalRequest).options(joinedload(ApprovalRequest.workflow)) \
        .filter(ApprovalRequest.company_id == cid)
    if status == "open":
        q = q.filter(ApprovalRequest.status.in_(workflow_service.OPEN_STATUSES))
    elif status == "closed":
        q = q.filter(~ApprovalRequest.status.in_(workflow_service.OPEN_STATUSES))
    return [_request_out(r, user) for r in q.order_by(ApprovalRequest.created_at.desc()).limit(200)]


@router.get("/requests/{request_id}")
def get_request(request_id: int, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    cid = company_id_of(user)
    r = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id,
                                         ApprovalRequest.company_id == cid).first()
    if not r:
        raise HTTPException(404, "Request not found")
    out = _request_out(r, user)
    approvers = {u.id: u for u in db.query(User).filter(
        User.id.in_([a.approver_id for a in r.actions] or [0]))}
    out["actions"] = [{
        "stage_number": a.stage_number,
        "stage_label": a.stage_label,
        "action": a.action.value,
        "comments": a.comments,
        "approver": approvers[a.approver_id].full_name if a.approver_id in approvers else None,
        "created_at": jsonable(a.created_at),
    } for a in r.actions]
    return out


@router.post("/requests/{request_id}/action")
def act_on_request(request_id: int, data: ActionIn, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    cid = company_id_of(user)
    r = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id,
                                         ApprovalRequest.company_id == cid).first()
    if not r:
        raise HTTPException(404, "Request not found")
    workflow_service.act(db, r, user, data.approve, data.comments)
    db.commit()
    return get_request(request_id, user, db)
