from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.database import get_db
from app.models import User, Order, OrderItem, Department
from app.utils.security import get_current_user, require_role
from app.schemas.order import OrderCreate, OrderResponse
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])

def _get_visible_departments(db: Session, user_department_id: UUID) -> list[UUID]:
    """
    Holt alle Departments die der User sehen darf:
    - Eigenes Department
    - Parent (eine Stufe hoch)
    - Alle Geschwister (Children des Parents)
    """
    result = [user_department_id]
    
    # Eigenes Department holen
    department = db.query(Department).filter(Department.id == user_department_id).first()
    
    if department and department.parent_id:
        # Parent hinzufügen
        result.append(department.parent_id)
        
        # Alle Geschwister holen (gleicher Parent)
        siblings = db.query(Department).filter(
            Department.parent_id == department.parent_id,
            Department.is_active == True
        ).all()
        
        for sibling in siblings:
            if sibling.id not in result:
                result.append(sibling.id)
    
    return result

@router.get("/", response_model=list[OrderResponse])
def get_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Order).options(
        joinedload(Order.department),
        joinedload(Order.creator),
        joinedload(Order.approver),
        joinedload(Order.items).joinedload(OrderItem.article),
        joinedload(Order.items).joinedload(OrderItem.supplier)
    ).filter(Order.is_active == True)
    
    if current_user.role.name != "Admin":
        visible_departments = _get_visible_departments(db, current_user.department_id)
        query = query.filter(Order.department_id.in_(visible_departments))
    
    return query.all()


@router.get("/{id}", response_model=OrderResponse)
def get_order(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).options(
        joinedload(Order.department),
        joinedload(Order.creator),
        joinedload(Order.approver),
        joinedload(Order.items).joinedload(OrderItem.article),
        joinedload(Order.items).joinedload(OrderItem.supplier)
    ).filter(Order.id == id, Order.is_active == True).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Bestellung nicht gefunden")
    
    # Berechtigung prüfen
    if current_user.role.name != "Admin" and order.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Keine Berechtigung für diese Bestellung")
    
    return order


@router.post("/", response_model=OrderResponse)
def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return order_service.create_order(db, current_user, order_data)


@router.delete("/{id}")
@require_role(["Admin"])
def delete_order(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == id, Order.is_active == True).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Bestellung nicht gefunden")
    
    # Soft Delete
    order.is_active = False
    db.commit()
    
    return {"message": "Bestellung gelöscht"}