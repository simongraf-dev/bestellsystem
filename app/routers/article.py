from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.orm import Session, joinedload

from app.models import User, Article, ArticleGroup, OrderItem, Order, ArticleSupplier, ArticleStorageLocation
from app.models.order import OrderStatus
from app.schemas.article import ArticleCreate, ArticleResponse, ArticleUpdate, ArticleOrderHistoryResponse, ArticleOrderHistoryItem

from app.database import get_db
from app.utils.security import get_current_user
from app.utils.security import require_role

router = APIRouter(prefix="/articles", tags=["articles"])

@router.get("/", response_model=list[ArticleResponse])
def get_all_articles(
    name: Optional[str] = None,
    article_group_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    supplier_id: Optional[UUID] = None,
    storage_location_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
    ):
    query = db.query(Article).options(joinedload(Article.article_group))

    if is_active is not None:
        query = query.filter(Article.is_active == is_active)

    if article_group_id:
        query = query.filter(Article.article_group_id == article_group_id)
    
    if supplier_id:
        article_ids = db.query(ArticleSupplier.article_id).filter(
                ArticleSupplier.supplier_id == supplier_id)
                query = query.filter(Article.id.in_(article_ids))

    if storage_location_id:
        article_ids = db.query(ArticleStorageLocation.article_id).filter(
                ArticleStorageLocation.storage_location_id == storage_location_id)
                query = query.filter(Article.id.in_(article_ids))
    if name:
        query = query.filter(Article.name.ilike(f"%{name}%"))
    
    return query.all()

@router.get("/{id}", response_model=ArticleResponse)
def get_article_id(
                id: UUID,
                current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)
):
    article = db.query(Article).options(joinedload(Article.article_group)).filter(Article.id == id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Artikel ID nicht in DB")
    return article

@router.post("/", response_model=ArticleResponse)
@require_role(["Admin"])
def create_article(article: ArticleCreate,
                   current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)
):  
    # Check ob Artikelgruppe existiert
    group = db.query(ArticleGroup).filter(ArticleGroup.id == article.article_group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Artikelgruppe nicht gefunden")
    
    # Check ob Artikel mit gleichem Namen exisitert
    existing_article = db.query(Article).filter(Article.name.ilike(article.name)).first()
    if existing_article:
        raise HTTPException(status_code=409, detail="Artikel mit gleichem Namen existiert bereits")
    
    new_article = Article(
        name=article.name,
        unit=article.unit,
        is_active=article.is_active,
        article_group_id=article.article_group_id,
        notes=article.notes
    )
    db.add(new_article)
    db.commit()
    db.refresh(new_article)
    return new_article

@router.patch("/{id}", response_model=ArticleResponse)
def update_article(article_update: ArticleUpdate, id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Artikel ID nicht in DB")
    update_data = article_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(article, field, value)

    db.commit()
    db.refresh(article)
    return article

@router.delete("/{id}")
@require_role(["Admin"])
def delete_article(id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Artikel ID nicht in DB")
    article.is_active = False
    db.commit()
    db.refresh(article)
    return {"message": "Artikel erfolgreich gelöscht"}


@router.get("/{id}/order-history", response_model=ArticleOrderHistoryResponse)
def get_article_order_history(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Gibt die Bestellhistorie eines Artikels zurück:
    - Aktuelle offene Bestellungen (ENTWURF, VOLLSTAENDIG)
    - Vergangene/abgeschlossene Bestellungen
    """

    # 1. Artikel prüfen
    article = db.query(Article).filter(
        Article.id == id,
        Article.is_active == True
    ).first()

    if not article:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")

    # 2. Alle OrderItems für diesen Artikel laden
    order_items = db.query(OrderItem).options(
        joinedload(OrderItem.order).joinedload(Order.department),
        joinedload(OrderItem.supplier)
    ).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        OrderItem.article_id == id,
        Order.is_active == True
    ).order_by(
        Order.drafted_on.desc()
    ).all()

    # 3. In aktive und vergangene aufteilen
    active_statuses = [OrderStatus.ENTWURF, OrderStatus.VOLLSTAENDIG]

    active_orders = []
    past_orders = []

    for item in order_items:
        entry = ArticleOrderHistoryItem(
            order_item_id=item.id,
            order_id=item.order_id,
            amount=float(item.amount),
            note=item.note,
            supplier=item.supplier,
            department=item.order.department,
            order_status=item.order.status.value,
            delivery_date=item.order.delivery_date,
            drafted_on=item.order.drafted_on
        )

        if item.order.status in active_statuses:
            active_orders.append(entry)
        else:
            past_orders.append(entry)

    # 4. Past orders limitieren (active immer alle zeigen)
    past_orders = past_orders[:limit]

    return ArticleOrderHistoryResponse(
        article_id=article.id,
        article_name=article.name,
        active_orders=active_orders,
        past_orders=past_orders,
        total_orders=len(order_items)
    )