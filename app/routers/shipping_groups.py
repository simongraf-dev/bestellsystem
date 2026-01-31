from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from datetime import date

from app.database import get_db
from app.models import User, ShippingGroup, OrderItem, ApproverSupplier
from app.models.shipping_group import ShippingGroupStatus
from app.schemas.shipping_group import ShippingGroupResponse
from app.utils.security import get_current_user

router = APIRouter(prefix="/shipping-groups", tags=["shipping-groups"])


@router.get("/", response_model=list[ShippingGroupResponse])
def get_shipping_groups(
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Liste aller ShippingGroups.
    - Admin: sieht alle
    - Freigeber: sieht nur ShippingGroups seiner Lieferanten
    """
    query = db.query(ShippingGroup).options(
        joinedload(ShippingGroup.supplier),
        joinedload(ShippingGroup.items).joinedload(OrderItem.article),
        joinedload(ShippingGroup.items).joinedload(OrderItem.supplier)
    )
    
    # Optional: Filter nach Status
    if status:
        query = query.filter(ShippingGroup.status == status)
    
    # Admin sieht alles
    if current_user.role.name != "Admin":
        # Freigeber sieht nur seine Lieferanten
        approved_supplier_ids = db.query(ApproverSupplier.supplier_id).filter(
            ApproverSupplier.user_id == current_user.id
        ).subquery()
        
        query = query.filter(ShippingGroup.supplier_id.in_(approved_supplier_ids))
    
    return query.all()


@router.get("/{id}", response_model=ShippingGroupResponse)
def get_shipping_group(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Detail einer ShippingGroup.
    """
    shipping_group = db.query(ShippingGroup).options(
        joinedload(ShippingGroup.supplier),
        joinedload(ShippingGroup.items).joinedload(OrderItem.article),
        joinedload(ShippingGroup.items).joinedload(OrderItem.supplier)
    ).filter(ShippingGroup.id == id).first()
    
    if not shipping_group:
        raise HTTPException(status_code=404, detail="Versandgruppe nicht gefunden")
    
    # Berechtigung prüfen
    if current_user.role.name != "Admin":
        is_approver = db.query(ApproverSupplier).filter(
            ApproverSupplier.user_id == current_user.id,
            ApproverSupplier.supplier_id == shipping_group.supplier_id
        ).first()
        
        if not is_approver:
            raise HTTPException(status_code=403, detail="Keine Berechtigung für diese Versandgruppe")
    
    return shipping_group


@router.post("/{id}/freigeben", response_model=ShippingGroupResponse)
def freigeben_shipping_group(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ShippingGroup freigeben: OFFEN → VERSENDET
    - Prüft Berechtigung (Admin oder Freigeber für diesen Lieferanten)
    """
    shipping_group = db.query(ShippingGroup).options(
        joinedload(ShippingGroup.supplier),
        joinedload(ShippingGroup.items).joinedload(OrderItem.article),
        joinedload(ShippingGroup.items).joinedload(OrderItem.supplier)
    ).filter(ShippingGroup.id == id).first()
    
    if not shipping_group:
        raise HTTPException(status_code=404, detail="Versandgruppe nicht gefunden")
    
    # Status prüfen
    if shipping_group.status != ShippingGroupStatus.OFFEN:
        raise HTTPException(status_code=400, detail="Versandgruppe ist nicht offen")
    
    if shipping_group.delivery_date and shipping_group.delivery_date < date.today():
        raise HTTPException(status_code=400, detail="Lieferdatum liegt in der Vergangenheit")
    
    # Berechtigung prüfen
    if current_user.role.name != "Admin":
        is_approver = db.query(ApproverSupplier).filter(
            ApproverSupplier.user_id == current_user.id,
            ApproverSupplier.supplier_id == shipping_group.supplier_id
        ).first()
        
        if not is_approver:
            raise HTTPException(status_code=403, detail="Keine Freigabe-Berechtigung für diesen Lieferanten")
    
    # Status ändern
    shipping_group.status = ShippingGroupStatus.VERSENDET
    
    # TODO: Hier später Email/PDF generieren und versenden
    
    db.commit()
    db.refresh(shipping_group)
    
    return shipping_group