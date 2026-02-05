
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.services.reservation_service import sync_reservations
from app.utils.logging_config import setup_logging

logger = setup_logging()

def main():     
    logger.info("Reservierungs-Sync gestartet (Cronjob)")

    db = SessionLocal()
    try:
        result = sync_reservations(db, forecast_days=14)
        logger.info(f"Ergebnis: {result}")
    except Exception as e:
        logger.error(f"Sync fehlgeschlagen: {e}")
    finally:
        db.close()

    logger.info("Reservierungs-Sync beendet")

if __name__ == "__main__":
    main()
