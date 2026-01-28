from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class DepartmentInfo(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}

class RoleInfo(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    name: str
    email: str
    password_plain: str
    department_id: UUID
    role_id: UUID
    is_active: bool = True

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    department_id: Optional[UUID] = None
    role_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    password_plain: Optional[str] = None

class UserResponse(BaseModel):
    id: UUID
    name: str 
    email: str
    department: DepartmentInfo
    role: RoleInfo
    is_active: bool
    is_2fa_enabled: bool

    model_config = {"from_attributes": True}