import logging
import time
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

# Retry-Konfiguration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def _get_berlin_tz():
    """Gibt die Berlin-Timezone zurück (mit Sommer-/Winterzeit)."""
    if ZoneInfo:
        return ZoneInfo("Europe/Berlin")
    # Fallback: UTC+1 für Winter, UTC+2 für Sommer (vereinfacht)
    # Hinweis: Dieser Fallback ist nicht 100% korrekt für Sommerzeitübergänge
    return timezone(timedelta(hours=1))


def _timestamp_to_berlin_datetime(timestamp_ms: int) -> datetime:
    """Konvertiert einen Millisekunden-Timestamp in eine Berlin-DateTime."""
    tz = _get_berlin_tz()
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=tz)


def _api_request_with_retry(url: str, payload: dict, headers: dict) -> dict | None:
    """Führt einen API-Request mit Retry-Logik aus."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                url=url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY_SECONDS * (2 ** attempt)
                logger.warning(f"API-Fehler (Versuch {attempt + 1}/{MAX_RETRIES}): {e}. Warte {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"API-Fehler nach {MAX_RETRIES} Versuchen: {e}")
                return None
    return None


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

        data = _api_request_with_retry(settings.teburio_url, payload, headers)

        if data is None:
            logger.error(f"API-Fehler auf Seite {page}: Keine Antwort nach Retries")
            return None  # Fehler: Keine unvollständigen Daten verwenden

        if 'errors' in data:
            logger.error(f"GraphQL Errors: {data['errors']}")
            return None  # Fehler: GraphQL-Fehler sind kritisch

        analytics = data.get('data', {}).get('bookingsAnalytics')
        if not analytics:
            logger.error("Ungültige API-Antwort: bookingsAnalytics fehlt")
            return None

        bookings = analytics.get('bookings', [])
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

    return all_bookings if all_bookings else None


def _booking_to_timeslot(booking_timestamp_ms: int) -> TimeSlot:
    """
    Bestimmt anhand des Buchungs-Timestamps ob Mittag oder Abend.
    """
    booking_dt = _timestamp_to_berlin_datetime(booking_timestamp_ms)

    if booking_dt.hour < MITTAG_ABEND_GRENZE:
        return TimeSlot.MITTAG
    else:
        return TimeSlot.ABEND


def sync_reservations(db: Session, forecast_days: int = 14):
    """
    Hauptfunktion: Holt Buchungsdaten von Teburio und speichert
    aggregierte Zusammenfassungen in der DB.
    """
    tz = _get_berlin_tz()
    today = date.today()
    end = today + timedelta(days=forecast_days)

    # Datumsstrings für API
    start_dt = datetime.combine(today, datetime.min.time()).replace(tzinfo=tz)
    end_dt = datetime.combine(end, datetime.max.time().replace(microsecond=0)).replace(tzinfo=tz)
    start_str = start_dt.isoformat()
    end_str = end_dt.isoformat()

    logger.info(f"Starte Reservierungs-Sync: {today} bis {end}")

    # 1. Buchungen von API holen
    bookings = fetch_bookings_from_teburio(start_str, end_str)

    # None = API-Fehler, [] = keine Buchungen (beides unterschiedlich behandeln)
    if bookings is None:
        logger.error("API-Fehler: Sync abgebrochen")
        return {"status": "error", "message": "API-Fehler beim Abrufen der Buchungen"}

    logger.info(f"{len(bookings)} Buchungen von Teburio erhalten")

    # 2. Aggregieren: Pro Tag + Zeitfenster zählen
    # Initialisiere alle Tage mit 0 (damit Tage ohne Buchungen auch gespeichert werden)
    daily_stats = {}
    for day_offset in range(forecast_days + 1):
        current_date = today + timedelta(days=day_offset)
        for slot in TimeSlot:
            daily_stats[(current_date, slot)] = {'reservations': 0, 'guests': 0}

    for booking in bookings:
        # Stornierte und No-Shows ignorieren
        if booking.get('cancelled') or booking.get('noShow'):
            continue

        # Konsistente Timezone-Konvertierung
        booking_dt = _timestamp_to_berlin_datetime(booking['date'])
        booking_date = booking_dt.date()
        time_slot = _booking_to_timeslot(booking['date'])
        people = booking.get('people', 0)

        key = (booking_date, time_slot)
        if key in daily_stats:
            daily_stats[key]['reservations'] += 1
            daily_stats[key]['guests'] += people

    # 3. In DB speichern (UPSERT: Update wenn existiert, Insert wenn neu)
    saved = 0
    now = datetime.now(timezone.utc)

    for (forecast_date, time_slot), stats in daily_stats.items():
        existing = db.query(ReservationSummary).filter(
            ReservationSummary.forecast_date == forecast_date,
            ReservationSummary.time_slot == time_slot
        ).first()

        if existing:
            existing.total_reservations = stats['reservations']
            existing.total_guests = stats['guests']
            existing.synced_at = now
        else:
            new_entry = ReservationSummary(
                forecast_date=forecast_date,
                time_slot=time_slot,
                total_reservations=stats['reservations'],
                total_guests=stats['guests'],
                synced_at=now
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
