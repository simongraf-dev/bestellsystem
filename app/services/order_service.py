from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, Depends
from uuid import UUID

import holidays
from datetime import date, timedelta

from app.models import User, Order, OrderItem, Article, ArticleSupplier, Supplier, ShippingGroup, Department, DeliveryDay
from app.schemas.order import OrderCreate, OrderResponse, OrderItemCreate
from app.models.delivery_days import Weekday
from app.utils.security import get_current_user, get_db

WEEKDAY_MAP = {
    0: Weekday.MO,
    1: Weekday.DI,
    2: Weekday.MI,
    3: Weekday.DO,
    4: Weekday.FR,
    5: Weekday.SA,
    6: Weekday.SO,
}

# Helferfunktion um Parentbereiche zu finden
def _is_descendant_of(department_id: UUID, ancestor_id: UUID, db: Session) -> bool:
    department = db.query(Department).filter(Department.id == department_id).first() 
    # Checkt ob gleiches Deparmtent
    if department_id == ancestor_id:
        return True
    
    while department.parent_id:
        if department.parent_id == ancestor_id:
            return True
        department = db.query(Department).filter(Department.id == department.parent_id).first()
    return False

# Berechnet das nächste Lieferdatum basierend auf den Liefertagen des Lieferanten.
# Feiertage werden wie Sonntage behandelt (keine Lieferung)

def _get_next_delivery_date(db: Session, supplier_id: UUID) -> date | None:
    sh_holidays = holidays.Germany(state="SH", years=[2026, 2027, 2028])
    delivery_days = db.query(DeliveryDay).filter(DeliveryDay.supplier_id == supplier_id).all()
    valid_weekdays = {d.weekday for d in delivery_days}  # Set der Liefertage
    
    check_date = date.today() + timedelta(days=1)
    
    for _ in range(14):
        # wenn Feiertag -> überspringen
        if check_date in sh_holidays:
            check_date += timedelta(days=1)
            continue
        
        # Wochentag ermitteln und prüfen
        current_weekday = WEEKDAY_MAP[check_date.weekday()]
        if current_weekday in valid_weekdays:
            return check_date
        
        check_date += timedelta(days=1)
    
    return None
        


# kotrolliert ob User für dieses Department bestllen darf
def _get_and_validate_department(db: Session, user: User, requested_department_id: UUID | None) -> UUID:
    if not requested_department_id:
        return user.department_id
    if user.role.name == "Admin":
        return requested_department_id
    if not _is_descendant_of(requested_department_id, user.department_id, db):
        raise HTTPException(status_code=403, detail="Keine Berechtigung für diese Abteilung")
    return requested_department_id

#Hauptlogik um die Bestellung auf ShippingGroups aufzuteilen
def _process_order_item(db: Session, order: Order, item: OrderItemCreate):
    article = db.query(Article).filter(Article.id == item.article_id, Article.is_active == True).first()
    if not article:
        raise HTTPException(status_code=403, detail="Artikel nicht gefunden")
    suppliers = db.query(ArticleSupplier).filter(ArticleSupplier.article_id == item.article_id).all()
    note = item.note
    supplier_id = None
    delivery_date = order.delivery_date
    if not suppliers:
        note = (note or "") + " | Kein Lieferant gefunden! Bitte manuell checken."
    elif len(suppliers) == 1:
        supplier_id = suppliers[0].supplier_id
        # Lieferdatumslogik wenn kein Datum in order
        if not order.delivery_date:
            supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
            if supplier.fixed_delivery_days:
                delivery_date = _get_next_delivery_date(db, supplier_id)
    new_order_item= OrderItem(
        order_id=order.id,
        supplier_id=supplier_id,
        article_id=article.id,
        amount=item.amount,
        note=note
    )
    db.add(new_order_item)
    db.flush()
    if supplier_id:
        shipping_group = db.query(ShippingGroup).filter(
            ShippingGroup.supplier_id == new_order_item.supplier_id,
            ShippingGroup.delivery_date == delivery_date
        ).first()
        if not shipping_group:
            new_shipping_group=ShippingGroup(
                supplier_id=new_order_item.supplier_id,
                delivery_date=delivery_date
            )
            db.add(new_shipping_group)
            db.flush()
            new_order_item.shipping_group_id=new_shipping_group.id
        else:
            new_order_item.shipping_group_id=shipping_group.id

    
    
def create_order(db: Session, user: User, order: OrderCreate):
    order.department_id = _get_and_validate_department(db, user, order.department_id)
    new_order = Order(
        department_id=order.department_id,
        creator_id=user.id,
        delivery_date=order.delivery_date,
        additional_articles=order.additional_articles,
        delivery_notes=order.delivery_notes,
    )
    db.add(new_order)
    db.flush()
    for item in order.items:
        _process_order_item(db, new_order, item)
    db.commit()
    return db.query(Order).options(
        joinedload(Order.department),
        joinedload(Order.creator),
        joinedload(Order.approver),
        joinedload(Order.items).joinedload(OrderItem.article),
        joinedload(Order.items).joinedload(OrderItem.supplier)
    ).filter(Order.id == new_order.id).first()
    

