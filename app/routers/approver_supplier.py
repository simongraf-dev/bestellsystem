from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.schemas.approver_supplier import ApproverSupplierCreate, ApproverSupplierResponse
from app.database import get_db
from app.utils.security import get_current_user, require_role

from app.models import User, ApproverSupplier, Supplier

router = APIRouter(prefix="/approver-suppliers", tags=["approver-suppliers"])

@router.get("/", response_model=list[ApproverSupplierResponse])
def get_approver_supplier(user_id: Optional[UUID] = None,
                        supplier_id: Optional[UUID] = None,
                        current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)
):
    query = db.query(ApproverSupplier).options(joinedload(ApproverSupplier.user), joinedload(ApproverSupplier.supplier))
    
    if user_id:
        query = query.filter(ApproverSupplier.user_id == user_id)
    if supplier_id:
        query = query.filter(ApproverSupplier.supplier_id == supplier_id)
    
    return query.all()


@router.post("/", response_model=ApproverSupplierResponse)
@require_role(["Admin"])
def create_approver_supplier(approver_data: ApproverSupplierCreate,
                            current_user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == approver_data.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    supplier = db.query(Supplier).filter(Supplier.id == approver_data.supplier_id, Supplier.is_active == True).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden")
    new_approver_supplier= ApproverSupplier(
        user_id=approver_data.user_id,
        supplier_id=approver_data.supplier_id
    )
    existing = db.query(ApproverSupplier).filter(
    ApproverSupplier.user_id == approver_data.user_id,
    ApproverSupplier.supplier_id == approver_data.supplier_id
).first()
    if existing:
        raise HTTPException(status_code=400, detail="Berechtigung existiert bereits")
    db.add(new_approver_supplier)
    db.commit()
    return db.query(ApproverSupplier).options(
        joinedload(ApproverSupplier.user),
        joinedload(ApproverSupplier.supplier)
    ).filter(ApproverSupplier.user_id == approver_data.user_id, ApproverSupplier.supplier_id == approver_data.supplier_id).first()


@router.delete("/")
@require_role(["Admin"])
def delete_approver_supplier(user_id: UUID,
                            supplier_id: UUID,
                            current_user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)
) -> dict:
    approver = db.query(ApproverSupplier).filter(
        ApproverSupplier.user_id == user_id,
        ApproverSupplier.supplier_id == supplier_id
    ).first()
    if not approver:
        raise HTTPException(status_code=404, detail="User-Lieferanten Verknüpfung nicht gefunden")
    db.delete(approver)
    db.commit()
    return {"message": "User-Lieferanten Verknüpfung gelöscht"}