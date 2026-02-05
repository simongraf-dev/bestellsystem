from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog, ActionType
from app.models.user import User
from app.models.order import Order

from app.schemas.activity import ActivityResponse
from sqlalchemy.orm import Session, joinedload

from app.utils.security import get_current_user, require_role
from app.database import get_db
from app.routers.orders import _get_visible_departments

router = APIRouter(prefix="/activities", tags=["activities"])

@router.get("/", response_model=list[ActivityResponse])
def get_activities(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    department_id: Optional[UUID] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100)
):
    visible = _get_visible_departments(db, user.department_id)
    order_query = db.query(Order.id).filter(Order.department_id.in_(visible))
    if department_id:
        if department_id not in visible:
            raise HTTPException(status_code=403, detail="Keine Berechtigung für diese Abteilung")
        order_query = order_query.filter(Order.department_id == department_id)

    activities = db.query(ActivityLog).filter(
                ActivityLog.entity_id.in_(order_query)
                ).options(
                joinedload(ActivityLog.user)
                ).order_by(
                ActivityLog.timestamp.desc()
                ).offset(skip).limit(limit).all()
    return activities

    

@router.get("/order/{id}", response_model=list[ActivityResponse])
def get_order_activities(
    id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
                    
):
    order = db.query(Order).filter(
            Order.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Bestellung nicht gefunden")
    visible = _get_visible_departments(db, user.department_id)
    if order.department_id not in visible:
        raise HTTPException(status_code=403, detail="Keine Berechtigung für diese Bestellung")
    
    activities = db.query(ActivityLog).filter(
            ActivityLog.entity_id == id,
            ActivityLog.entity_type == "order").options(
            joinedload(ActivityLog.user)).order_by(
            ActivityLog.timestamp.desc()).all()

    return activities