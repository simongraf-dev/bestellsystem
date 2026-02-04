"""
Email-Service für den Versand von Bestellungen an Lieferanten.
"""
from datetime import date
from pathlib import Path

from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig
import logging
from app.config import settings

logger = logging.getLogger("app.services.email_service")


# ============ KONFIGURATION ============

conf = ConnectionConfig(
    MAIL_USERNAME=settings.smtp_user,
    MAIL_PASSWORD=settings.smtp_password,
    MAIL_FROM=settings.smtp_from,
    MAIL_PORT=settings.smtp_port,
    MAIL_SERVER=settings.smtp_host,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


# ============ HILFSFUNKTIONEN ============

def format_date(d: date) -> str:
    """Formatiert Datum auf Deutsch."""
    if d is None:
        return "nach Absprache"
    return d.strftime("%d.%m.%Y")


# ============ EMAIL VERSAND ============

async def send_order_email(
    to_email: str,
    supplier_name: str,
    delivery_date: date | None,
    pdf_path: str,
    order_reference: str
) -> dict:
    """
    Sendet Bestellungs-Email mit PDF an Lieferanten.
    
    Args:
        to_email: Email-Adresse des Lieferanten
        supplier_name: Name des Lieferanten (für Anrede)
        delivery_date: Gewünschtes Lieferdatum
        pdf_path: Pfad zur PDF-Datei
        order_reference: Bestellnummer (z.B. "SG-A7F3B2")
        
    Returns:
        Dict mit {"success": bool, "error": str|None}
    """
    # Email-Text
    delivery_text = format_date(delivery_date)
    
    body = f"""Guten Tag,

anbei erhalten Sie unsere Bestellung für Lieferung am {delivery_text}.

Bestellnummer: {order_reference}

Bei Rückfragen stehen wir Ihnen gerne zur Verfügung.

Mit freundlichen Grüßen
{settings.company_name}

---
{settings.company_address}
{settings.company_city}
Tel: {settings.company_phone}
"""

    # Attachment vorbereiten
    attachments = []
    if pdf_path and Path(pdf_path).exists():
        attachments.append(pdf_path)
    
    # Message erstellen
    message = MessageSchema(
        subject=f"Bestellung {order_reference} - Lieferung {delivery_text}",
        recipients=[to_email],
        body=body,
        subtype=MessageType.plain,
        attachments=attachments
    )
    
    # Senden
    try:
        fm = FastMail(conf)
        await fm.send_message(message)
        return {"success": True, "error": None}
    except Exception as e:
        logger.error(f"EMAIL FEHLER: {e}")
        return {"success": False, "error": str(e)}


async def send_order_email_to_supplier(
    to_email: str,
    cc_emails: list[str] | None,
    supplier_name: str,
    delivery_date: date | None,
    pdf_path: str,
    order_reference: str
) -> bool:
    """
    Erweiterte Version mit CC-Empfängern.
    
    Args:
        to_email: Haupt-Empfänger (Lieferant)
        cc_emails: Liste von CC-Empfängern (z.B. interner Verteiler)
        supplier_name: Name des Lieferanten
        delivery_date: Gewünschtes Lieferdatum
        pdf_path: Pfad zur PDF-Datei
        order_reference: Bestellnummer
        
    Returns:
        True wenn erfolgreich, False bei Fehler
    """
    delivery_text = format_date(delivery_date)
    
    body = f"""Guten Tag,

anbei erhalten Sie unsere Bestellung für Lieferung am {delivery_text}.

Bestellnummer: {order_reference}

Bei Rückfragen stehen wir Ihnen gerne zur Verfügung.

Mit freundlichen Grüßen
{settings.company_name}

---
{settings.company_address}
{settings.company_city}
Tel: {settings.company_phone}
"""

    attachments = []
    if pdf_path and Path(pdf_path).exists():
        attachments.append(pdf_path)
    
    message = MessageSchema(
        subject=f"Bestellung {order_reference} - Lieferung {delivery_text}",
        recipients=[to_email],
        cc=cc_emails or [],
        body=body,
        subtype=MessageType.plain,
        attachments=attachments
    )
    
    try:
        fm = FastMail(conf)
        await fm.send_message(message)
        return True
    except Exception as e:
        logger.error(f"EMAIL FEHLER: {e}")
        return False