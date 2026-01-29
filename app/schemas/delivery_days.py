from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from app.models.delivery_days import Weekday

class SupplierInfo(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}

class DeliveryDayCreate(BaseModel):
    supplier_id: UUID
    weekday: Weekday

class DeliveryDayResponse(BaseModel):
    id: UUID
    supplier: SupplierInfo
    weekday: Weekday

    model_config = {"from_attributes": True}