from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from uuid import UUID

from app.schemas.article_supplier import ArticleSupplierCreate, ArticleSupplierResponse
from app.database import get_db
from app.utils.security import get_current_user

from app.models import User, ArticleSupplier, Article, Supplier

from app.utils.security import require_role

router = APIRouter(prefix="/article-suppliers", tags=["article-suppliers"])

@router.get("/")
def get_article_supplier(article_id: Optional[UUID] = None,
                         supplier_id: Optional[UUID] = None,
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)
):
   
    query = db.query(ArticleSupplier).options(joinedload(ArticleSupplier.article),
                                                        joinedload(ArticleSupplier.supplier))
    if article_id:
        query = query.filter(ArticleSupplier.article_id == article_id)

    if supplier_id:
        query = query.filter(ArticleSupplier.supplier_id == supplier_id)
    return query.all()


@router.post("/", response_model=ArticleSupplierResponse)
@require_role(["Admin"])
@router.post("/", response_model=ArticleSupplierResponse)
@require_role(["Admin"])
def create_article_supplier(article_supplier: ArticleSupplierCreate,
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)
):
    # Artikel prüfen
    article = db.query(Article).filter(Article.id == article_supplier.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")

    # Supplier prüfen
    supplier = db.query(Supplier).filter(Supplier.id == article_supplier.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden")

    # Duplikat prüfen
    existing = db.query(ArticleSupplier).filter(
        ArticleSupplier.article_id == article_supplier.article_id,
        ArticleSupplier.supplier_id == article_supplier.supplier_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Verknüpfung existiert bereits")

    new_article_supplier = ArticleSupplier(
        article_id=article_supplier.article_id,
        supplier_id=article_supplier.supplier_id,
        article_number_supplier=article_supplier.article_number_supplier,
        price=article_supplier.price,
        unit=article_supplier.unit
    )
    db.add(new_article_supplier)
    db.commit()
    
    return db.query(ArticleSupplier).options(
        joinedload(ArticleSupplier.article),
        joinedload(ArticleSupplier.supplier)
    ).filter(ArticleSupplier.id == new_article_supplier.id).first()

@router.delete("/{id}")
@require_role(["Admin"])
def delete_article_supplier(id: UUID,
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)
) -> dict:
    article = db.query(ArticleSupplier).filter(ArticleSupplier.id == id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Artikel-Lieferanten Kombi nicht gefunden")
    db.delete(article)
    db.commit()
    return {"message": "Artikel-Lieferanten Kombi gelöscht"}
