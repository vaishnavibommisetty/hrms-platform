from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_hr_or_above
from app.models.user import User, UserRole
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeOut
from app.schemas.common import PaginatedResponse
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["Employees"])


def _resolve_company(current_user: User) -> int:
    """All employee operations are scoped to the caller's company."""
    if not current_user.company_id:
        from fastapi import HTTPException
        raise HTTPException(400, "No company associated with your account")
    return current_user.company_id


@router.get("", response_model=PaginatedResponse[EmployeeOut])
def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company_id = _resolve_company(current_user)
    employees, total = employee_service.get_employees(
        db, company_id, page, page_size, search, department_id, status, sort_by, sort_order
    )
    items = [EmployeeOut(**employee_service.enrich_employee(e, db)) for e in employees]
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(items=items, total=total, page=page,
                             page_size=page_size, total_pages=total_pages)


@router.post("", response_model=EmployeeOut, status_code=201)
def create_employee(
    data: EmployeeCreate,
    current_user: User = Depends(get_hr_or_above),
    db: Session = Depends(get_db),
):
    company_id = _resolve_company(current_user)
    emp = employee_service.create_employee(db, data, company_id, current_user)
    return EmployeeOut(**employee_service.enrich_employee(emp, db))


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company_id = _resolve_company(current_user)
    # Employees can only see their own record
    if current_user.role == UserRole.EMPLOYEE:
        from app.models.employee import Employee
        from app.core.database import get_db
        from fastapi import HTTPException
        emp = db.query(Employee).filter(
            Employee.user_id == current_user.id
        ).first()
        if not emp or emp.id != employee_id:
            raise HTTPException(403, "You can only view your own profile")
    emp = employee_service.get_employee_by_id(db, employee_id, company_id)
    return EmployeeOut(**employee_service.enrich_employee(emp, db))


@router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    current_user: User = Depends(get_hr_or_above),
    db: Session = Depends(get_db),
):
    company_id = _resolve_company(current_user)
    emp = employee_service.update_employee(db, employee_id, data, company_id, current_user)
    return EmployeeOut(**employee_service.enrich_employee(emp, db))


@router.delete("/{employee_id}")
def deactivate_employee(
    employee_id: int,
    current_user: User = Depends(get_hr_or_above),
    db: Session = Depends(get_db),
):
    company_id = _resolve_company(current_user)
    employee_service.deactivate_employee(db, employee_id, company_id, current_user)
    return {"message": "Employee deactivated successfully"}
