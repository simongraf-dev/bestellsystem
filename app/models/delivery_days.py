from sqlalchemy import ForeignKey, Column, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from app.database import Base

class Weekday(enum.Enum):
    MO = "MO"
    DI = "DI"
    MI = "MI"
    DO = "DO"
    FR = "FR"
    SA = "SA"
    SO = "SO"

class DeliveryDay(Base):
    __tablename__ = "delivery_days"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    weekday = Column(Enum(Weekday), nullable=False)