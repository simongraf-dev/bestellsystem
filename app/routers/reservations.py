import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.reservation import ReservationSummary, TimeSlot
from app.schemas.reservation import (
     ReservationOverviewResponse,
     DailyReservationResponse
)
from app.utils.security import get_current_user

logger = logging.getLogger("app.routers.reservations")

router = APIRouter(prefix="/reservations", tags=["reservations"])

@router.get("/overview", response_model=ReservationOverviewResponse)
def get_reservation_overview(
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Gibt die Reservierungsübersicht für die nächsten X Tage zurück.
    Jeder Tag zeigt Mittag + Abend separat und als Summe.
    """
    today = date.today()
    end = today + timedelta(days=days)

    # Alle Einträge im Zeitraum laden
    summaries = db.query(ReservationSummary).filter(
        ReservationSummary.forecast_date >= today,
        ReservationSummary.forecast_date <= end
    ).order_by(
        ReservationSummary.forecast_date
    ).all()

    # Nach Datum gruppieren
    by_date = {}
    last_synced = None

    for s in summaries:
        if s.forecast_date not in by_date:
            by_date[s.forecast_date] = {
                "mittag_reservations": 0,
                "mittag_guests": 0,
                "abend_reservations": 0,
                "abend_guests": 0
            }

        if s.time_slot == TimeSlot.MITTAG:
            by_date[s.forecast_date]["mittag_reservations"] = s.total_reservations
            by_date[s.forecast_date]["mittag_guests"] = s.total_guests
        elif s.time_slot == TimeSlot.ABEND:
            by_date[s.forecast_date]["abend_reservations"] = s.total_reservations
            by_date[s.forecast_date]["abend_guests"] = s.total_guests

        # Letzten Sync-Zeitpunkt tracken
        if not last_synced or s.synced_at > last_synced:
            last_synced = s.synced_at

    # Response bauen (auch Tage OHNE Reservierungen zeigen)
    daily_list = []
    for i in range(days):
        d = today + timedelta(days=i)
        data = by_date.get(d, {
            "mittag_reservations": 0,
            "mittag_guests": 0,
            "abend_reservations": 0,
            "abend_guests": 0
        })

        daily_list.append(DailyReservationResponse(
            forecast_date=d,
            mittag_reservations=data["mittag_reservations"],
            mittag_guests=data["mittag_guests"],
            abend_reservations=data["abend_reservations"],
            abend_guests=data["abend_guests"],
            total_reservations=data["mittag_reservations"] + data["abend_reservations"],
            total_guests=data["mittag_guests"] + data["abend_guests"]
        ))

    return ReservationOverviewResponse(
        days=daily_list,
        last_synced=last_synced
    )
