from pydantic import BaseModel
from uuid import UUID

class DepartmentInfo(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}

class RoleInfo(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}

class UserResponse(BaseModel):
    id: UUID
    name: str 
    email: str
    department: DepartmentInfo
    role: RoleInfo
    is_active: bool

    model_config = {"from_attributes": True}