from sqlalchemy.orm import Session
from typing import Optional, Any
from app.models.audit import AuditLog
from app.models.user import User


def log_action(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    entity_ref: Optional[str] = None,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    user: Optional[User] = None,
    company_id: Optional[int] = None,
    ip_address: Optional[str] = None,
):
    """Create an audit log entry. Call this for every important action."""
    entry = AuditLog(
        company_id=company_id or (user.company_id if user else None),
        user_id=user.id if user else None,
        user_email=user.email if user else "system",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_ref=entity_ref,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
    )
    db.add(entry)
    # Note: caller must commit the session
    return entry
