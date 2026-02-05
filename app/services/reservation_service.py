import logging
import requests
from datetime import datetime, date, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

from sqlalchemy.orm import Session
from app.models.reservation import ReservationSummary, TimeSlot
from app.config import settings

logger = logging.getLogger("app.services.reservation_service")

# Grenzwert: Buchungen VOR dieser Stunde = Mittag, danach = Abend
MITTAG_ABEND_GRENZE = 16 


def fetch_bookings_from_teburio(start_date: str, end_date: str) -> list | None:
    """
    Holt Buchungen von der Teburio GraphQL API mit Pagination.
    
    """

    query = """
    query bookingsAnalytics($locationId: String!, $date: Date!, $endDate: Date!, $startingAfter: Date) {
        bookingsAnalytics(locationId: $locationId, date: $date, endDate: $endDate, startingAfter: $startingAfter) {
            cursor
            hasMore
            count
            bookings {
                _id
                date
                endDate
                people
                cancelled
                noShow
                walkIn
                source
                __typename
            }
            __typename
        }
    }
    """

    all_bookings = []
    cursor = None
    page = 1

    # Diese Settings musst du in deiner config.py ergänzen:
    # TEBURIO_URL, TEBURIO_TOKEN, TEBURIO_LOCATION_ID
    headers = {
        "content-type": "application/json",
        "account_token": settings.teburio_token
    }

    while True:
        payload = {
            "operationName": "bookingsAnalytics",
            "query": query,
            "variables": {
                "locationId": settings.teburio_location_id,
                "date": start_date,
                "endDate": end_date,
                "startingAfter": cursor
            }
        }

        try:
            response = requests.post(
                url=settings.teburio_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if 'errors' in data:
                logger.error(f"GraphQL Errors: {data['errors']}")
                break

            analytics = data['data']['bookingsAnalytics']
            bookings = analytics['bookings']
            all_bookings.extend(bookings)

            logger.info(f"Seite {page}: {len(bookings)} Buchungen geholt (Gesamt: {len(all_bookings)})")

            if not analytics.get('hasMore', False):
                break

            cursor = analytics.get('cursor')
            if not cursor:
                break

            page += 1
            if page > 50:
                logger.warning("Sicherheits-Abbruch: Zu viele Seiten")
                break

        except requests.exceptions.RequestException as e:
            logger.error(f"API-Fehler auf Seite {page}: {e}")
            break

    return all_bookings if all_bookings else None


def _booking_to_timeslot(booking_timestamp_ms: int) -> TimeSlot:
    """
    Bestimmt anhand des Buchungs-Timestamps ob Mittag oder Abend.
    """
    if ZoneInfo:
        tz = ZoneInfo("Europe/Berlin")
        booking_dt = datetime.fromtimestamp(booking_timestamp_ms / 1000, tz=tz)
    else:
        # Fallback: UTC + 1
        booking_dt = datetime.fromtimestamp(booking_timestamp_ms / 1000, tz=timezone.utc)

    hour = booking_dt.hour

    if hour < MITTAG_ABEND_GRENZE:
        return TimeSlot.MITTAG
    else:
        return TimeSlot.ABEND


def sync_reservations(db, forecast_days: int = 14):
    """
    Hauptfunktion: Holt Buchungsdaten von Teburio und speichert
    aggregierte Zusammenfassungen in der DB.
    """
    today = date.today()
    end = today + timedelta(days=forecast_days)

    # Datumsstrings für API
    if ZoneInfo:
        tz = ZoneInfo("Europe/Berlin")
        start_dt = datetime.combine(today, datetime.min.time()).replace(tzinfo=tz)
        end_dt = datetime.combine(end, datetime.max.time()).replace(tzinfo=tz)
        start_str = start_dt.isoformat()
        end_str = end_dt.isoformat()
    else:
        start_str = today.strftime("%Y-%m-%dT00:00:00+01:00")
        end_str = end.strftime("%Y-%m-%dT23:59:59+01:00")

    logger.info(f"Starte Reservierungs-Sync: {today} bis {end}")

    # 1. Buchungen von API holen
    bookings = fetch_bookings_from_teburio(start_str, end_str)

    if not bookings:
        logger.warning("Keine Buchungen von API erhalten")
        return {"status": "error", "message": "Keine Buchungen erhalten"}

    logger.info(f"{len(bookings)} Buchungen von Teburio erhalten")

    # 2. Aggregieren: Pro Tag + Zeitfenster zählen
    daily_stats = {}  # {(date, TimeSlot): {reservations: X, guests: Y}}

    for booking in bookings:
        # Stornierte und No-Shows ignorieren
        if booking.get('cancelled') or booking.get('noShow'):
            continue

        booking_date = datetime.fromtimestamp(booking['date'] / 1000).date()
        time_slot = _booking_to_timeslot(booking['date'])
        people = booking.get('people', 0)

        key = (booking_date, time_slot)
        if key not in daily_stats:
            daily_stats[key] = {'reservations': 0, 'guests': 0}

        daily_stats[key]['reservations'] += 1
        daily_stats[key]['guests'] += people

    # 3. In DB speichern (UPSERT: Update wenn existiert, Insert wenn neu)
    saved = 0
    for (forecast_date, time_slot), stats in daily_stats.items():
        existing = db.query(ReservationSummary).filter(
            ReservationSummary.forecast_date == forecast_date,
            ReservationSummary.time_slot == time_slot
        ).first()

        if existing:
            existing.total_reservations = stats['reservations']
            existing.total_guests = stats['guests']
            existing.synced_at = datetime.now(timezone.utc)
        else:
            new_entry = ReservationSummary(
                forecast_date=forecast_date,
                time_slot=time_slot,
                total_reservations=stats['reservations'],
                total_guests=stats['guests']
            )
            db.add(new_entry)

        saved += 1

    db.commit()
    logger.info(f"Sync fertig: {saved} Einträge gespeichert/aktualisiert")

    return {
        "status": "success",
        "bookings_fetched": len(bookings),
        "entries_saved": saved
    }
