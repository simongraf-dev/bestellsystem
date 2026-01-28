from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.models.department import Department
from app.models.user import User
from app.security import get_current_user, require_role
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("/", response_model=list[DepartmentResponse])
def get_all_departments(
    name: Optional[str] = None,
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    query = db.query(Department).options(
        joinedload(Department.parent),
        joinedload(Department.children)
    ).filter(Department.is_active == True)
    
    if name:
        query = query.filter(Department.name.ilike(f"%{name}%"))
    return query.all()


@router.get("/{id}", response_model=DepartmentResponse)
def get_department(id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    department = db.query(Department).options(
        joinedload(Department.parent),
        joinedload(Department.children)
    ).filter(Department.id == id, Department.is_active == True).first()
    
    if not department:
        raise HTTPException(status_code=404, detail="Bereich nicht gefunden")
    return department


@router.post("/", response_model=DepartmentResponse)
@require_role(["Admin"])
def create_department(department: DepartmentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Prüfen ob Parent existiert
    if department.parent_id:
        parent = db.query(Department).filter(Department.id == department.parent_id, Department.is_active == True).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent-Bereich nicht gefunden")
    
    new_department = Department(**department.model_dump())
    db.add(new_department)
    db.commit()
    db.refresh(new_department)
    
    # Neu laden mit Relationships
    return db.query(Department).options(
        joinedload(Department.parent),
        joinedload(Department.children)
    ).filter(Department.id == new_department.id).first()


@router.patch("/{id}", response_model=DepartmentResponse)
@require_role(["Admin"])
def update_department(id: UUID, department_update: DepartmentUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    department = db.query(Department).filter(Department.id == id, Department.is_active == True).first()
    if not department:
        raise HTTPException(status_code=404, detail="Bereich nicht gefunden")
    
    # Prüfen ob neuer parent existiert 
    if department_update.parent_id:
        parent = db.query(Department).filter(Department.id == department_update.parent_id, Department.is_active == True).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent-Bereich nicht gefunden")
        # Sich selbst als Parent verhindern
        if department_update.parent_id == id:
            raise HTTPException(status_code=400, detail="Bereich kann nicht sein eigener Parent sein")
    
    update_data = department_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(department, field, value)
    
    db.commit()
    
    return db.query(Department).options(
        joinedload(Department.parent),
        joinedload(Department.children)
    ).filter(Department.id == id).first()


@router.delete("/{id}")
@require_role(["Admin"])
def delete_department(id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    department = db.query(Department).options(
        joinedload(Department.children)
    ).filter(Department.id == id, Department.is_active == True).first()
    
    if not department:
        raise HTTPException(status_code=404, detail="Bereich nicht gefunden")
    if department.children:
        raise HTTPException(status_code=400, detail="Bereich hat aktive Unterbereiche")
    
    department.is_active = False
    db.commit()
    return {"message": "Bereich gelöscht"}