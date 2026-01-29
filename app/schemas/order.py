from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime, date

class DepartmentInfo(BaseModel):
    id: UUID
    name: str
    model_config = {"from_attributes": True}

class SupplierInfo(BaseModel):
    id: UUID
    name: str
    model_config = {"from_attributes": True}

class CreatorInfo(BaseModel):
    id: UUID
    name: str
    model_config = {"from_attributes": True}

class ApproverInfo(BaseModel):
    id: UUID
    name: str
    model_config = {"from_attributes": True}

class ArticleInfo(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}



class OrderItemCreate(BaseModel):
    article_id: UUID
    amount: float
    note: Optional[str] = None

class OrderCreate(BaseModel):
    items: list[OrderItemCreate]
    delivery_date: Optional[date] = None
    additional_articles: Optional[str] = None
    delivery_notes: Optional[str] = None
    department_id: Optional[UUID] = None


class OrderItemResponse(BaseModel):
    id: UUID
    article: ArticleInfo
    supplier: Optional[SupplierInfo]
    amount: float
    note: Optional[str]
    shipping_group_id: Optional[UUID]

    
    model_config = {"from_attributes": True}

class OrderResponse(BaseModel):
    id: UUID
    department: Optional[DepartmentInfo]
    creator: CreatorInfo
    approver: Optional[ApproverInfo]
    delivery_date: Optional[date]
    status: str
    items: list[OrderItemResponse]
    additional_articles: Optional[str]
    delivery_notes: Optional[str]
    drafted_on: datetime
    is_active: bool

    model_config = {"from_attributes": True}