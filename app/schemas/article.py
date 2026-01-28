from pydantic import BaseModel
from typing import Optional

from uuid import UUID

class ArticleGroupInfo(BaseModel):
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