import uuid
import enum
from datetime import date, datetime, timezone

from sqlalchemy import Column, Date, Integer, DateTime, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class TimeSlot(enum.Enum):
    MITTAG = "MITTAG"       
    ABEND = "ABEND"         


class ReservationSummary(Base):
    """
    Aggregierte Reservierungsdaten pro Tag und Zeitfenster.
    Wird regelmäßig per Cronjob von Teburio API aktualisiert.
    """
    __tablename__ = "reservation_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    forecast_date = Column(Date, nullable=False)
    time_slot = Column(Enum(TimeSlot), nullable=False)
    total_reservations = Column(Integer, nullable=False, default=0)
    total_guests = Column(Integer, nullable=False, default=0)
    synced_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    
    __table_args__ = (
        UniqueConstraint('forecast_date', 'time_slot', name='uq_date_timeslot'),
    )