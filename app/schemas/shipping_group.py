from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import date

from app.schemas.order import SupplierInfo, OrderItemResponse


class ShippingGroupResponse(BaseModel):
    id: UUID
    supplier: SupplierInfo
    delivery_date: Optional[date]
    status: str
    items: list[OrderItemResponse]
    
    model_config = {"from_attributes": True}