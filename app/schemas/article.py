from uuid import UUID
from typing import Optional, List
from datetime import date, datetime

from pydantic import BaseModel


class ArticleGroupInfo(BaseModel):
    id: UUID
    name: str
    model_config = {"from_attributes": True}

class OrderHistorySupplierInfo(BaseModel):
    """Lieferant-Info für die Artikelhistorie"""
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class OrderHistoryDepartmentInfo(BaseModel):
    """Department-Info für die Artikelhistorie"""
    id: UUID
    name: str

    model_config = {"from_attributes": True}
    
class ArticleCreate(BaseModel):
    name: str
    unit: str
    notes: Optional[str] = None
    article_group_id: UUID
    is_active: bool = True

class ArticleUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    article_group_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class ArticleResponse(BaseModel):
    id: UUID
    name: str
    unit: str
    is_active: bool
    notes: Optional[str]
    article_group: ArticleGroupInfo

    model_config = {"from_attributes": True}


class ArticleOrderHistoryItem(BaseModel):
    """Ein einzelner Bestelleintrag in der Artikelhistorie"""
    order_item_id: UUID
    order_id: UUID
    amount: float
    note: Optional[str] = None
    supplier: Optional[OrderHistorySupplierInfo] = None
    department: Optional[OrderHistoryDepartmentInfo] = None
    order_status: str
    delivery_date: Optional[date] = None
    drafted_on: datetime  # Wann die Order erstellt wurde

    model_config = {"from_attributes": True}


class ArticleOrderHistoryResponse(BaseModel):
    """Gesamte Artikelhistorie"""
    article_id: UUID
    article_name: str
    active_orders: list[ArticleOrderHistoryItem]     
    past_orders: list[ArticleOrderHistoryItem]        
    total_orders: int                      