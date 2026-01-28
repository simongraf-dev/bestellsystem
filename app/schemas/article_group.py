from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class ArticleGroupCreate(BaseModel):
    name: str
    is_active: bool = True

class ArticleGroupUpdate(BaseModel):
    name: str
    is_active: Optional[str] = None

class ArticleGroupResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool
    
    model_config = {"from_attributes": True}