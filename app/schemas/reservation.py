from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel
from typing import Optional



class ReservationSummaryResponse(BaseModel):
    """Einzelner Eintrag: Ein Tag + Zeitfenster"""
    id: UUID
    forecast_date: date
    time_slot: str         
    total_reservations: int
    total_guests: int
    synced_at: datetime

    model_config = {"from_attributes": True}


class DailyReservationResponse(BaseModel):
    """Tagesübersicht: Mittag + Abend kombiniert"""
    forecast_date: date
    mittag_reservations: int
    mittag_guests: int
    abend_reservations: int
    abend_guests: int
    total_reservations: int
    total_guests: int


class ReservationOverviewResponse(BaseModel):
    """Gesamtübersicht für die nächsten X Tage"""
    days: list[DailyReservationResponse]
    last_synced: Optional[datetime] = None