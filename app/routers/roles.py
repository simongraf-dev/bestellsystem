
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.roles import Role
from app.models.user import User
from app.utils.security import get_current_user

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/")
def get_all_roles(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Role).all()