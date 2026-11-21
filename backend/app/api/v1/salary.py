from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.v1._common import HR_ROLES, company_id_of, jsonable, require, row
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.employee import Employee
from app.models.salary import (CalculationType, ComponentType, EmployeeSalaryAssignment,
                               SalaryComponent, SalaryStructure, SalaryStructureComponent)
from app.models.user import User
from app.services.audit_service import log_action
from app.services.salary_engine import breakdown_json, calculate_breakdown

router = APIRouter(prefix="/salary", tags=["Salary Structures"])


# ── Schemas ──────────────────────────────────────────────────────────────
class ComponentIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=2, max_length=20)
    component_type: ComponentType
    calculation_type: CalculationType
    is_taxable: bool = True
    description: Optional[str] = None


class StructureLine(BaseModel):
    component_id: int
    value: float = Field(ge=0)
    sequence: int = 1


class StructureIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None
    components: List[StructureLine] = Field(min_length=1)


class AssignmentIn(BaseModel):
    employee_id: int
    structure_id: int
    gross_ctc: float = Field(gt=0)


# ── Helpers ──────────────────────────────────────────────────────────────
def _component_out(c: SalaryComponent) -> dict:
    return row(c, "id", "name", "code", "component_type", "calculation_type", "is_taxable",
               "description", "is_active")


def _structure_out(s: SalaryStructure, db: Session) -> dict:
    current = db.query(EmployeeSalaryAssignment).filter(
        EmployeeSalaryAssignment.structure_id == s.id,
        EmployeeSalaryAssignment.end_date.is_(None),
    ).count()
    out = row(s, "id", "name", "version", "description", "is_active", "effective_date", "created_at")
    out["employee_count"] = current
    out["components"] = [
        {
            "id": sc.id,
            "component_id": sc.component_id,
            "code": sc.component.code,
            "name": sc.component.name,
            "component_type": sc.component.component_type.value,
            "calculation_type": sc.component.calculation_type.value,
            "value": float(sc.value),
            "sequence": sc.sequence,
        }
        for sc in sorted(s.components, key=lambda x: x.sequence or 0)
    ]
    return out


def _get_structure(db: Session, company_id: int, structure_id: int) -> SalaryStructure:
    s = db.query(SalaryStructure).options(
        joinedload(SalaryStructure.components).joinedload(SalaryStructureComponent.component)
    ).filter(SalaryStructure.id == structure_id, SalaryStructure.company_id == company_id).first()
    if not s:
        raise HTTPException(404, "Salary structure not found")
    return s


