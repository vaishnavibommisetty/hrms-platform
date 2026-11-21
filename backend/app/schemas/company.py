from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class CompanyCreate(BaseModel):
    name: str
    code: str
    industry: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    # Admin user details
    admin_name: str
    admin_email: EmailStr
    admin_password: str


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyOut(BaseModel):
    id: int
    name: str
    code: str
    industry: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    is_active: bool
    created_at: datetime
    employee_count: Optional[int] = None

    model_config = {"from_attributes": True}
