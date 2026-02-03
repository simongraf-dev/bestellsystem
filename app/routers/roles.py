
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.role import Role
from app.models.user import User
from app.utils.security import get_current_user
from app.schemas.role import RoleResponse

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/", response_model=list[RoleResponse])
def get_all_roles(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Role).all()