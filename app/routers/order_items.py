from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.database import get_db
from app.models import User, Order, OrderItem, Department
from app.utils.security import get_current_user, require_role
from app.schemas.order import OrderCreate, OrderResponse, OrderUpdate, OrderItemCreate, OrderItemResponse, OrderItemUpdate
from app.services.order_service import _can_edit_order
from app.models.order import OrderStatus

router = APIRouter(prefix="/order-items", tags=["order-items"])

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
    for field, value in update_data.items():
        setattr(order_item, field, value)

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
    db.delete(order_item)
    db.commit()
    return {"message": "Bestellter Artikel gelöscht"}