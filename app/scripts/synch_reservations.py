import sys
import traceback

from app.database import SessionLocal
from app.services.reservation_service import sync_reservations
from app.utils.logging_config import setup_logging

logger = setup_logging()


def main() -> int:
    """
    Führt den Reservierungs-Sync aus.
    Gibt Exit-Code zurück: 0 = Erfolg, 1 = Fehler
    """
    logger.info("Reservierungs-Sync gestartet (Cronjob)")

    db = SessionLocal()
    try:
        result = sync_reservations(db, forecast_days=14)

        if result.get("status") == "success":
            logger.info(f"Sync erfolgreich: {result['bookings_fetched']} Buchungen, {result['entries_saved']} Einträge")
            return 0
        else:
            logger.error(f"Sync fehlgeschlagen: {result.get('message', 'Unbekannter Fehler')}")
            return 1

    except Exception as e:
        logger.error(f"Sync fehlgeschlagen: {e}")
        logger.error(traceback.format_exc())
        return 1
    finally:
        db.close()
        logger.info("Reservierungs-Sync beendet")


if __name__ == "__main__":
    sys.exit(main())
