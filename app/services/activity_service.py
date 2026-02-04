from sqlalchemy.orm import Session
from app.models.activity_log import ActivityLog, ActionType
from uuid import UUID
from typing import Optional, Any



def log_activity(
    db: Session,
    entity_type: str,
    entity_id: UUID,
    user_id: UUID,
    action_type: ActionType,
    description: str,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    details: Optional[dict] = None
):
    new_activity_log = ActivityLog(
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        action_type=action_type,
        description=description,
        old_value=old_value,
        new_value=new_value,
        details=details
    )
    db.add(new_activity_log)
    db.commit()