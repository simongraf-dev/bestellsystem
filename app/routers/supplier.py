from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.models.supplier import Supplier
from app.models.user import User
from app.security import get_current_user, require_role
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierResponse

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("/", response_model=list[SupplierResponse])
def get_all_suppliers(
    name: Optional[str] = None,
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    query = db.query(Supplier).filter(Supplier.is_active == True)
    if name:
        query = query.filter(Supplier.name.ilike(f"%{name}%"))
    return query.all()


@router.get("/{id}", response_model=SupplierResponse)
def get_supplier(id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == id, Supplier.is_active == True).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden")
    return supplier


@router.post("/", response_model=SupplierResponse)
@require_role(["Admin"])
def create_supplier(supplier: SupplierCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_supplier = Supplier(**supplier.model_dump())
    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)
    return new_supplier


@router.patch("/{id}", response_model=SupplierResponse)
@require_role(["Admin"])
def update_supplier(id: UUID, supplier_update: SupplierUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == id, Supplier.is_active == True).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden")
    
    update_data = supplier_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)
    
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{id}")
@require_role(["Admin"])
def delete_supplier(id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == id, Supplier.is_active == True).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden")
    
    supplier.is_active = False
    db.commit()
    return {"message": "Lieferant gelöscht"}