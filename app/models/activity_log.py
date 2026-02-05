import uuid
import enum

from sqlalchemy import Column, DateTime, Enum, Text, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base

class ActionType(enum.Enum):
    ORDER_CREATED = "ORDER CREATED"
    ORDER_COMPLETED = "ORDER COMPLETED"
    ORDER_SENT = "ORDER SENT"
    ORDER_CANCELLED = "ORDER CANCELLED"
    FOLLOW_UP_ORDER_CREATED = "FOLLOW UP ORDER CREATED"
    ITEM_ADDED = "ITEM ADDED"
    ITEM_REMOVED = "ITEM REMOVED"
    ITEM_QUANTITY_CHANGED = "ITEM QUANTITY CHANGED"
    SUPPLIER_CHANGED = "SUPPLIER CHANGED"
    DELIVERY_DATE_CHANGED = "DELIVERY DATE CHANGED"
    NOTE_CHANGED = "NOTE CHANGED"
    DELIVERY_NOTE_CHANGED = "DELIVERY NOTE CHANGED"
    ADDITIONAL_ARTICLES_CHANGED = "ADDITIONAL ARTICLES CHANGED"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    user = relationship("User")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    action_type = Column(Enum(ActionType), nullable=False)
    description = Column(Text, nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    

