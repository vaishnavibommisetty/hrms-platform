from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    full_name: str
    role: UserRole
    company_id: Optional[int] = None
    company_name: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    company_id: Optional[int] = None
    is_active: bool

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
