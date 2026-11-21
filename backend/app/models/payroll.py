from sqlalchemy import (Column, Integer, String, Boolean, DateTime, ForeignKey,
                        Enum as SAEnum, Numeric, Text, UniqueConstraint, JSON)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class PayrollStatus(str, enum.Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PAID = "paid"
    CANCELLED = "cancelled"


class PayrollRun(Base):
    """
    One payroll run per month per company.
    Contains all payslips for that period.
    """
    __tablename__ = "payroll_runs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    month = Column(Integer, nullable=False)   # 1–12
    year = Column(Integer, nullable=False)
    status = Column(SAEnum(PayrollStatus), default=PayrollStatus.DRAFT)

    # Aggregates — computed when processing
    total_employees = Column(Integer, nullable=True)
    total_gross = Column(Numeric(15, 2), nullable=True)
    total_deductions = Column(Numeric(15, 2), nullable=True)
    total_net = Column(Numeric(15, 2), nullable=True)
    total_bonus = Column(Numeric(15, 2), nullable=True)

    processed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("company_id", "month", "year", name="uq_payroll_month_year"),
    )

    company = relationship("Company", back_populates="payroll_runs")
    payslips = relationship("Payslip", back_populates="payroll_run", cascade="all, delete-orphan")


class Payslip(Base):
    """Individual employee payslip for a payroll run."""
    __tablename__ = "payslips"

    id = Column(Integer, primary_key=True, index=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    # Calculated amounts
    gross_salary = Column(Numeric(12, 2), nullable=False)
    total_earnings = Column(Numeric(12, 2), nullable=False)
    total_deductions = Column(Numeric(12, 2), nullable=False)
    net_salary = Column(Numeric(12, 2), nullable=False)
    bonus = Column(Numeric(12, 2), default=0)

    # Leave adjustments
    unpaid_leave_days = Column(Numeric(5, 2), default=0)
    unpaid_leave_deduction = Column(Numeric(12, 2), default=0)

    working_days = Column(Integer, nullable=True)
    paid_days = Column(Numeric(5, 2), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("payroll_run_id", "employee_id", name="uq_payslip_run_employee"),
    )

    payroll_run = relationship("PayrollRun", back_populates="payslips")
    employee = relationship("Employee", back_populates="payslips")
    items = relationship("PayslipItem", back_populates="payslip", cascade="all, delete-orphan")


class PayslipItem(Base):
    """
    Line items on a payslip — one row per salary component.
    E.g. Basic: ₹20,000 | HRA: ₹10,000 | PF Deduction: ₹2,400
    """
    __tablename__ = "payslip_items"

    id = Column(Integer, primary_key=True, index=True)
    payslip_id = Column(Integer, ForeignKey("payslips.id"), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey("salary_components.id"), nullable=True)
    component_name = Column(String(100), nullable=False)   # Stored for history
    component_type = Column(String(20), nullable=False)    # earning / deduction
    amount = Column(Numeric(12, 2), nullable=False)
    sequence = Column(Integer, default=1)

    payslip = relationship("Payslip", back_populates="items")
