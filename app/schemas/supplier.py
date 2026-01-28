from pydantic import BaseModel
from uuid import UUID
from typing import Optional


class SupplierCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    fixed_delivery_days: bool = False
    is_active: bool = True


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    fixed_delivery_days: Optional[bool] = None
    is_active: Optional[bool] = None


class SupplierResponse(BaseModel):
    id: UUID
    name: str
    email: Optional[str]
    phone: Optional[str]
    fixed_delivery_days: bool
    is_active: bool

    model_config = {"from_attributes": True}