from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.article_storage_location import ArticleStorageLocation
from app.models.article import Article
from app.models.storage_location import StorageLocation
from app.models.user import User
from app.utils.security import get_current_user, require_role
from app.schemas.article_storage_location import ArticleStorageLocationCreate, ArticleStorageLocationResponse

router = APIRouter(prefix="/article-storage-locations", tags=["article-storage-locations"])


@router.get("/", response_model=list[ArticleStorageLocationResponse])
def get_article_storage_locations(
    article_id: Optional[UUID] = None,
    storage_location_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ArticleStorageLocation).options(
        joinedload(ArticleStorageLocation.article),
        joinedload(ArticleStorageLocation.storage_location)
    )
    
    if article_id:
        query = query.filter(ArticleStorageLocation.article_id == article_id)
    if storage_location_id:
        query = query.filter(ArticleStorageLocation.storage_location_id == storage_location_id)
    
    return query.all()


@router.post("/", response_model=ArticleStorageLocationResponse)
@require_role(["Admin"])
def create_article_storage_location(
    data: ArticleStorageLocationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Artikel prüfen
    article = db.query(Article).filter(
        Article.id == data.article_id,
        Article.is_active == True
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")
    
    # Lagerort prüfen
    storage_location = db.query(StorageLocation).filter(
        StorageLocation.id == data.storage_location_id,
        StorageLocation.is_active == True
    ).first()
    if not storage_location:
        raise HTTPException(status_code=404, detail="Lagerort nicht gefunden")
    
    # Duplikat prüfen
    existing = db.query(ArticleStorageLocation).filter(
        ArticleStorageLocation.article_id == data.article_id,
        ArticleStorageLocation.storage_location_id == data.storage_location_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Verknüpfung existiert bereits")
    
    new_link = ArticleStorageLocation(
        article_id=data.article_id,
        storage_location_id=data.storage_location_id
    )
    db.add(new_link)
    db.commit()
    
    return db.query(ArticleStorageLocation).options(
        joinedload(ArticleStorageLocation.article),
        joinedload(ArticleStorageLocation.storage_location)
    ).filter(
        ArticleStorageLocation.article_id == data.article_id,
        ArticleStorageLocation.storage_location_id == data.storage_location_id
    ).first()


@router.delete("/")
@require_role(["Admin"])
def delete_article_storage_location(
    article_id: UUID,
    storage_location_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    link = db.query(ArticleStorageLocation).filter(
        ArticleStorageLocation.article_id == article_id,
        ArticleStorageLocation.storage_location_id == storage_location_id
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Verknüpfung nicht gefunden")
    
    db.delete(link)
    db.commit()
    return {"message": "Verknüpfung gelöscht"}