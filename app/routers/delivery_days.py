from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.models.delivery_days import DeliveryDay
from app.models.user import User
from app.utils.security import get_current_user, require_role
from app.schemas.delivery_days import DeliveryDayCreate, DeliveryDayResponse

router = APIRouter(prefix="/delivery-days", tags=["delivery-days"])

@router.get("/{supplier_id}", response_model=list[DeliveryDayResponse])
def get_all_delivery_days(
                    supplier_id: Optional[UUID] = None,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)
):
    query = db.query(DeliveryDay).options(joinedload(DeliveryDay.supplier))
    if supplier_id:
        query = query.filter(DeliveryDay.supplier_id == supplier_id)
    return query.all()


@router.post("/", response_model=DeliveryDayResponse)
@require_role(["Admin"])
def create_delivery_day(request: DeliveryDayCreate,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)
):
    new_delivery_date = DeliveryDay(
        supplier_id=request.supplier_id,
        weekday=request.weekday
    )

    db.add(new_delivery_date)
    db.commit()
    db.refresh(new_delivery_date)
    return db.query(DeliveryDay).options(
        joinedload(DeliveryDay.supplier)
        ).filter(DeliveryDay.id == new_delivery_date.id).first()

@router.delete("/{id}")
@require_role(["Admin"])
def delete_delivery_day(id: UUID,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)
):
    delivery_day = db.query(DeliveryDay).filter(DeliveryDay.id == id).first()
    if not delivery_day:
        raise HTTPException(status_code=403, detail="Liefertag nicht gefunden")
    db.delete(delivery_day)
    db.commit()
    return {"message": "Liefertag gelöscht"}