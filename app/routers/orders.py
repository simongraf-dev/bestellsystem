from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.database import get_db
from app.models import User, Order, OrderItem, Department
from app.utils.security import get_current_user, require_role
from app.services.order_service import _can_edit_order
from app.schemas.order import OrderCreate, OrderResponse, OrderUpdate, OrderItemCreate, OrderItemResponse
from app.services import order_service
from app.models.order import OrderStatus

router = APIRouter(prefix="/orders", tags=["orders"])

def _get_visible_departments(db: Session, user_department_id: UUID) -> list[UUID]:
    """
    Holt alle Departments die der User sehen darf:
    - Eigenes Department
    - Parent (eine Stufe hoch)
    - Alle Geschwister (Children des Parents)
    - Alle eigenen Children (eine Stufe runter)
    """
    result = [user_department_id]
    
    # Eigenes Department holen
    department = db.query(Department).filter(Department.id == user_department_id).first()
    
    if department:
        # Parent und Geschwister
        if department.parent_id:
            result.append(department.parent_id)
            
            siblings = db.query(Department).filter(
                Department.parent_id == department.parent_id,
                Department.is_active == True
            ).all()
            
            for sibling in siblings:
                if sibling.id not in result:
                    result.append(sibling.id)
        
        # Eigene Children hinzufügen
        children = db.query(Department).filter(
            Department.parent_id == user_department_id,
            Department.is_active == True
        ).all()
        
        for child in children:
            if child.id not in result:
                result.append(child.id)
    
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
        raise HTTPException(status_code=404, detail="Keine Berechtigung für diese Bestellung")
    
    return order


@router.post("/", response_model=OrderResponse)
def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return order_service.create_order(db, current_user, order_data)

# Order löschen
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

# Order updaten
@router.patch("/{id}", response_model=OrderResponse)
def update_order(
    id: UUID,
    order_update: OrderUpdate,
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
    
   
    if not _can_edit_order(db, current_user, order):
        raise HTTPException(status_code=403, detail="Keine Berechtigung für diese Bestellung")
    
    update_data = order_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    
    db.commit()
    db.refresh(order)
    return order
    

@router.post("/{order_id}/items", response_model=OrderResponse)
def add_order_item(
    order_id: UUID,
    item: OrderItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return order_service.add_item_to_order(db, current_user, order_id, item)


@router.post("/{id}/abschliessen", response_model=OrderResponse)
def abschliessen_order(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return order_service.close_order(db, current_user, id)