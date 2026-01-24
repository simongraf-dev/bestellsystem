from sqlalchemy import Column, DateTime, Enum, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid
import enum
from datetime import datetime, timezone

from app.database import Base

class ActionType(enum.Enum):
    ORDER_CREATED = "ORDER CREATED"
    ORDER_COMPLETED = "ORDER COMPLETED"
    ORDER_SENT = "ORDER SENT"
    ORDER_CANCELLED = "ORDER CANCELLED"
    FOLLOW_UP_ORDER_CREATED = "FOLLOW UP ORDER CREATED"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    action_type = Column(Enum(ActionType), nullable=False)
    description = Column(Text, nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    is_major_event = Column(Boolean, nullable=False)

