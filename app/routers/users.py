from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.department import Department
from app.models.role import Role
from app.utils.security import get_current_user, require_role, hash_password
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
@require_role(["Admin"])
def get_all_users(
    name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(User).options(
        joinedload(User.department),
        joinedload(User.role)
    ).filter(User.is_active == True)
    
    if name:
        query = query.filter(User.name.ilike(f"%{name}%"))
    return query.all()


@router.get("/{id}", response_model=UserResponse)
@require_role(["Admin"])
def get_user(id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).options(
        joinedload(User.department),
        joinedload(User.role)
    ).filter(User.id == id, User.is_active == True).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    return user

@router.post("/", response_model=UserResponse)
@require_role(["Admin"])
def create_user(
    request: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Überprüft ob Mail bereits genutzt wird und ob Department und Role exisitieren
    existing_mail = db.query(User).filter(User.email == request.email, User.is_active == True).first() # pyright: ignore[reportOptionalCall]
    if existing_mail:
        raise HTTPException(status_code=400, detail="Mail wird bereits verwendet")
    existing_department = db.query(Department).filter(
        Department.id == request.department_id, 
        Department.is_active == True
        ).first() # type: ignore
    if not existing_department:
        raise HTTPException(status_code=404, detail="Department existiert nicht")
    existing_role = db.query(Role).filter(
        Role.id == request.role_id, 
        ).first() # pyright: ignore[reportOptionalCall]
    if not existing_role:
        raise HTTPException(status_code=404, detail="Role existiert nicht")
    
    hashed_password = hash_password(request.password_plain)

    new_user = User(
        name=request.name,
        email=request.email,
        password_hash=hashed_password,
        department_id=request.department_id,
        role_id=request.role_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return db.query(User).options(
        joinedload(User.role),
        joinedload(User.department) 
    ).filter(User.id == new_user.id).first()

@router.patch("/{id}", response_model=UserResponse)
@require_role(["Admin"])
def update_user(
    id: UUID,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    
    # Sich selbst nicht deaktivieren
    if id == current_user.id and user_update.is_active == False:
        raise HTTPException(status_code=400, detail="Du kannst dich nicht selbst deaktivieren")
    
    # Email-Duplikat prüfen
    if user_update.email and user_update.email != user.email:
        existing_mail = db.query(User).filter(
            User.email == user_update.email,
            User.is_active == True,
            User.id != id
        ).first() # type: ignore
        if existing_mail:
            raise HTTPException(status_code=400, detail="Email wird bereits verwendet")
    
    # Department prüfen
    if user_update.department_id:
        existing_department = db.query(Department).filter(
            Department.id == user_update.department_id,
            Department.is_active == True
        ).first() # type: ignore
        if not existing_department:
            raise HTTPException(status_code=404, detail="Department existiert nicht")
    
    # Role prüfen
    if user_update.role_id:
        existing_role = db.query(Role).filter(Role.id == user_update.role_id).first()
        if not existing_role:
            raise HTTPException(status_code=404, detail="Role existiert nicht")
    
    # Update durchführen
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Passwort hasshen
    if "password_plain" in update_data:
        password_plain = update_data.pop("password_plain")
        if password_plain:
            user.password_hash = hash_password(password_plain)
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    
    return db.query(User).options(
        joinedload(User.department),
        joinedload(User.role)
    ).filter(User.id == id).first()

@router.delete("/{id}")
@require_role(["Admin"])
def delete_user(id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Sich selbst nicht löschen
    if id == current_user.id:
        raise HTTPException(status_code=400, detail="Du kannst dich nicht selbst löschen")
    
    user = db.query(User).filter(User.id == id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    
    user.is_active = False
    db.commit()
    return {"message": "User gelöscht"}



    
    
