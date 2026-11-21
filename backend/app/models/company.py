from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(20), unique=True, nullable=False, index=True)
    industry = Column(String(100))
    address = Column(Text)
    phone = Column(String(20))
    email = Column(String(200))
    website = Column(String(200))
    logo_url = Column(String(500))
    subscription_plan = Column(String(50), default="standard")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="company", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="company", cascade="all, delete-orphan")
    salary_components = relationship("SalaryComponent", back_populates="company")
    salary_structures = relationship("SalaryStructure", back_populates="company")
    compensation_cycles = relationship("CompensationCycle", back_populates="company")
    performance_cycles = relationship("PerformanceCycle", back_populates="company")
    payroll_runs = relationship("PayrollRun", back_populates="company")
    workflow_definitions = relationship("WorkflowDefinition", back_populates="company")
    test_plans = relationship("TestPlan", back_populates="company")
    audit_logs = relationship("AuditLog", back_populates="company")
    compensation_rules = relationship("CompensationRule", back_populates="company")

    def __repr__(self):
        return f"<Company id={self.id} code={self.code} name={self.name}>"
