from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.storage_location import StorageLocation
from app.models.department import Department
from app.models.user import User
from app.utils.security import get_current_user, require_role
from app.schemas.storage_location import StorageLocationCreate, StorageLocationUpdate, StorageLocationResponse

router = APIRouter(prefix="/storage-locations", tags=["storage-locations"])


@router.get("/", response_model=list[StorageLocationResponse])
def get_all_storage_locations(
    name: Optional[str] = None,
    department_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(StorageLocation).options(
        joinedload(StorageLocation.department)
    ).filter(StorageLocation.is_active == True)
    
    if name:
        query = query.filter(StorageLocation.name.ilike(f"%{name}%"))
    if department_id:
        query = query.filter(StorageLocation.department_id == department_id)
    
    return query.all()


@router.get("/{id}", response_model=StorageLocationResponse)
def get_storage_location(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    storage_location = db.query(StorageLocation).options(
        joinedload(StorageLocation.department)
    ).filter(StorageLocation.id == id, StorageLocation.is_active == True).first()
    
    if not storage_location:
        raise HTTPException(status_code=404, detail="Lagerort nicht gefunden")
    return storage_location


@router.post("/", response_model=StorageLocationResponse)
@require_role(["Admin"])
def create_storage_location(
    storage_location: StorageLocationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Department prüfen
    department = db.query(Department).filter(
        Department.id == storage_location.department_id,
        Department.is_active == True
    ).first()
    if not department:
        raise HTTPException(status_code=404, detail="Abteilung nicht gefunden")
    
    new_storage_location = StorageLocation(**storage_location.model_dump())
    db.add(new_storage_location)
    db.commit()
    
    return db.query(StorageLocation).options(
        joinedload(StorageLocation.department)
    ).filter(StorageLocation.id == new_storage_location.id).first()


@router.patch("/{id}", response_model=StorageLocationResponse)
@require_role(["Admin"])
def update_storage_location(
    id: UUID,
    storage_location_update: StorageLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    storage_location = db.query(StorageLocation).filter(
        StorageLocation.id == id,
        StorageLocation.is_active == True
    ).first()
    
    if not storage_location:
        raise HTTPException(status_code=404, detail="Lagerort nicht gefunden")
    
    update_data = storage_location_update.model_dump(exclude_unset=True)
    
    # Falls Department geändert wird, prüfen ob es existiert
    if "department_id" in update_data:
        department = db.query(Department).filter(
            Department.id == update_data["department_id"],
            Department.is_active == True
        ).first()
        if not department:
            raise HTTPException(status_code=404, detail="Abteilung nicht gefunden")
    
    for field, value in update_data.items():
        setattr(storage_location, field, value)
    
    db.commit()
    
    return db.query(StorageLocation).options(
        joinedload(StorageLocation.department)
    ).filter(StorageLocation.id == id).first()


@router.delete("/{id}")
@require_role(["Admin"])
def delete_storage_location(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    storage_location = db.query(StorageLocation).filter(
        StorageLocation.id == id,
        StorageLocation.is_active == True
    ).first()
    
    if not storage_location:
        raise HTTPException(status_code=404, detail="Lagerort nicht gefunden")
    
    storage_location.is_active = False
    db.commit()
    return {"message": "Lagerort gelöscht"}