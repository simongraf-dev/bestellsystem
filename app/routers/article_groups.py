from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.article_group import ArticleGroup
from app.models.article import Article
from app.models.user import User
from app.utils.security import get_current_user, require_role

router = APIRouter(prefix="/article-groups", tags=["article-groups"])


@router.get("/")
def get_all_article_groups(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ArticleGroup).all()


@router.get("/{id}")
def get_article_group(id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = db.query(ArticleGroup).filter(ArticleGroup.id == id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Artikelgruppe nicht gefunden")
    return group


@router.post("/")
@require_role(["Admin"])
def create_article_group(name: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_group = ArticleGroup(name=name)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return new_group


@router.patch("/{id}")
@require_role(["Admin"])
def update_article_group(id: UUID, name: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = db.query(ArticleGroup).filter(ArticleGroup.id == id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Artikelgruppe nicht gefunden")
    group.name = name
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{id}")
@require_role(["Admin"])
def delete_article_group(id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = db.query(ArticleGroup).filter(ArticleGroup.id == id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Artikelgruppe nicht gefunden")
    
    article_count = db.query(Article).filter(Article.article_group_id == id).count()
    if article_count > 0:
        raise HTTPException(status_code=400, detail=f"Gruppe enthält noch {article_count} Artikel")
    group.is_active = False
    db.commit()
    return {"message": "Artikelgruppe gelöscht"}