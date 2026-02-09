from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.orm import Session, joinedload

from app.models import User, Article, Department, Supplier, DepartmentSupplier
from app.schemas.department_supplier import DepartmentSupplierCreate, DepartmentSupplierResponse, DepartmentSupplierUpdate

from app.database import get_db
from app.utils.security import get_current_user
from app.utils.security import require_role

router = APIRouter(prefix="/department-suppliers", tags=["department-suppliers"])

@router.get("/", response_model=list[DepartmentSupplierResponse])
def get_department_supplier(
                        department_id: Optional[UUID] = None,
                        supplier_id: Optional[UUID] = None,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)
):
    query = db.query(DepartmentSupplier).options(
        joinedload(DepartmentSupplier.department),
        joinedload(DepartmentSupplier.supplier)
    )
    if department_id:
        query = query.filter(DepartmentSupplier.department_id == department_id)
    if supplier_id:
        query = query.filter(DepartmentSupplier.supplier_id == supplier_id)
    return query.all()

@router.patch("/{id}", response_model=DepartmentSupplierResponse)
@require_role(["Admin"])
def update_department_supplier(
                    request: DepartmentSupplierUpdate,
                    id: UUID,
                    db: Session = Depends(get_db),
                    current_user: User = (get_current_user)
):
    department_supplier = db.query(DepartmentSupplier).options(
        joinedload(DepartmentSupplier.department),
        joinedload(DepartmentSupplier.supplier)
        ).filter(DepartmentSupplier.id == id).first()
    
    if not department_supplier:
        raise HTTPException(status_code=404, detail="Bereich/Lieferanten Verknüpfung nicht gefunden")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(department_supplier, field, value)
    
    db.commit()
    db.refresh(department_supplier)
    return department_supplier

@router.delete("/{id}")
@require_role(["Admin"])
def delete_article_supplier(
                id: UUID,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user) 
):
    department_supplier = db.query(DepartmentSupplier).filter(DepartmentSupplier.id == id).first()
    if not department_supplier:
        raise HTTPException(status_code=404, detail="Bereich/Lieferanten Verknüpfung nicht gefunden")
    
    db.delete(department_supplier)
    db.commit()
    return {"message": "Verknüpfung wurde gelöscht"}


    
@router.post("/", response_model=DepartmentSupplierResponse)
@require_role(["Admin"])
def create_department_supplier(
                        request: DepartmentSupplierCreate,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)
):  
    # Check auf bestehende Kombination
    existing_combination = db.query(DepartmentSupplier
                                    ).filter(DepartmentSupplier.department_id == request.department_id,
                                             DepartmentSupplier.supplier_id == request.supplier_id).first()
    if existing_combination:
        raise HTTPException(status_code=409, detail="Verknüpfung exisstiert bereits")
    
    department = db.query(Department).filter(Department.id == request.department_id, Department.is_active == True).first()
    if not department:
        raise HTTPException(status_code=404, detail="Bereich nicht gefunden")
    supplier = db.query(Supplier).filter(Supplier.id == request.supplier_id, Supplier.is_active == True).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden")
    
    new_department_supplier = DepartmentSupplier(
        department_id=request.department_id,
        supplier_id=request.supplier_id,
        customer_number=request.customer_number
    )

    db.add(new_department_supplier)
    db.commit()
    db.refresh(new_department_supplier)

    return db.query(DepartmentSupplier).options(
        joinedload(DepartmentSupplier.department),
        joinedload(DepartmentSupplier.supplier)
        ).filter(DepartmentSupplier.id == new_department_supplier.id).first()