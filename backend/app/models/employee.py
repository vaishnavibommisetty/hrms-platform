from sqlalchemy import (Column, Integer, String, Boolean, DateTime,
                        ForeignKey, Date, Enum as SAEnum, Numeric, Text, UniqueConstraint)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class EmploymentStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    RESIGNED = "resigned"
    TERMINATED = "terminated"
    ON_LEAVE = "on_leave"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERN = "intern"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_dept_company_code"),
    )

    company = relationship("Company", back_populates="departments")
    employees = relationship("Employee", back_populates="department")
    designations = relationship("Designation", back_populates="department", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Department id={self.id} name={self.name}>"


class Designation(Base):
    __tablename__ = "designations"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    level = Column(Integer, default=1)  # 1=Junior, 5=Senior, 10=VP
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    department = relationship("Department", back_populates="designations")
    employees = relationship("Employee", back_populates="designation")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    designation_id = Column(Integer, ForeignKey("designations.id"), nullable=True)
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # Identity
    employee_code = Column(String(20), nullable=False)  # Unique per company, e.g. ABC-001
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(200), nullable=False)
    phone = Column(String(20))
    gender = Column(SAEnum(Gender), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    address = Column(Text)
    emergency_contact = Column(String(200))

    # Employment
    joining_date = Column(Date, nullable=False)
    leaving_date = Column(Date, nullable=True)
    employment_type = Column(SAEnum(EmploymentType), default=EmploymentType.FULL_TIME)
    status = Column(SAEnum(EmploymentStatus), default=EmploymentStatus.ACTIVE, nullable=False)

    # Salary (gross CTC — breakdown comes from salary structure)
    gross_ctc = Column(Numeric(12, 2), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("company_id", "employee_code", name="uq_emp_company_code"),
    )

    # Relationships
    company = relationship("Company", back_populates="employees")
    user = relationship("User", back_populates="employee")
    department = relationship("Department", back_populates="employees")
    designation = relationship("Designation", back_populates="employees")
    manager = relationship("Employee", remote_side=[id], foreign_keys=[manager_id])
    reportees = relationship("Employee", foreign_keys=[manager_id], overlaps="manager")
    salary_assignments = relationship("EmployeeSalaryAssignment", back_populates="employee")
    compensation_plans = relationship("CompensationPlan", back_populates="employee")
    performance_reviews = relationship("PerformanceReview", back_populates="employee")
    payslips = relationship("Payslip", back_populates="employee")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Employee id={self.id} code={self.employee_code} name={self.full_name}>"
