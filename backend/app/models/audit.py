from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class AuditLog(Base):
    """
    Immutable audit trail of all important actions in the system.
    Never update or delete audit records.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    # nullable — platform admin actions may not belong to a company

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_email = Column(String(200))  # Stored directly for history (user may be deleted)

    action = Column(String(100), nullable=False, index=True)
    # e.g. "employee.create", "salary.update", "payroll.approve"

    entity_type = Column(String(100), nullable=False, index=True)
    # e.g. "employee", "salary_structure", "payroll_run"

    entity_id = Column(Integer, nullable=True)
    entity_ref = Column(String(200))  # Human-readable label

    old_values = Column(JSON, nullable=True)   # State before change
    new_values = Column(JSON, nullable=True)   # State after change

    ip_address = Column(String(45))   # IPv4 or IPv6
    user_agent = Column(String(500))

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        nullable=False, index=True)

    company = relationship("Company", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog id={self.id} action={self.action} entity={self.entity_type}/{self.entity_id}>"
