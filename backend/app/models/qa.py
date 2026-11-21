from sqlalchemy import (Column, Integer, String, Boolean, DateTime, ForeignKey,
                        Enum as SAEnum, Text, UniqueConstraint)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class TestType(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    BOUNDARY = "boundary"
    SECURITY = "security"
    REGRESSION = "regression"


class ExecutionStatus(str, enum.Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class DefectSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DefectPriority(str, enum.Enum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


class DefectStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    VERIFIED = "verified"
    CLOSED = "closed"
    REOPENED = "reopened"
    WONT_FIX = "wont_fix"


class TestPlan(Base):
    __tablename__ = "test_plans"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    module = Column(String(100), nullable=False)   # e.g. "Employee Management"
    description = Column(Text)
    version = Column(String(20), default="1.0")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    company = relationship("Company", back_populates="test_plans")
    test_cases = relationship("TestCase", back_populates="plan", cascade="all, delete-orphan")


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("test_plans.id"), nullable=False, index=True)
    case_id = Column(String(20), nullable=False)  # e.g. TC-001
    title = Column(String(500), nullable=False)
    test_type = Column(SAEnum(TestType), nullable=False)
    preconditions = Column(Text)
    test_steps = Column(Text, nullable=False)
    expected_result = Column(Text, nullable=False)
    module = Column(String(100))
    priority = Column(String(20), default="medium")
    is_automated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    plan = relationship("TestPlan", back_populates="test_cases")
    executions = relationship("TestExecution", back_populates="test_case",
                              cascade="all, delete-orphan")
    defects = relationship("Defect", back_populates="test_case")


class TestExecution(Base):
    __tablename__ = "test_executions"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False, index=True)
    executed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(SAEnum(ExecutionStatus), nullable=False)
    actual_result = Column(Text)
    notes = Column(Text)
    execution_time_ms = Column(Integer, nullable=True)  # How long the test took
    build_version = Column(String(50), nullable=True)   # App version tested against
    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    test_case = relationship("TestCase", back_populates="executions")


class Defect(Base):
    __tablename__ = "defects"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=True)
    defect_id = Column(String(20), nullable=False)  # e.g. BUG-001
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    steps_to_reproduce = Column(Text)
    expected_behaviour = Column(Text)
    actual_behaviour = Column(Text)
    severity = Column(SAEnum(DefectSeverity), nullable=False)
    priority = Column(SAEnum(DefectPriority), nullable=False)
    status = Column(SAEnum(DefectStatus), default=DefectStatus.OPEN)
    module = Column(String(100))
    reported_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    test_case = relationship("TestCase", back_populates="defects")
