from uuid import UUID

from pydantic import BaseModel
from app.schemas.user import DepartmentInfo
from typing import Optional


class StorageLocationCreate(BaseModel):
    name: str
    department_id: UUID

class StorageLocationResponse(BaseModel):
    id: UUID
    name: str
    department: DepartmentInfo
    is_active: bool

    model_config = {"from_attributes": True}

class StorageLocationUpdate(BaseModel):
    name: Optional[str] = None
    department_id: Optional[UUID] = None