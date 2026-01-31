from sqlalchemy import Column, Enum, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from sqlalchemy.orm import relationship

from app.database import Base

class ShippingGroupStatus(enum.Enum):
    OFFEN = "OFFEN"
    VERSENDET = "VERSENDET"
    STORNIERT = "STORNIERT"


class ShippingGroup(Base):
    __tablename__ = "shipping_groups"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    delivery_date = Column(Date, nullable=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    send_date = Column(DateTime, nullable=True)
    status = Column(Enum(ShippingGroupStatus), nullable=False, default=ShippingGroupStatus.OFFEN)

    items = relationship("OrderItem", back_populates="shipping_group")
    supplier = relationship("Supplier")
    items = relationship("OrderItem", back_populates="shipping_group")