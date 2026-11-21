from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1._common import ADMIN_ROLES, company_id_of, require, row
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.audit import AuditLog
from app.models.user import User, UserRole

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("")
def list_audit(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
               entity_type: Optional[str] = None, action: Optional[str] = None,
               search: Optional[str] = None,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require(user, ADMIN_ROLES + (UserRole.HR_MANAGER,), "viewing the audit log")
    cid = company_id_of(user)
    q = db.query(AuditLog).filter(AuditLog.company_id == cid)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if action:
        q = q.filter(AuditLog.action == action)
    if search:
        like = f"%{search}%"
        q = q.filter((AuditLog.entity_ref.ilike(like)) | (AuditLog.user_email.ilike(like)))
    total = q.count()
    items = q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()) \
        .offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [row(a, "id", "user_email", "action", "entity_type", "entity_id", "entity_ref",
                      "old_values", "new_values", "created_at") for a in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/filters")
def audit_filters(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    entity_types = [e for (e,) in db.query(AuditLog.entity_type).filter(AuditLog.company_id == cid)
                    .distinct().order_by(AuditLog.entity_type)]
    actions = [a for (a,) in db.query(AuditLog.action).filter(AuditLog.company_id == cid)
               .distinct().order_by(AuditLog.action)]
    return {"entity_types": entity_types, "actions": actions}
