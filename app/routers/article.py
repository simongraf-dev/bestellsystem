from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from uuid import UUID

from app.schemas.article import ArticleCreate, ArticleResponse, ArticleUpdate
from app.database import get_db
from app.utils.security import get_current_user

from app.models import User, Article, ArticleGroup

from app.utils.security import require_role

router = APIRouter(prefix="/articles", tags=["articles"])

@router.get("/", response_model=list[ArticleResponse])
def get_all_articles(
    name: Optional[str] = None,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
    ):
    query = db.query(Article).options(joinedload(Article.article_group)).filter(Article.is_active == True)
    
    if name:
        query = query.filter(Article.name.ilike(f"%{name}%"))
    
    return query.all()

@router.get("/{id}", response_model=ArticleResponse)
def get_article_id(id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    article = db.query(Article).options(joinedload(Article.article_group)).filter(Article.id == id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Artikel ID nicht in DB")
    return article

@router.post("/", response_model=ArticleResponse)
@require_role(["Admin"])
def create_article(article: ArticleCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = db.query(ArticleGroup).filter(ArticleGroup.id == article.article_group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Artikelgruppe nicht gefunden")
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
@require_role(["Admin"])
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

    