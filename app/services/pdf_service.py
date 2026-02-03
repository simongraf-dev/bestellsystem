"""
PDF-Generierung für ShippingGroups.

Erstellt minimalistisch-schicke Bestellungs-PDFs für Lieferanten.
"""
from io import BytesIO
from uuid import UUID
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    Image, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from sqlalchemy.orm import Session

from app.models import ShippingGroup, OrderItem, DepartmentSupplier
from app.config import settings




# ============ KONFIGURATION ============

COMPANY_NAME = settings.company_name
COMPANY_ADDRESS = settings.company_address
COMPANY_CITY = settings.company_city
COMPANY_PHONE = settings.company_phone
COMPANY_EMAIL = settings.company_email

# Logo-Pfad (optional, None wenn kein Logo)
LOGO_PATH = None 


# ============ STYLES ============

def get_custom_styles():
    """Erstellt custom Paragraph-Styles für das PDF."""
    styles = getSampleStyleSheet()
    
    # Titel
    styles.add(ParagraphStyle(
        name='DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=6*mm,
        textColor=colors.HexColor('#333333')
    ))
    
    # Absender (klein, grau)
    styles.add(ParagraphStyle(
        name='Sender',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#666666')
    ))
    
    # Empfänger
    styles.add(ParagraphStyle(
        name='Recipient',
        parent=styles['Normal'],
        fontSize=11,
        leading=14
    ))
    
    # Section Header (z.B. Department-Name)
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=8*mm,
        spaceAfter=3*mm,
        textColor=colors.HexColor('#444444')
    ))
    
    # Notizen
    styles.add(ParagraphStyle(
        name='Notes',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#555555'),
        leftIndent=5*mm
    ))
    
    # Footer
    styles.add(ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#888888'),
        alignment=TA_CENTER
    ))
    
    return styles


# ============ HILFSFUNKTIONEN ============

def format_date(d: date) -> str:
    """Formatiert Datum auf Deutsch."""
    if d is None:
        return "Nach Absprache"
    return d.strftime("%d.%m.%Y")


def generate_short_id(uuid: UUID) -> str:
    """Generiert eine kurze Referenz-ID aus der UUID."""
    return f"SG-{str(uuid)[:8].upper()}"


def get_customer_number(db: Session, department_id: UUID, supplier_id: UUID) -> str | None:
    """Holt die Kundennummer für ein Department bei einem Lieferanten."""
    dept_supplier = db.query(DepartmentSupplier).filter(
        DepartmentSupplier.department_id == department_id,
        DepartmentSupplier.supplier_id == supplier_id
    ).first()
    
    if dept_supplier and dept_supplier.customer_number:
        return dept_supplier.customer_number
    return None


# ============ PDF GENERIERUNG ============

