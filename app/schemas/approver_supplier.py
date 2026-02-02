from uuid import UUID

from pydantic import BaseModel

class UserInfo(BaseModel):
    id: UUID
    email: str
    
    model_config = {"from_attributes": True}

class SupplierInfo(BaseModel):
    id: UUID
    name: str
    
    model_config = {"from_attributes": True}

class ApproverSupplierCreate(BaseModel):
    user_id: UUID
    supplier_id: UUID

class ApproverSupplierResponse(BaseModel):
    user: UserInfo
    supplier: SupplierInfo

    model_config = {"from_attributes": True}

