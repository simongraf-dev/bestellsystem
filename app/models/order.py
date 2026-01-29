from sqlalchemy import Text, DateTime, Column, ForeignKey, Enum, Date, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy.orm import relationship

from app.database import Base

class OrderStatus(enum.Enum):
    ENTWURF = "ENTWURF"
    VOLLSTAENDIG = "VOLLSTAENDIG"
    BESTELLT = "BESTELLT"
    STORNIERT = "STORNIERT"

class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    delivery_date = Column(Date, nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.ENTWURF)
    additional_articles = Column(Text, nullable=True)
    delivery_notes = Column(Text, nullable=True)
    drafted_on = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_on = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    department = relationship("Department")
    creator = relationship("User", foreign_keys=[creator_id])
    approver = relationship("User", foreign_keys=[approver_id])
    items = relationship("OrderItem", back_populates="order")
