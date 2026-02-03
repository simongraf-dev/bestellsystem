from uuid import UUID

from pydantic import BaseModel

class ArticleInfo(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}

class StorageLocationInfo(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class ArticleStorageLocationCreate(BaseModel):
    article_id: UUID
    storage_location_id: UUID



class ArticleStorageLocationResponse(BaseModel):
    article: ArticleInfo
    storage_location: StorageLocationInfo

    model_config = {"from_attributes": True}