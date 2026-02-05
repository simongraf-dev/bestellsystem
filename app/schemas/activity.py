from uuid import UUID
from datetime import datetime

from pydantic import BaseModel
from typing import Optional

from app.models.activity_log import ActionType

class UserInfo(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}

class ActivityResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    user: UserInfo
    timestamp: datetime
    action_type: ActionType
    description: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    details: Optional[dict] = None

    model_config = {"from_attributes": True}

