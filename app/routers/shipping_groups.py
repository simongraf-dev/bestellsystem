import os
from datetime import date
from uuid import UUID
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload


from app.models import User, ShippingGroup, OrderItem, ApproverSupplier, Order
from app.models.shipping_group import ShippingGroupStatus
from app.schemas.shipping_group import ShippingGroupResponse, ShippingGroupDetailResponse, ShippingGroupOrderInfo
from app.models.activity_log import ActionType

from app.database import get_db
from app.services.pdf_service import generate_shipping_group_pdf
from app.services.email_service import send_order_email
from app.utils.security import get_current_user
from app.services.activity_service import log_activity



logger = logging.getLogger("app.routers.shipping_groups")

router = APIRouter(prefix="/shipping-groups", tags=["shipping-groups"])


@router.get("/", response_model=list[ShippingGroupResponse])
def get_shipping_groups(
    status: Optional[ShippingGroupStatus] = None,
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
async def freigeben_shipping_group(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ShippingGroup freigeben: OFFEN → VERSENDET
    - Prüft Berechtigung (Admin oder Freigeber für diesen Lieferanten)
    - Validiert Lieferdatum
    - Generiert PDF und speichert es
    - Sendet Email an Lieferanten
    - ActivityLog
    """
    shipping_group = db.query(ShippingGroup).options(
        joinedload(ShippingGroup.supplier),
        joinedload(ShippingGroup.items).joinedload(OrderItem.article),
        joinedload(ShippingGroup.items).joinedload(OrderItem.supplier),
        joinedload(ShippingGroup.items).joinedload(OrderItem.order).joinedload(Order.department)
    ).filter(ShippingGroup.id == id).first()
    
    if not shipping_group:
        raise HTTPException(status_code=404, detail="Versandgruppe nicht gefunden")
    
    # Status prüfen
    if shipping_group.status != ShippingGroupStatus.OFFEN:
        raise HTTPException(status_code=400, detail="Versandgruppe ist nicht offen")
    
    if not shipping_group.delivery_date:
        raise HTTPException(status_code=400, detail="Kein Lieferdatum gesetzt")
    
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
    
    # Kurzreferenz generieren
    short_id = f"SG-{str(shipping_group.id)[:8].upper()}"
    pdf_path = None
    
    # PDF generieren
    try:
        pdf_bytes = generate_shipping_group_pdf(
            db=db,
            shipping_group=shipping_group,
            approved_by=current_user.name
        )
        
        # Pfad erstellen: storage/pdfs/2026/02/SG-A7F3B2.pdf
        today = date.today()
        pdf_dir = f"storage/pdfs/{today.year}/{today.month:02d}"
        os.makedirs(pdf_dir, exist_ok=True)
        
        pdf_filename = f"{short_id}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        # PDF speichern
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        
        # Pfad in DB speichern
        shipping_group.pdf_path = pdf_path
        
    except Exception as e:
        logger.warning(f"PDF-Generierung fehlgeschlagen: {e}")
    
    # Email versenden (nur wenn Lieferant Email hat)
    if shipping_group.supplier and shipping_group.supplier.email and pdf_path:
        try:
            email_sent = await send_order_email(
                to_email=shipping_group.supplier.email,
                supplier_name=shipping_group.supplier.name,
                delivery_date=shipping_group.delivery_date,
                pdf_path=pdf_path,
                order_reference=short_id
            )
            if not email_sent:
                logger.warning(f"Email an {shipping_group.supplier.email} konnte nicht gesendet werden")
        except Exception as e:
            logger.warning(f"Email-Versand fehlgeschlagen: {e}")
    
    # Status ändern
    shipping_group.status = ShippingGroupStatus.VERSENDET
    shipping_group.sender_id = current_user.id
    shipping_group.send_date = date.today()
    
    db.commit()
    db.refresh(shipping_group)
    log_activity(
        db=db,
        entity_type="shipping_group", 
        entity_id=shipping_group.id,
        user_id=current_user.id,
        action_type=ActionType.ORDER_SENT,
        description="Bestellung an Lieferant versendet",
        details={
            "supplier_id": str(shipping_group.supplier_id),
            "delivery_date": str(shipping_group.delivery_date),
            "item_count": len(shipping_group.items)
        }
    )
    return shipping_group




@router.get("/{id}/pdf")
def download_shipping_group_pdf(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    PDF einer ShippingGroup herunterladen.
    
    Nur verfügbar wenn:
    - ShippingGroup existiert
    - PDF wurde generiert (status = VERSENDET)
    - User hat Berechtigung (Admin oder Freigeber für Lieferant)
    """
    shipping_group = db.query(ShippingGroup).filter(ShippingGroup.id == id).first()
    
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
    
    # PDF vorhanden?
    if not shipping_group.pdf_path:
        raise HTTPException(status_code=404, detail="PDF wurde noch nicht generiert")
    
    if not os.path.exists(shipping_group.pdf_path):
        raise HTTPException(status_code=404, detail="PDF-Datei nicht gefunden")
    
    # Dateiname für Download
    short_id = f"SG-{str(shipping_group.id)[:8].upper()}"
    filename = f"Bestellung_{short_id}.pdf"
    
    return FileResponse(
        path=shipping_group.pdf_path,
        filename=filename,
        media_type="application/pdf"
    )


@router.get("/{id}/order", response_model=ShippingGroupDetailResponse)
def get_shipping_group_order(
                    id: UUID,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)
):
    shipping_group = db.query(ShippingGroup).options(
            joinedload(ShippingGroup.items),
            joinedload(ShippingGroup.supplier)).filter(
            ShippingGroup.id == id)
    if not shipping_group:
        raise HTTPException(status_code=404, detail="Versandgruppe nicht gefunden")
    
    for order in shipping_group:
        
    

    

    