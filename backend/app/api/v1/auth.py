from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut, ChangePasswordRequest
from app.core.security import hash_password
from app.services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email, User.is_active == True).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    log_action(db, "user.login", "user", entity_id=user.id,
               entity_ref=user.email, user=user)
    db.commit()

    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "company_id": user.company_id,
    }
    access_token = create_access_token(token_data)

    company_name = None
    if user.company_id:
        from app.models.company import Company
        company = db.query(Company).filter(Company.id == user.company_id).first()
        company_name = company.name if company else None

    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        company_id=user.company_id,
        company_name=company_name,
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(400, "Current password is incorrect")
    if len(data.new_password) < 8:
        raise HTTPException(400, "New password must be at least 8 characters")
    current_user.hashed_password = hash_password(data.new_password)
    log_action(db, "user.change_password", "user", entity_id=current_user.id,
               user=current_user)
    db.commit()
    return {"message": "Password changed successfully"}
