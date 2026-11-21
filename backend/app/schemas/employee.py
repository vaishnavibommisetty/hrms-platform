from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime
from app.models.employee import EmploymentStatus, EmploymentType, Gender


class DepartmentCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentOut(BaseModel):
    id: int
    company_id: int
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool
    employee_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class DesignationCreate(BaseModel):
    name: str
    level: int = 1
    department_id: int


class DesignationOut(BaseModel):
    id: int
    name: str
    level: int
    department_id: int

    model_config = {"from_attributes": True}


class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    department_id: int
    designation_id: Optional[int] = None
    manager_id: Optional[int] = None
    joining_date: date
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    gross_ctc: Optional[float] = None
    # Optionally create login credentials
    create_login: bool = False
    login_password: Optional[str] = None


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    manager_id: Optional[int] = None
    employment_type: Optional[EmploymentType] = None
    status: Optional[EmploymentStatus] = None
    gross_ctc: Optional[float] = None
    leaving_date: Optional[date] = None


class EmployeeOut(BaseModel):
    id: int
    company_id: int
    employee_code: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    department_id: int
    department_name: Optional[str] = None
    designation_id: Optional[int] = None
    designation_name: Optional[str] = None
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    joining_date: date
    employment_type: EmploymentType
    status: EmploymentStatus
    gross_ctc: Optional[float] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