def generate_shipping_group_pdf(
    db: Session, 
    shipping_group: ShippingGroup,
    approved_by: str
) -> bytes:
    """
    Generiert ein PDF für eine ShippingGroup.
    
    Args:
        db: Datenbank-Session
        shipping_group: Die ShippingGroup mit geladenen Relationships
        approved_by: Name des Freigebers
        
    Returns:
        PDF als bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    styles = get_custom_styles()
    story = []
    
    # ---- HEADER ----
    
    # Logo (falls vorhanden)
    if LOGO_PATH:
        try:
            logo = Image(LOGO_PATH, width=40*mm, height=15*mm)
            story.append(logo)
            story.append(Spacer(1, 5*mm))
        except:
            pass  # Logo nicht gefunden, weitermachen
    
    # Absender-Zeile (klein)
    sender_line = f"{COMPANY_NAME} · {COMPANY_ADDRESS} · {COMPANY_CITY}"
    story.append(Paragraph(sender_line, styles['Sender']))
    story.append(Spacer(1, 8*mm))
    
    # Empfänger (Lieferant)
    supplier = shipping_group.supplier
    if supplier:
        recipient_text = f"<b>{supplier.name}</b>"
        if supplier.email:
            recipient_text += f"<br/>{supplier.email}"
        story.append(Paragraph(recipient_text, styles['Recipient']))
    
    story.append(Spacer(1, 10*mm))
    
    # ---- TITEL + META ----
    
    story.append(Paragraph("Bestellung", styles['DocTitle']))
    
    # Meta-Informationen als kleine Tabelle
    ref_id = generate_short_id(shipping_group.id)
    meta_data = [
        ["Bestellnummer:", ref_id],
        ["Lieferdatum:", format_date(shipping_group.delivery_date)],
        ["Freigegeben von:", approved_by],
        ["Freigabedatum:", format_date(date.today())],
    ]
    
    meta_table = Table(meta_data, colWidths=[35*mm, 60*mm])
    meta_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8*mm))
    
    # Trennlinie
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc')))
    story.append(Spacer(1, 5*mm))
    
    # ---- ARTIKEL NACH DEPARTMENT GRUPPIERT ----
    
    # Items nach Department gruppieren
    items_by_department = {}
    for item in shipping_group.items:
        if not item.order or not item.order.is_active:
            continue
            
        dept_id = item.order.department_id
        dept_name = item.order.department.name if item.order.department else "Unbekannt"
        
        if dept_id not in items_by_department:
            items_by_department[dept_id] = {
                "name": dept_name,
                "items": [],
                "notes": []
            }
        
        items_by_department[dept_id]["items"].append(item)
        
        # Order-Notizen sammeln (nur einmal pro Order)
        if item.order.delivery_notes:
            if item.order.delivery_notes not in items_by_department[dept_id]["notes"]:
                items_by_department[dept_id]["notes"].append(item.order.delivery_notes)
    
    # Pro Department einen Block
    for dept_id, dept_data in items_by_department.items():
        # Department-Header mit Kundennummer
        customer_number = get_customer_number(db, dept_id, shipping_group.supplier_id)
        
        header_text = f"<b>{dept_data['name']}</b>"
        if customer_number:
            header_text += f" <font size='9' color='#666666'>(Kd.-Nr.: {customer_number})</font>"
        
        story.append(Paragraph(header_text, styles['SectionHeader']))
        
        # Artikeltabelle
        table_data = [["Menge", "Einheit", "Artikel", "Art.-Nr.", "Notiz"]]
        
        for item in dept_data["items"]:
            article_name = item.article.name if item.article else "–"
            
            # Artikelnummer vom Lieferanten (aus ArticleSupplier)
            art_nr = "–"
            if item.article:
                from app.models import ArticleSupplier
                art_sup = db.query(ArticleSupplier).filter(
                    ArticleSupplier.article_id == item.article_id,
                    ArticleSupplier.supplier_id == shipping_group.supplier_id
                ).first()
                if art_sup and art_sup.article_number_supplier:
                    art_nr = art_sup.article_number_supplier
            
            note = item.note or ""
            
            table_data.append([
                str(item.amount),
                item.article.unit if item.article else "–",
                article_name,
                art_nr,
                Paragraph(note, styles['Notes']) if note else ""
            ])
        
        # Tabelle formatieren
        article_table = Table(
            table_data, 
            colWidths=[15*mm, 20*mm, 55*mm, 25*mm, 45*mm]
        )
        article_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            
            # Body
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            
            # Grid
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#cccccc')),
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#eeeeee')),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor('#cccccc')),
        ]))
        story.append(article_table)
        
        # Liefernotizen für dieses Department
        if dept_data["notes"]:
            story.append(Spacer(1, 3*mm))
            for note in dept_data["notes"]:
                story.append(Paragraph(f"<i>Hinweis: {note}</i>", styles['Notes']))
    
    # ---- ZUSÄTZLICHE ARTIKEL (Freitext) ----
    
    # Sammle alle additional_articles aus den Orders
    additional_articles = []
    for item in shipping_group.items:
        if item.order and item.order.additional_articles:
            if item.order.additional_articles not in additional_articles:
                additional_articles.append(item.order.additional_articles)
    
    if additional_articles:
        story.append(Spacer(1, 8*mm))
        story.append(Paragraph("<b>Zusätzliche Artikel:</b>", styles['Normal']))
        story.append(Spacer(1, 2*mm))
        for text in additional_articles:
            story.append(Paragraph(text, styles['Notes']))
    
    # ---- FOOTER ----
    
    story.append(Spacer(1, 15*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc')))
    story.append(Spacer(1, 3*mm))
    
    footer_text = f"{COMPANY_NAME} · {COMPANY_PHONE} · {COMPANY_EMAIL}"
    story.append(Paragraph(footer_text, styles['Footer']))
    
    # PDF bauen
    doc.build(story)
    
    return buffer.getvalue()