# ── Components ───────────────────────────────────────────────────────────
@router.get("/components")
def list_components(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    comps = db.query(SalaryComponent).filter(SalaryComponent.company_id == cid) \
        .order_by(SalaryComponent.component_type, SalaryComponent.name).all()
    return [_component_out(c) for c in comps]


@router.post("/components", status_code=201)
def create_component(data: ComponentIn, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    require(user, HR_ROLES, "salary setup")
    cid = company_id_of(user)
    code = data.code.strip().upper()
    if db.query(SalaryComponent).filter(SalaryComponent.company_id == cid,
                                        SalaryComponent.code == code).first():
        raise HTTPException(400, f"Component code '{code}' already exists")
    comp = SalaryComponent(company_id=cid, name=data.name.strip(), code=code,
                           component_type=data.component_type,
                           calculation_type=data.calculation_type,
                           is_taxable=data.is_taxable, description=data.description)
    db.add(comp)
    db.flush()
    log_action(db, "salary_component.create", "salary_component", comp.id, comp.code, user=user)
    db.commit()
    return _component_out(comp)


# ── Structures ───────────────────────────────────────────────────────────
@router.get("/structures")
def list_structures(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    structures = db.query(SalaryStructure).options(
        joinedload(SalaryStructure.components).joinedload(SalaryStructureComponent.component)
    ).filter(SalaryStructure.company_id == cid).order_by(SalaryStructure.name).all()
    return [_structure_out(s, db) for s in structures]


@router.get("/structures/{structure_id}")
def get_structure(structure_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return _structure_out(_get_structure(db, company_id_of(user), structure_id), db)


@router.post("/structures", status_code=201)
def create_structure(data: StructureIn, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    require(user, HR_ROLES, "salary setup")
    cid = company_id_of(user)
    ids = [line.component_id for line in data.components]
    if len(set(ids)) != len(ids):
        raise HTTPException(400, "Each component can appear only once in a structure")
    comps = {c.id: c for c in db.query(SalaryComponent).filter(
        SalaryComponent.company_id == cid, SalaryComponent.id.in_(ids)).all()}
    if len(comps) != len(ids):
        raise HTTPException(400, "One or more components do not belong to your company")
    for line in data.components:
        c = comps[line.component_id]
        if c.calculation_type != CalculationType.FIXED and line.value > 100:
            raise HTTPException(400, f"{c.name}: a percentage cannot exceed 100")

    latest = db.query(SalaryStructure).filter(SalaryStructure.company_id == cid,
                                              SalaryStructure.name == data.name.strip()) \
        .order_by(SalaryStructure.version.desc()).first()
    s = SalaryStructure(company_id=cid, name=data.name.strip(), description=data.description,
                        version=(latest.version + 1) if latest else 1,
                        effective_date=datetime.now(timezone.utc), created_by_id=user.id)
    for line in data.components:
        s.components.append(SalaryStructureComponent(component_id=line.component_id,
                                                     value=line.value, sequence=line.sequence))
    db.add(s)
    db.flush()
    log_action(db, "salary_structure.create", "salary_structure", s.id,
               f"{s.name} v{s.version}", user=user)
    db.commit()
    return _structure_out(_get_structure(db, cid, s.id), db)


@router.get("/structures/{structure_id}/preview")
def preview_structure(structure_id: int, ctc: float = Query(..., gt=0),
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _get_structure(db, company_id_of(user), structure_id)
    return breakdown_json(calculate_breakdown(s, ctc))


# ── Employee assignments ─────────────────────────────────────────────────
@router.get("/assignments")
def list_assignments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = company_id_of(user)
    rows = db.query(EmployeeSalaryAssignment, Employee, SalaryStructure) \
        .join(Employee, Employee.id == EmployeeSalaryAssignment.employee_id) \
        .join(SalaryStructure, SalaryStructure.id == EmployeeSalaryAssignment.structure_id) \
        .filter(Employee.company_id == cid, EmployeeSalaryAssignment.end_date.is_(None),
                Employee.is_active == True) \
        .order_by(Employee.first_name).all()
    return [{
        "id": a.id,
        "employee_id": e.id,
        "employee_code": e.employee_code,
        "employee_name": e.full_name,
        "department": e.department.name if e.department else None,
        "structure_id": s.id,
        "structure_name": f"{s.name} v{s.version}",
        "gross_ctc": float(a.gross_ctc),
        "monthly_gross": round(float(a.gross_ctc) / 12, 2),
        "effective_date": jsonable(a.effective_date),
    } for a, e, s in rows]


@router.post("/assignments", status_code=201)
def assign_structure(data: AssignmentIn, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    require(user, HR_ROLES, "salary assignment")
    cid = company_id_of(user)
    emp = db.query(Employee).filter(Employee.id == data.employee_id,
                                    Employee.company_id == cid).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    structure = _get_structure(db, cid, data.structure_id)
    now = datetime.now(timezone.utc)
    old_ctc = float(emp.gross_ctc) if emp.gross_ctc else None
    db.query(EmployeeSalaryAssignment).filter(
        EmployeeSalaryAssignment.employee_id == emp.id,
        EmployeeSalaryAssignment.end_date.is_(None),
    ).update({"end_date": now})
    a = EmployeeSalaryAssignment(employee_id=emp.id, structure_id=structure.id,
                                 gross_ctc=data.gross_ctc, effective_date=now,
                                 created_by_id=user.id)
    emp.gross_ctc = data.gross_ctc
    db.add(a)
    db.flush()
    log_action(db, "salary.assign", "employee", emp.id, emp.full_name,
               old_values={"gross_ctc": old_ctc},
               new_values={"gross_ctc": data.gross_ctc, "structure": structure.name}, user=user)
    db.commit()
    return {"id": a.id, "employee_id": emp.id, "structure_id": structure.id,
            "gross_ctc": data.gross_ctc}


@router.get("/employees/{employee_id}")
def employee_salary(employee_id: int, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    cid = company_id_of(user)
    emp = db.query(Employee).filter(Employee.id == employee_id, Employee.company_id == cid).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    history = db.query(EmployeeSalaryAssignment).filter(
        EmployeeSalaryAssignment.employee_id == emp.id
    ).order_by(EmployeeSalaryAssignment.effective_date.desc()).all()
    current = next((h for h in history if h.end_date is None), None)
    breakdown = None
    if current:
        s = _get_structure(db, cid, current.structure_id)
        breakdown = breakdown_json(calculate_breakdown(s, current.gross_ctc))
    return {
        "employee_id": emp.id,
        "employee_name": emp.full_name,
        "current": None if not current else {
            "structure_id": current.structure_id,
            "structure_name": current.structure.name,
            "gross_ctc": float(current.gross_ctc),
            "effective_date": jsonable(current.effective_date),
        },
        "breakdown": breakdown,
        "history": [{
            "structure_name": h.structure.name,
            "gross_ctc": float(h.gross_ctc),
            "effective_date": jsonable(h.effective_date),
            "end_date": jsonable(h.end_date),
        } for h in history],
    }
