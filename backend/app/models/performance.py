from sqlalchemy import (Column, Integer, String, Boolean, DateTime, ForeignKey,
                        Enum as SAEnum, Numeric, Text, CheckConstraint, UniqueConstraint)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class ReviewStatus(str, enum.Enum):
    DRAFT = "draft"
    SELF_REVIEW = "self_review"
    MANAGER_REVIEW = "manager_review"
    COMPLETED = "completed"


class PerformanceCycle(Base):
    """A performance review cycle (e.g. H1 2024, Annual 2024)."""
    __tablename__ = "performance_cycles"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    year = Column(Integer, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(SAEnum(ReviewStatus), default=ReviewStatus.DRAFT)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="performance_cycles")
    kpis = relationship("KPI", back_populates="cycle", cascade="all, delete-orphan")
    reviews = relationship("PerformanceReview", back_populates="cycle")


class KPI(Base):
    """
    Key Performance Indicators defined per cycle.
    Companies can customize KPI names and weights.
    Total weights must sum to 100%.
    """
    __tablename__ = "kpis"

    id = Column(Integer, primary_key=True, index=True)
    cycle_id = Column(Integer, ForeignKey("performance_cycles.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    weight_pct = Column(Numeric(5, 2), nullable=False)  # e.g. 40.00 for 40%
    sequence = Column(Integer, default=1)

    __table_args__ = (
        CheckConstraint("weight_pct > 0 AND weight_pct <= 100", name="ck_kpi_weight"),
    )

    cycle = relationship("PerformanceCycle", back_populates="kpis")
    scores = relationship("KPIScore", back_populates="kpi")


class PerformanceReview(Base):
    """An employee's performance review for a cycle."""
    __tablename__ = "performance_reviews"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    cycle_id = Column(Integer, ForeignKey("performance_cycles.id"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # manager

    self_overall_score = Column(Numeric(5, 2), nullable=True)
    manager_overall_score = Column(Numeric(5, 2), nullable=True)
    final_score = Column(Numeric(5, 2), nullable=True)  # Weighted aggregate

    self_comments = Column(Text)
    manager_comments = Column(Text)
    status = Column(SAEnum(ReviewStatus), default=ReviewStatus.DRAFT)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("employee_id", "cycle_id", name="uq_review_emp_cycle"),
    )

    employee = relationship("Employee", back_populates="performance_reviews")
    cycle = relationship("PerformanceCycle", back_populates="reviews")
    kpi_scores = relationship("KPIScore", back_populates="review", cascade="all, delete-orphan")


class KPIScore(Base):
    """Individual KPI score for a performance review."""
    __tablename__ = "kpi_scores"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("performance_reviews.id"), nullable=False, index=True)
    kpi_id = Column(Integer, ForeignKey("kpis.id"), nullable=False)
    self_score = Column(Numeric(5, 2), nullable=True)   # 0–100
    manager_score = Column(Numeric(5, 2), nullable=True)  # 0–100

    __table_args__ = (
        UniqueConstraint("review_id", "kpi_id", name="uq_kpiscores_review_kpi"),
        CheckConstraint("self_score IS NULL OR (self_score >= 0 AND self_score <= 100)",
                        name="ck_self_score_range"),
        CheckConstraint("manager_score IS NULL OR (manager_score >= 0 AND manager_score <= 100)",
                        name="ck_mgr_score_range"),
    )

    review = relationship("PerformanceReview", back_populates="kpi_scores")
    kpi = relationship("KPI", back_populates="scores")
