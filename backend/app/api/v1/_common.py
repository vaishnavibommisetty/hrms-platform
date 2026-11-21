"""Small helpers shared by the module routers."""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from fastapi import HTTPException

from app.models.user import User, UserRole

HR_ROLES = (UserRole.PLATFORM_ADMIN, UserRole.COMPANY_ADMIN, UserRole.HR_MANAGER)
FINANCE_ROLES = (UserRole.PLATFORM_ADMIN, UserRole.COMPANY_ADMIN, UserRole.FINANCE_MANAGER)
ADMIN_ROLES = (UserRole.PLATFORM_ADMIN, UserRole.COMPANY_ADMIN)


def company_id_of(user: User) -> int:
    """Every module call is scoped to the caller's company (multi-tenant isolation)."""
    if not user.company_id:
        raise HTTPException(400, "No company associated with your account")
    return user.company_id


def require(user: User, roles: tuple, what: str = "this action") -> None:
    if user.role not in roles:
        allowed = ", ".join(r.value.replace("_", " ") for r in roles if r != UserRole.PLATFORM_ADMIN)
        raise HTTPException(403, f"Only {allowed} can perform {what}")


def jsonable(value: Any) -> Any:
    """Convert DB values (Decimal, enums, dates) to JSON-friendly values."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def row(obj: Any, *fields: str) -> dict:
    return {f: jsonable(getattr(obj, f)) for f in fields}


def money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))
