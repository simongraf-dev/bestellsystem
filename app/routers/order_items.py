from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models import User, OrderItem, Supplier, ApproverSupplier
from app.models.order import OrderStatus
from app.models.shipping_group import ShippingGroup, ShippingGroupStatus
from app.models.activity_log import ActionType
from app.schemas.order import OrderItemResponse, OrderItemUpdate

from app.services.activity_service import log_activity
from app.services.order_service import _can_edit_order, _get_next_delivery_date
from app.utils.security import get_current_user
from app.database import get_db

router = APIRouter(prefix="/order-items", tags=["order-items"])

def _get_order_item_action_type_for_field(field: str) -> ActionType:
    mapping = {
        "amount": ActionType.ITEM_QUANTITY_CHANGED,
        "note": ActionType.NOTE_CHANGED
    }
    action_type = mapping.get(field)
    if not action_type:
        raise ValueError(f"Unbekanntes Feld: {field}")
    return action_type

@router.patch("/{id}", response_model=OrderItemResponse)
def update_order_item(order_item_update: OrderItemUpdate,
                    id: UUID,
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)
                    ):
    order_item = db.query(OrderItem).options(
        joinedload(OrderItem.order),
        joinedload(OrderItem.article),
        joinedload(OrderItem.supplier)
).filter(OrderItem.id == id).first()
    if not order_item:
        raise HTTPException(status_code=404, detail="Bestellter Artikel nicht gefunden")
    order = order_item.order
    if order.status != OrderStatus.ENTWURF:
        raise HTTPException(status_code=403, detail="Bestellung kann nur als Entwurf bearbeitet werden")
    if not _can_edit_order(db, current_user, order):
        raise HTTPException(status_code=403, detail="Keine Berechtigung diese Bestellung zu bearbeiten")
    update_data = order_item_update.model_dump(exclude_unset=True)

    # Änderungen tracken
    for field, new_value in update_data.items():
        old_value = getattr(order_item, field)
        
        # Logging wenn sich etwas geändert hat
        if old_value != new_value:
            action_type = _get_order_item_action_type_for_field(field)

            log_activity(
                db=db,
                entity_type="order",
                entity_id=order_item.order_id,
                user_id=current_user.id,
                action_type=action_type,
                description=f"{order_item.article.name}: {field} geändert",
                old_value=str(old_value) if old_value else None,
                new_value=str(new_value) if new_value else None
            )

        setattr(order_item, field, new_value)

    db.commit()
    db.refresh(order_item)
    return order_item

@router.delete("/{id}")
def delete_order_item(id: UUID,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)) -> dict:
    order_item = db.query(OrderItem).options(
        joinedload(OrderItem.order),
        joinedload(OrderItem.article),
        joinedload(OrderItem.supplier)
).filter(OrderItem.id == id).first()
    if not order_item:
        raise HTTPException(status_code=404, detail="Bestellter Artikel nicht gefunden")
    order = order_item.order
    if order.status != OrderStatus.ENTWURF:
        raise HTTPException(status_code=403, detail="Bestellung kann nur als Entwurf bearbeitet werden")
    if not _can_edit_order(db, current_user, order):
        raise HTTPException(status_code=403, detail="Keine Berechtigung diese Bestellung zu bearbeiten")
    item_details = {
        "article_id": order_item.article.id,
        "article_name": order_item.article.name,
        "amount": order_item.amount,
        "department": order.department_id
        }
    db.delete(order_item)
    db.commit()
    log_activity(db, "order", order.id, current_user.id, ActionType.ITEM_REMOVED, "Artikel entfernt", details=item_details)
    return {"message": "Bestellter Artikel gelöscht"}


@router.patch("/{id}/assign-supplier", response_model=OrderItemResponse)
def assign_supplier_to_order_item(
    id: UUID,
    supplier_data: OrderItemAssignSupplier,  # Schema mit supplier_id
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lieferant einem OrderItem zuweisen.
    Nur Freigeber (mit ApproverSupplier-Berechtigung) und Admins.
    Nur bei Status ENTWURF oder VOLLSTAENDIG.
    """

    # 1. OrderItem laden
    order_item = db.query(OrderItem).options(
        joinedload(OrderItem.order),
        joinedload(OrderItem.article),
        joinedload(OrderItem.supplier)
    ).filter(OrderItem.id == id).first()

    if not order_item:
        raise HTTPException(status_code=404, detail="Bestellter Artikel nicht gefunden")

    order = order_item.order

    # 2. Status-Check: Nicht bei bereits versendeten Bestellungen
    if order.status not in [OrderStatus.ENTWURF, OrderStatus.VOLLSTAENDIG]:
        raise HTTPException(
            status_code=400,
            detail="Lieferant kann nur bei Entwurf oder vollständigen Bestellungen zugewiesen werden"
        )

    # 3. Berechtigungs-Check: Admin darf immer, sonst ApproverSupplier prüfen
    if current_user.role.name != "Admin":
        is_approver = db.query(ApproverSupplier).filter(
            ApproverSupplier.user_id == current_user.id,
            ApproverSupplier.supplier_id == supplier_data.supplier_id
        ).first()

        if not is_approver:
            raise HTTPException(
                status_code=403,
                detail="Keine Berechtigung für diesen Lieferanten"
            )

    # 4. Lieferant validieren
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_data.supplier_id,
        Supplier.is_active == True
    ).first()

    if not supplier:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden")

    # 5. Alten Lieferanten für Logging merken
    old_supplier_name = order_item.supplier.name if order_item.supplier else None
    old_supplier_id = order_item.supplier_id

    # 6. Lieferant zuweisen
    order_item.supplier_id = supplier.id

    # 7. Lieferdatum berechnen (wenn Lieferant feste Liefertage hat)
    delivery_date = _get_next_delivery_date(db, supplier.id)

    # 8. ShippingGroup finden oder erstellen
    if delivery_date:
        shipping_group = db.query(ShippingGroup).filter(
            ShippingGroup.supplier_id == supplier.id,
            ShippingGroup.delivery_date == delivery_date,
            ShippingGroup.status == ShippingGroupStatus.OFFEN
        ).first()

        if not shipping_group:
            shipping_group = ShippingGroup(
                supplier_id=supplier.id,
                delivery_date=delivery_date,
                status=ShippingGroupStatus.OFFEN
            )
            db.add(shipping_group)
            db.flush()

        order_item.shipping_group_id = shipping_group.id

    # 9. Speichern
    db.commit()
    db.refresh(order_item)

    # 10. Activity Log
    log_activity(
        db=db,
        entity_type="order",
        entity_id=order.id,
        user_id=current_user.id,
        action_type=ActionType.SUPPLIER_CHANGED,
        description=f"{order_item.article.name}: Lieferant geändert",
        old_value=old_supplier_name,
        new_value=supplier.name,
        details={
            "article_id": str(order_item.article_id),
            "article_name": order_item.article.name,
            "old_supplier_id": str(old_supplier_id) if old_supplier_id else None,
            "new_supplier_id": str(supplier.id),
            "delivery_date": str(delivery_date) if delivery_date else None
        }
    )

    return order_item