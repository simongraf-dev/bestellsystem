from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class ArticleInfo(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}

class SupplierInfo(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class ArticleSupplierCreate(BaseModel):
    article_id: UUID
    supplier_id: UUID
    article_number_supplier: Optional[str] = None
    price: Optional[float] = None
    unit: str

class ArticleSupplierResponse(BaseModel):
    id: UUID
    supplier: SupplierInfo
    article: ArticleInfo
    article_number_supplier: Optional[str] = None
    price: Optional[float] = None
    unit: str

    model_config = {"from_attributes": True}