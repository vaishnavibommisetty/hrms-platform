from sqlalchemy import (Column, Integer, String, Boolean, DateTime, ForeignKey,
                        Enum as SAEnum, Text, JSON)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class WorkflowEntityType(str, enum.Enum):
    SALARY_INCREMENT = "salary_increment"
    PAYROLL_APPROVAL = "payroll_approval"
    COMPENSATION_PLAN = "compensation_plan"
    EMPLOYEE_CREATION = "employee_creation"
    LEAVE_REQUEST = "leave_request"


class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ActionType(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFICATION_REQUESTED = "modification_requested"
    FORWARDED = "forwarded"


class WorkflowDefinition(Base):
    """
    Company-configurable approval workflow template.
    stages_config is a JSON array: [{"stage":1,"role":"hr_manager","label":"HR Review"}, ...]
    Companies can define different workflows for different entity types.
    """
    __tablename__ = "workflow_definitions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    entity_type = Column(SAEnum(WorkflowEntityType), nullable=False)
    stages_config = Column(JSON, nullable=False)  # [{stage, role, label}, ...]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    company = relationship("Company", back_populates="workflow_definitions")
    requests = relationship("ApprovalRequest", back_populates="workflow")


class ApprovalRequest(Base):
    """An approval workflow instance triggered for a specific entity."""
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    workflow_id = Column(Integer, ForeignKey("workflow_definitions.id"), nullable=False)
    entity_type = Column(SAEnum(WorkflowEntityType), nullable=False)
    entity_id = Column(Integer, nullable=False)   # ID of the thing being approved
    entity_ref = Column(String(200))              # Human-readable label
    current_stage = Column(Integer, default=1)
    total_stages = Column(Integer, nullable=False)
    status = Column(SAEnum(RequestStatus), default=RequestStatus.PENDING)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    workflow = relationship("WorkflowDefinition", back_populates="requests")
    actions = relationship("ApprovalAction", back_populates="request",
                           cascade="all, delete-orphan", order_by="ApprovalAction.created_at")


class ApprovalAction(Base):
    """A single approver's action on an approval request."""
    __tablename__ = "approval_actions"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("approval_requests.id"), nullable=False, index=True)
    stage_number = Column(Integer, nullable=False)
    stage_label = Column(String(100))
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(SAEnum(ActionType), nullable=False)
    comments = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    request = relationship("ApprovalRequest", back_populates="actions")
