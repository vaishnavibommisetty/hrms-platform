from sqlalchemy import (Column, Integer, String, Boolean, DateTime, ForeignKey,
                        Enum as SAEnum, Numeric, Text, CheckConstraint)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class CycleStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PlanStatus(str, enum.Enum):
    PENDING = "pending"
    MANAGER_REVIEW = "manager_review"
    HR_REVIEW = "hr_review"
    FINANCE_REVIEW = "finance_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class CompensationCycle(Base):
    """Annual compensation planning cycle."""
    __tablename__ = "compensation_cycles"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)  # e.g. "FY 2024-25 Annual Review"
    year = Column(Integer, nullable=False)
    status = Column(SAEnum(CycleStatus), default=CycleStatus.DRAFT)
    total_budget = Column(Numeric(15, 2), nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    company = relationship("Company", back_populates="compensation_cycles")
    plans = relationship("CompensationPlan", back_populates="cycle", cascade="all, delete-orphan")


class CompensationRule(Base):
    """
    Configurable rules for automatic increment recommendations.
    E.g.: performance_score >= 90 → recommend 15% increment.
    """
    __tablename__ = "compensation_rules"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)  # e.g. "Excellent Performer"
    min_score = Column(Numeric(5, 2), nullable=False)
    max_score = Column(Numeric(5, 2), nullable=False)
    recommended_increment_pct = Column(Numeric(5, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("min_score >= 0 AND max_score <= 100", name="ck_score_range"),
        CheckConstraint("min_score < max_score", name="ck_score_order"),
        CheckConstraint("recommended_increment_pct >= 0", name="ck_increment_positive"),
    )

    company = relationship("Company", back_populates="compensation_rules")


class CompensationPlan(Base):
    """Per-employee compensation recommendation within a cycle."""
    __tablename__ = "compensation_plans"

    id = Column(Integer, primary_key=True, index=True)
    cycle_id = Column(Integer, ForeignKey("compensation_cycles.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    current_salary = Column(Numeric(12, 2), nullable=False)
    performance_score = Column(Numeric(5, 2), nullable=True)

    # Recommended by system (based on rules)
    system_recommended_pct = Column(Numeric(5, 2), nullable=True)
    system_recommended_salary = Column(Numeric(12, 2), nullable=True)

    # Manager adjustment
    manager_recommended_pct = Column(Numeric(5, 2), nullable=True)
    manager_recommended_salary = Column(Numeric(12, 2), nullable=True)
    manager_notes = Column(Text)
    manager_reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    manager_reviewed_at = Column(DateTime, nullable=True)

    # Final (after all approvals)
    final_increment_pct = Column(Numeric(5, 2), nullable=True)
    final_new_salary = Column(Numeric(12, 2), nullable=True)
    bonus_amount = Column(Numeric(12, 2), nullable=True)

    status = Column(SAEnum(PlanStatus), default=PlanStatus.PENDING)
    rejection_reason = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    cycle = relationship("CompensationCycle", back_populates="plans")
    employee = relationship("Employee", back_populates="compensation_plans")
