from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_hr_or_above
from app.models.employee import Department, Designation, Employee
from app.models.user import User
from app.schemas.employee import DepartmentCreate, DepartmentUpdate, DepartmentOut, DesignationCreate, DesignationOut
from app.services.audit_service import log_action

router = APIRouter(prefix="/departments", tags=["Departments & Designations"])


def _company_id(user: User) -> int:
    if not user.company_id:
        raise HTTPException(400, "No company associated with your account")
    return user.company_id


@router.get("/", response_model=List[DepartmentOut])
def list_departments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company_id = _company_id(current_user)
    depts = db.query(Department).filter(
        Department.company_id == company_id,
        Department.is_active == True,
    ).all()
    result = []
    for d in depts:
        emp_count = db.query(Employee).filter(
            Employee.department_id == d.id, Employee.is_active == True
        ).count()
        out = DepartmentOut.model_validate(d)
        out.employee_count = emp_count
        result.append(out)
    return result


@router.post("/", response_model=DepartmentOut, status_code=201)
def create_department(
    data: DepartmentCreate,
    current_user: User = Depends(get_hr_or_above),
    db: Session = Depends(get_db),
):
    company_id = _company_id(current_user)
    # Check code uniqueness within company
    if db.query(Department).filter(
        Department.company_id == company_id,
        Department.code == data.code.upper()
    ).first():
        raise HTTPException(400, f"Department code '{data.code}' already exists")

    dept = Department(
        company_id=company_id,
        name=data.name,
        code=data.code.upper(),
        description=data.description,
    )
    db.add(dept)
    log_action(db, "department.create", "department",
               entity_ref=data.name, user=current_user, company_id=company_id)
    db.commit()
    db.refresh(dept)
    out = DepartmentOut.model_validate(dept)
    out.employee_count = 0
    return out


@router.put("/{dept_id}", response_model=DepartmentOut)
def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    current_user: User = Depends(get_hr_or_above),
    db: Session = Depends(get_db),
):
    company_id = _company_id(current_user)
    dept = db.query(Department).filter(
        Department.id == dept_id,
        Department.company_id == company_id,
    ).first()
    if not dept:
        raise HTTPException(404, "Department not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(dept, key, value)

    db.commit()
    db.refresh(dept)
    out = DepartmentOut.model_validate(dept)
    out.employee_count = db.query(Employee).filter(
        Employee.department_id == dept_id, Employee.is_active == True
    ).count()
    return out


@router.get("/{dept_id}/designations", response_model=List[DesignationOut])
def list_designations(
    dept_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company_id = _company_id(current_user)
    return db.query(Designation).filter(
        Designation.department_id == dept_id,
        Designation.company_id == company_id,
    ).all()


@router.post("/{dept_id}/designations", response_model=DesignationOut, status_code=201)
def create_designation(
    dept_id: int,
    data: DesignationCreate,
    current_user: User = Depends(get_hr_or_above),
    db: Session = Depends(get_db),
):
    company_id = _company_id(current_user)
    # Validate department
    dept = db.query(Department).filter(
        Department.id == dept_id,
        Department.company_id == company_id
    ).first()
    if not dept:
        raise HTTPException(404, "Department not found")

    desig = Designation(
        company_id=company_id,
        department_id=dept_id,
        name=data.name,
        level=data.level,
    )
    db.add(desig)
    db.commit()
    db.refresh(desig)
    return desig
