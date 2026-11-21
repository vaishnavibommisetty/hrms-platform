from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_platform_admin
from app.models.company import Company
from app.models.user import User, UserRole
from app.models.employee import Employee
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyOut
from app.core.security import hash_password
from app.services.audit_service import log_action

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("", response_model=List[CompanyOut])
def list_companies(
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    companies = db.query(Company).filter(Company.is_active == True).all()
    result = []
    for c in companies:
        emp_count = db.query(Employee).filter(
            Employee.company_id == c.id, Employee.is_active == True
        ).count()
        out = CompanyOut.model_validate(c)
        out.employee_count = emp_count
        result.append(out)
    return result


@router.post("", response_model=CompanyOut, status_code=201)
def create_company(
    data: CompanyCreate,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    # Check code uniqueness
    if db.query(Company).filter(Company.code == data.code.upper()).first():
        raise HTTPException(400, f"Company code '{data.code}' already exists")
    if db.query(User).filter(User.email == data.admin_email).first():
        raise HTTPException(400, f"User with email '{data.admin_email}' already exists")

    company = Company(
        name=data.name,
        code=data.code.upper(),
        industry=data.industry,
        address=data.address,
        phone=data.phone,
        email=data.email,
        website=data.website,
    )
    db.add(company)
    db.flush()

    admin_user = User(
        company_id=company.id,
        email=data.admin_email,
        hashed_password=hash_password(data.admin_password),
        full_name=data.admin_name,
        role=UserRole.COMPANY_ADMIN,
    )
    db.add(admin_user)
    log_action(db, "company.create", "company", entity_id=company.id,
               entity_ref=company.name, user=current_user)
    db.commit()
    db.refresh(company)
    out = CompanyOut.model_validate(company)
    out.employee_count = 0
    return out


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Users can only see their own company (unless platform admin)
    if current_user.role != UserRole.PLATFORM_ADMIN:
        if current_user.company_id != company_id:
            raise HTTPException(403, "Access denied")

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "Company not found")

    emp_count = db.query(Employee).filter(
        Employee.company_id == company_id, Employee.is_active == True
    ).count()
    out = CompanyOut.model_validate(company)
    out.employee_count = emp_count
    return out


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int,
    data: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in [UserRole.PLATFORM_ADMIN, UserRole.COMPANY_ADMIN]:
        raise HTTPException(403, "Access denied")
    if current_user.role == UserRole.COMPANY_ADMIN and current_user.company_id != company_id:
        raise HTTPException(403, "Cannot modify another company")

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "Company not found")

    old_vals = {"name": company.name, "is_active": company.is_active}
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(company, key, value)

    log_action(db, "company.update", "company", entity_id=company.id,
               entity_ref=company.name, old_values=old_vals,
               new_values=update_data, user=current_user)
    db.commit()
    db.refresh(company)
    out = CompanyOut.model_validate(company)
    out.employee_count = db.query(Employee).filter(
        Employee.company_id == company_id, Employee.is_active == True
    ).count()
    return out
