from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class DepartmentInfo(BaseModel):
    id: UUID
    name: str
    model_config = {"from_attributes": True}

class DepartmentCreate(BaseModel):
    name: str
    is_active: bool = True
    parent_id: Optional[UUID] = None

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    parent_id: Optional[UUID] = None

class DepartmentResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool
    parent: Optional[DepartmentInfo]
    children: list[DepartmentInfo]
    
    model_config = {"from_attributes": True}
