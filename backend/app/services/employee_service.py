from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, Tuple, List
from fastapi import HTTPException
from app.models.employee import Employee, Department, Designation, EmploymentStatus
from app.models.user import User, UserRole
from app.models.company import Company
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.core.security import hash_password
from app.services.audit_service import log_action


def generate_employee_code(db: Session, company_id: int, company_code: str) -> str:
    """Generate a unique sequential employee code per company. e.g. ABC-0042"""
    count = db.query(func.count(Employee.id)).filter(
        Employee.company_id == company_id
    ).scalar()
    return f"{company_code}-{(count + 1):04d}"


def get_employees(
    db: Session,
    company_id: int,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Tuple[List[Employee], int]:
    query = db.query(Employee).filter(
        Employee.company_id == company_id,
        Employee.is_active == True,
    )

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Employee.first_name.ilike(search_term),
                Employee.last_name.ilike(search_term),
                Employee.email.ilike(search_term),
                Employee.employee_code.ilike(search_term),
            )
        )

    if department_id:
        query = query.filter(Employee.department_id == department_id)

    if status:
        query = query.filter(Employee.status == status)

    # Sorting
    if sort_by not in Employee.__table__.columns:
        sort_by = "created_at"
    sort_col = getattr(Employee, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_employee_by_id(db: Session, employee_id: int, company_id: int) -> Employee:
    emp = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.company_id == company_id,
        Employee.is_active == True,
    ).first()
    if not emp:
        raise HTTPException(404, f"Employee {employee_id} not found")
    return emp


def create_employee(
    db: Session,
    data: EmployeeCreate,
    company_id: int,
    current_user: User,
) -> Employee:
    # Validate department belongs to company
    dept = db.query(Department).filter(
        Department.id == data.department_id,
        Department.company_id == company_id,
    ).first()
    if not dept:
        raise HTTPException(400, "Department not found in this company")

    # Validate designation if provided
    if data.designation_id:
        desig = db.query(Designation).filter(
            Designation.id == data.designation_id,
            Designation.company_id == company_id,
        ).first()
        if not desig:
            raise HTTPException(400, "Designation not found in this company")

    # Validate manager if provided
    if data.manager_id:
        manager = db.query(Employee).filter(
            Employee.id == data.manager_id,
            Employee.company_id == company_id,
        ).first()
        if not manager:
            raise HTTPException(400, "Manager not found in this company")

    # Get company for code generation
    company = db.query(Company).filter(Company.id == company_id).first()
    employee_code = generate_employee_code(db, company_id, company.code)

    # Check email uniqueness within company
    existing = db.query(Employee).filter(
        Employee.email == data.email,
        Employee.company_id == company_id,
        Employee.is_active == True,
    ).first()
    if existing:
        raise HTTPException(400, f"An employee with email {data.email} already exists in this company")

    # Create user account if requested
    user_id = None
    if data.create_login and data.login_password:
        # Check global email uniqueness for user accounts
        existing_user = db.query(User).filter(User.email == data.email).first()
        if existing_user:
            raise HTTPException(400, f"A user account with email {data.email} already exists")
        new_user = User(
            company_id=company_id,
            email=data.email,
            hashed_password=hash_password(data.login_password),
            full_name=f"{data.first_name} {data.last_name}",
            role=UserRole.EMPLOYEE,
        )
        db.add(new_user)
        db.flush()  # Get the user ID
        user_id = new_user.id

    employee = Employee(
        company_id=company_id,
        user_id=user_id,
        employee_code=employee_code,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        gender=data.gender,
        date_of_birth=data.date_of_birth,
        address=data.address,
        emergency_contact=data.emergency_contact,
        department_id=data.department_id,
        designation_id=data.designation_id,
        manager_id=data.manager_id,
        joining_date=data.joining_date,
        employment_type=data.employment_type,
        gross_ctc=data.gross_ctc,
    )
    db.add(employee)
    db.flush()

    log_action(
        db, "employee.create", "employee",
        entity_id=employee.id,
        entity_ref=f"{employee.full_name} ({employee_code})",
        new_values={"email": data.email, "department_id": data.department_id},
        user=current_user,
        company_id=company_id,
    )
    db.commit()
    db.refresh(employee)
    return employee


def update_employee(
    db: Session,
    employee_id: int,
    data: EmployeeUpdate,
    company_id: int,
    current_user: User,
) -> Employee:
    emp = get_employee_by_id(db, employee_id, company_id)
    old_vals = {
        "department_id": emp.department_id,
        "gross_ctc": float(emp.gross_ctc) if emp.gross_ctc else None,
        "status": emp.status.value if emp.status else None,
    }

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(emp, key, value)

    log_action(
        db, "employee.update", "employee",
        entity_id=emp.id,
        entity_ref=emp.full_name,
        old_values=old_vals,
        new_values=update_data,
        user=current_user,
        company_id=company_id,
    )
    db.commit()
    db.refresh(emp)
    return emp


def deactivate_employee(
    db: Session,
    employee_id: int,
    company_id: int,
    current_user: User,
) -> Employee:
    emp = get_employee_by_id(db, employee_id, company_id)
    emp.is_active = False
    emp.status = EmploymentStatus.INACTIVE

    log_action(
        db, "employee.deactivate", "employee",
        entity_id=emp.id,
        entity_ref=emp.full_name,
        user=current_user,
        company_id=company_id,
    )
    db.commit()
    db.refresh(emp)
    return emp


def enrich_employee(employee: Employee, db: Session) -> dict:
    """Add computed/joined fields to an employee dict for the response."""
    d = {
        "id": employee.id,
        "company_id": employee.company_id,
        "employee_code": employee.employee_code,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "full_name": employee.full_name,
        "email": employee.email,
        "phone": employee.phone,
        "gender": employee.gender,
        "date_of_birth": employee.date_of_birth,
        "department_id": employee.department_id,
        "department_name": employee.department.name if employee.department else None,
        "designation_id": employee.designation_id,
        "designation_name": employee.designation.name if employee.designation else None,
        "manager_id": employee.manager_id,
        "manager_name": employee.manager.full_name if employee.manager else None,
        "joining_date": employee.joining_date,
        "employment_type": employee.employment_type,
        "status": employee.status,
        "gross_ctc": float(employee.gross_ctc) if employee.gross_ctc else None,
        "is_active": employee.is_active,
        "created_at": employee.created_at,
    }
    return d
