from sqlalchemy import (Column, Integer, String, Boolean, DateTime, ForeignKey,
                        Enum as SAEnum, Numeric, Text, UniqueConstraint, CheckConstraint)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class ComponentType(str, enum.Enum):
    EARNING = "earning"
    DEDUCTION = "deduction"


class CalculationType(str, enum.Enum):
    FIXED = "fixed"
    PERCENTAGE_OF_BASIC = "percentage_of_basic"
    PERCENTAGE_OF_GROSS = "percentage_of_gross"


class SalaryComponent(Base):
    """Master list of salary components (HRA, Basic, PF, etc.) — per company."""
    __tablename__ = "salary_components"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False)  # e.g. BASIC, HRA, PF
    component_type = Column(SAEnum(ComponentType), nullable=False)
    calculation_type = Column(SAEnum(CalculationType), nullable=False)
    is_taxable = Column(Boolean, default=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_component_company_code"),
    )

    company = relationship("Company", back_populates="salary_components")
    structure_components = relationship("SalaryStructureComponent", back_populates="component")


class SalaryStructure(Base):
    """
    A named salary template (e.g. 'Software Engineer Band 1').
    Companies can have multiple structures.
    Version-controlled — never overwrite, always create new version.
    """
    __tablename__ = "salary_structures"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    effective_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    company = relationship("Company", back_populates="salary_structures")
    components = relationship("SalaryStructureComponent", back_populates="structure",
                              cascade="all, delete-orphan")
    employee_assignments = relationship("EmployeeSalaryAssignment", back_populates="structure")


class SalaryStructureComponent(Base):
    """
    Links a component to a structure with a specific value/percentage.
    E.g. Basic = 50% of gross, HRA = 30% of basic, PF = fixed 1800.
    """
    __tablename__ = "salary_structure_components"

    id = Column(Integer, primary_key=True, index=True)
    structure_id = Column(Integer, ForeignKey("salary_structures.id"), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey("salary_components.id"), nullable=False)
    value = Column(Numeric(8, 4), nullable=False)
    # For PERCENTAGE_OF_BASIC/GROSS: value = 50.0000 means 50%
    # For FIXED: value = 1800.0000 means ₹1800
    sequence = Column(Integer, default=1)  # Calculation order

    __table_args__ = (
        UniqueConstraint("structure_id", "component_id", name="uq_struct_component"),
        CheckConstraint("value >= 0", name="ck_component_value_positive"),
    )

    structure = relationship("SalaryStructure", back_populates="components")
    component = relationship("SalaryComponent", back_populates="structure_components")


class EmployeeSalaryAssignment(Base):
    """
    Assigns a salary structure to an employee with a gross CTC.
    Historical: multiple records per employee (one per change).
    """
    __tablename__ = "employee_salary_assignments"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    structure_id = Column(Integer, ForeignKey("salary_structures.id"), nullable=False)
    gross_ctc = Column(Numeric(12, 2), nullable=False)
    effective_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)  # NULL = current
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    employee = relationship("Employee", back_populates="salary_assignments")
    structure = relationship("SalaryStructure", back_populates="employee_assignments")
