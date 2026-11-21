from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .security import decode_token
from app.models.user import User, UserRole

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or deactivated")
    return user


def require_roles(*roles: UserRole):
    """Factory: creates a dependency that restricts access to specified roles."""
    def _check(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in roles]}",
            )
        return current_user
    return _check


# Shorthand dependencies
def get_platform_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.PLATFORM_ADMIN:
        raise HTTPException(403, "Platform admin access required")
    return user


def get_company_admin_or_above(user: User = Depends(get_current_user)) -> User:
    if user.role not in [UserRole.PLATFORM_ADMIN, UserRole.COMPANY_ADMIN]:
        raise HTTPException(403, "Company admin access required")
    return user


def get_hr_or_above(user: User = Depends(get_current_user)) -> User:
    allowed = [UserRole.PLATFORM_ADMIN, UserRole.COMPANY_ADMIN, UserRole.HR_MANAGER]
    if user.role not in allowed:
        raise HTTPException(403, "HR Manager or above required")
    return user
