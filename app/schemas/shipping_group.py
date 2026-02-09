from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import date

from app.schemas.order import SupplierInfo, OrderItemResponse, DepartmentInfo, CreatorInfo
from app.models.shipping_group import ShippingGroupStatus


class ShippingGroupResponse(BaseModel):
    id: UUID
    supplier: SupplierInfo
    delivery_date: Optional[date]
    status: ShippingGroupStatus
    items: list[OrderItemResponse]
    
    

class ShippingGroupOrderInfo(BaseModel):
    """Eine Order innerhalb einer ShippingGroup — nur relevante Items"""
    id: UUID
    department: Optional[DepartmentInfo]
    creator: CreatorInfo
    status: str
    delivery_notes: Optional[str]
    additional_articles: Optional[str]
    items: list[OrderItemResponse] 

    model_config = {"from_attributes": True}


class ShippingGroupDetailResponse(BaseModel):
    id: UUID
    supplier: SupplierInfo
    delivery_date: Optional[date]
    status: str
    orders: list[ShippingGroupOrderInfo] 

    model_config = {"from_attributes": True}