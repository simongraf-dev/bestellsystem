# Security & Logic Review: TraumGmbH Bestellsystem

**Datum:** 2026-02-12
**Reviewer:** Claude (automatisierte Code-Review)
**Scope:** Gesamtes FastAPI-Backend (`app/`-Verzeichnis)
**Stack:** FastAPI, SQLAlchemy, PostgreSQL, JWT Auth mit 2FA (TOTP)

---

## Inhaltsverzeichnis

1. [Security Findings](#security-findings)
2. [Logic Findings](#logic-findings)
3. [Code-Fehler (Syntax/Runtime)](#code-fehler-syntaxruntime)
4. [Zusammenfassung](#zusammenfassung)

---

## Security Findings

---

### S-01: Deaktivierte User behalten Zugang über gültige Tokens

- **Datei:** `app/utils/security.py:63-74`
- **Severity:** 🔴 Critical
- **Kategorie:** Security – Authentication

**Beschreibung:**
Die Funktion `get_current_user()` prüft **nicht**, ob der User aktiv ist (`is_active`). Ein deaktivierter User kann mit einem noch gültigen Access-Token (30 Min.) weiterhin alle Endpoints nutzen. Über den Refresh-Endpoint (s. S-02) kann der Zugang sogar unbegrenzt verlängert werden.

**Risiko:**
Ein deaktivierter Mitarbeiter behält vollen Systemzugang, solange sein Token gültig ist – potenziell dauerhaft über Refresh-Tokens.

**Empfehlung:**
`is_active`-Check in `get_current_user()` ergänzen:
```python
def get_current_user(...) -> User:
    ...
    user = db.query(User).options(...).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User nicht in DB")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account deaktiviert")
    return user
```

---

### S-02: Refresh-Endpoint prüft User-Status nicht

- **Datei:** `app/routers/auth.py:52-65`
- **Severity:** 🔴 Critical
- **Kategorie:** Security – Authentication

**Beschreibung:**
Der `/auth/refresh`-Endpoint dekodiert lediglich das Refresh-Token und stellt neue Tokens aus, **ohne** den User in der Datenbank zu laden. Es wird weder geprüft, ob der User noch existiert, noch ob er aktiv ist.

**Risiko:**
Ein gelöschter oder deaktivierter User kann unbegrenzt neue Access-Tokens generieren (Refresh-Token gültig für 7 Tage, und mit jedem Refresh wird auch ein neues Refresh-Token ausgestellt → endloser Zugang).

**Empfehlung:**
User im Refresh-Endpoint aus der DB laden und Status prüfen:
```python
@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(request: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(request.refresh_token, "refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Refresh Token abgelaufen")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User nicht berechtigt")
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
```

---

### S-03: CORS-Konfiguration erlaubt alle Origins mit Credentials

- **Datei:** `app/main.py:26-32`
- **Severity:** 🔴 Critical
- **Kategorie:** Security – Konfiguration

**Beschreibung:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    ...
)
```
Starlettes `CORSMiddleware` reflektiert bei `allow_origins=["*"]` + `allow_credentials=True` den Request-Origin in der Response. Damit kann **jede beliebige Website** authentifizierte Requests an das Backend senden.

**Risiko:**
Ein Angreifer könnte über eine präparierte Website im Namen eines eingeloggten Users Bestellungen aufgeben oder Daten auslesen (CSRF-ähnlicher Angriff).

**Empfehlung:**
Explizite Origins konfigurieren:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bestellsystem.traumgmbh.de"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### S-04: 2FA-Validate prüft is_active nicht

- **Datei:** `app/routers/auth.py:113-139`
- **Severity:** 🟠 High
- **Kategorie:** Security – Authentication

**Beschreibung:**
Der `/auth/2fa/validate`-Endpoint lädt den User per `temp_token`, prüft den TOTP-Code und stellt Tokens aus – **ohne** den `is_active`-Status zu prüfen. Ein User könnte zwischen Login (wo `is_active` geprüft wird) und 2FA-Validierung deaktiviert werden.

**Risiko:**
Race Condition: User wird nach Login-Schritt-1 deaktiviert, kann aber über den 2FA-Schritt trotzdem Tokens erhalten.

**Empfehlung:**
`is_active`-Check nach dem User-Laden ergänzen:
```python
if not user or not user.is_active:
    raise HTTPException(status_code=401, detail="Account deaktiviert")
```

---

### S-05: Tokens werden bei Passwort-Änderung nicht invalidiert

- **Datei:** `app/routers/auth.py:142-157`, `app/utils/security.py:32-48`
- **Severity:** 🟠 High
- **Kategorie:** Security – Authentication

**Beschreibung:**
Nach einer Passwort-Änderung (oder Admin-Passwort-Reset über User-Update) bleiben alle bestehenden Access- und Refresh-Tokens gültig. Es gibt keinen Mechanismus zur Token-Invalidierung (kein `jti`-Tracking, keine Token-Versionierung, keine Blacklist).

**Risiko:**
Wenn ein Passwort geändert wird (z.B. nach Kompromittierung), können gestohlene Tokens bis zum Ablauf weiter genutzt werden.

**Empfehlung:**
Einen `token_version`-Counter im User-Model einführen. Bei Passwort-Änderung wird er inkrementiert. Die `token_version` wird im JWT-Payload gespeichert und bei `get_current_user()` gegen die DB geprüft.

---

### S-06: Article-Update Endpoint ohne Rollenprüfung

- **Datei:** `app/routers/article.py:89-100`
- **Severity:** 🟠 High
- **Kategorie:** Security – Authorization

**Beschreibung:**
Der `PATCH /articles/{id}`-Endpoint hat **keinen** `@require_role`-Decorator. Jeder authentifizierte User (auch Bedarfsmelder) kann beliebige Artikel bearbeiten – Name, Einheit, Gruppe, und `is_active`-Status ändern.

Zum Vergleich: `POST /articles/` und `DELETE /articles/{id}` erfordern korrekt die Rolle "Admin".

**Risiko:**
Nicht-Admin-User können Artikeldaten manipulieren, z.B. `is_active` auf `False` setzen und damit Artikel für alle löschen.

**Empfehlung:**
`@require_role(["Admin"])` hinzufügen:
```python
@router.patch("/{id}", response_model=ArticleResponse)
@require_role(["Admin"])
def update_article(...):
```

---

### S-07: department_supplier Update-Endpoint fehlt Depends()

- **Datei:** `app/routers/department_supplier.py:40`
- **Severity:** 🟠 High
- **Kategorie:** Security – Authentication (Bug)

**Beschreibung:**
```python
current_user: User = (get_current_user)  # FEHLER: Depends() fehlt!
```
Statt `Depends(get_current_user)` wird die Funktion `get_current_user` direkt als Default-Wert zugewiesen. Der `@require_role(["Admin"])`-Decorator versucht dann `current_user.role.name` auf dem Funktionsobjekt aufzurufen, was in einem `AttributeError` → HTTP 500 resultiert.

**Risiko:**
Der Endpoint ist effektiv defekt (immer 500). Kein direktes Sicherheitsrisiko, aber bei einer unvorsichtigen "Fehlerbehebung" (z.B. Entfernen des require_role-Decorators) wäre er komplett unauthentifiziert. Funktionalität ist nicht verfügbar.

**Empfehlung:**
```python
current_user: User = Depends(get_current_user)
```

---

### S-08: Inkonsistente Zugangskontrollen bei Order-Endpoints

- **Datei:** `app/routers/orders.py`, `app/services/order_service.py`
- **Severity:** 🟡 Medium
- **Kategorie:** Security – Authorization

**Beschreibung:**
Verschiedene Order-Endpoints nutzen unterschiedliche Logiken für die Department-basierte Zugriffskontrolle:

| Endpoint | Access Check | Sichtbarkeit |
|---|---|---|
| `GET /orders/` | `_get_visible_departments()` | Eigenes Dept + Parent + Siblings + Children |
| `GET /orders/{id}` | `department_id == user.department_id` | **Nur eigenes Department** |
| `POST /orders/` | `_is_descendant_of()` | Eigenes Dept + Nachfahren |
| `PATCH /orders/{id}` | `_can_edit_order()` → `_get_editable_departments()` | Eigenes Dept + Nachfahren (rekursiv) |
| `POST /orders/{id}/items` | `department_id == user.department_id` | **Nur eigenes Department** |

**Risiko:**
- User sieht eine Order in der Liste (GET /orders/), kann sie aber einzeln nicht aufrufen (GET /orders/{id} → 404)
- User erstellt eine Order für ein Child-Department, kann danach keine Items hinzufügen (403)

**Empfehlung:**
Einheitliche Helper-Funktion für "Kann User diese Order sehen/bearbeiten?" erstellen und in allen Endpoints verwenden. `get_order` sollte `_get_visible_departments()` nutzen, `add_item_to_order` sollte `_can_edit_order()` nutzen.

---

### S-09: Admin-Passwort-Reset ohne Mindestlängen-Validierung

- **Datei:** `app/schemas/user.py:34`, `app/routers/users.py:131-134`
- **Severity:** 🟡 Medium
- **Kategorie:** Security – Input Validation

**Beschreibung:**
`UserUpdate.password_plain` ist als `Optional[str] = None` definiert – ohne `min_length`-Validierung. Ein Admin kann ein leeres oder sehr kurzes Passwort setzen. Im Gegensatz dazu hat `UserCreate.password_plain` korrekt `min_length=8`.

**Risiko:**
Schwache Passwörter können über den Admin-Update-Endpunkt gesetzt werden.

**Empfehlung:**
```python
password_plain: Optional[str] = Field(default=None, min_length=8)
```

---

### S-10: Kein Rate-Limiting auf Refresh und Passwort-Änderung

- **Datei:** `app/routers/auth.py:52-65, 142-157`
- **Severity:** 🟡 Medium
- **Kategorie:** Security – Rate Limiting

**Beschreibung:**
Rate-Limiting ist korrekt auf Login (5/min), 2FA-Verify (3/min) und 2FA-Validate (5/min) konfiguriert. Aber der Refresh-Endpoint und die Passwort-Änderung haben **kein** Rate-Limiting.

**Risiko:**
- Refresh-Token-Brute-Force (theoretisch, JWTs sind lang)
- Passwort-Änderung: Rate-Limiting weniger kritisch, da eigenes Passwort nötig

**Empfehlung:**
Rate-Limiting auf `/auth/refresh` und `/auth/me/password` ergänzen.

---

### S-11: Kein Unique-Constraint auf User.email auf DB-Ebene

- **Datei:** `app/models/user.py:14`
- **Severity:** 🟡 Medium
- **Kategorie:** Security – Data Integrity

**Beschreibung:**
```python
email = Column(String(100), nullable=False)  # kein unique=True
```
Die Email-Eindeutigkeit wird nur in der Anwendungslogik geprüft (und dort nur gegen aktive User). Race Conditions könnten zu doppelten Emails führen.

**Risiko:**
Doppelte Email-Adressen in der Datenbank bei konkurrierenden Requests. Beim Re-Aktivieren eines Users könnte es Konflikte geben.

**Empfehlung:**
```python
email = Column(String(100), nullable=False, unique=True)
```
Und entsprechende Alembic-Migration.

---

### S-12: Email-Format wird nicht validiert

- **Datei:** `app/schemas/auth.py:7`, `app/schemas/user.py:22`
- **Severity:** 🔵 Low
- **Kategorie:** Security – Input Validation

**Beschreibung:**
Login und User-Erstellung verwenden `email: str` statt `EmailStr` aus Pydantic. Beliebige Strings werden als Email akzeptiert.

**Risiko:**
Ungültige Emails in der Datenbank; irrelevant für Login-Sicherheit, aber schlecht für Datenqualität.

**Empfehlung:**
```python
from pydantic import EmailStr
email: EmailStr
```

---

### S-13: Keine Passwort-Komplexitätsanforderungen

- **Datei:** `app/schemas/auth.py:42-43`, `app/schemas/user.py:23`
- **Severity:** 🔵 Low
- **Kategorie:** Security – Authentication

**Beschreibung:**
Passwörter erfordern nur `min_length=8`, aber keine Großbuchstaben, Zahlen oder Sonderzeichen.

**Risiko:**
Schwache Passwörter wie "passwort" oder "12345678" sind möglich. Für ein internes Gastro-Tool mit 2FA-Option ist das Risiko begrenzt.

**Empfehlung:**
Optional einen Pydantic-Validator ergänzen, der mindestens Buchstaben + Ziffern fordert. Oder bewusst auf Komplexitätsregeln verzichten und stattdessen eine Mindestlänge von 12+ setzen.

---

### S-14: Keine Pagination auf den meisten List-Endpoints

- **Datei:** Diverse Router (`users.py`, `orders.py`, `articles.py`, `suppliers.py`, etc.)
- **Severity:** 🔵 Low
- **Kategorie:** Security – DoS / Data Exposure

**Beschreibung:**
Die meisten `GET /`-Endpoints geben alle Datensätze ohne Limit zurück. Nur `GET /activities/` hat `skip`/`limit`-Parameter.

**Risiko:**
Bei großen Datenmengen können Responses sehr groß werden → Performance-Probleme. Für ein internes Tool mit begrenztem Datenvolumen ist das Risiko gering.

**Empfehlung:**
Pagination mit `skip`/`limit` auf allen List-Endpoints ergänzen, mindestens ein Server-seitiges Maximum setzen.

---

## Logic Findings

---

### L-01: ShippingGroup-Freigabe aktualisiert Order-Status nicht auf BESTELLT

- **Datei:** `app/routers/shipping_groups.py:94-203`
- **Severity:** 🟠 High
- **Kategorie:** Logic – Bestellprozess

**Beschreibung:**
Wenn eine ShippingGroup über `POST /{id}/freigeben` als VERSENDET markiert wird, bleiben die zugehörigen Orders im Status VOLLSTAENDIG. Es gibt keinen automatischen Übergang zu BESTELLT.

**Risiko:**
- Orders erscheinen weiterhin als "offen" obwohl sie bereits an den Lieferanten versendet wurden
- User könnten versuchen, diese Orders weiter zu bearbeiten
- Der Status BESTELLT wird nie gesetzt (kein Endpoint dafür)

**Empfehlung:**
Nach dem Versenden der ShippingGroup alle zugehörigen Orders auf BESTELLT setzen, deren Items vollständig in versendeten ShippingGroups sind.

---

### L-02: Order-Löschung berücksichtigt ShippingGroups nicht

- **Datei:** `app/routers/orders.py:141-157`
- **Severity:** 🟠 High
- **Kategorie:** Logic – Bestellprozess

**Beschreibung:**
Beim Soft-Delete einer Order (`DELETE /orders/{id}`) wird nur `order.is_active = False` gesetzt. Die zugehörigen OrderItems bleiben in ihren ShippingGroups. Eine bereits versendete ShippingGroup könnte Items einer gelöschten Order enthalten.

**Risiko:**
- ShippingGroups enthalten Items von gelöschten Orders
- PDFs und Lieferanten-Emails enthalten ungültige Positionen

**Empfehlung:**
Beim Order-Löschen: OrderItems aus ShippingGroups entfernen (shipping_group_id = NULL setzen). Leere ShippingGroups ggf. automatisch stornieren.

---

### L-03: OrderItem-Löschung hinterlässt leere ShippingGroups

- **Datei:** `app/routers/order_items.py:74-99`
- **Severity:** 🟡 Medium
- **Kategorie:** Logic – Bestellprozess

**Beschreibung:**
Beim Löschen eines OrderItems (`DELETE /order-items/{id}`) wird das Item gelöscht, aber die zugehörige ShippingGroup wird nicht geprüft. Wenn es das letzte Item der ShippingGroup war, bleibt eine leere ShippingGroup bestehen.

**Risiko:**
- Leere ShippingGroups können freigegeben werden → leere PDFs / Emails
- Dateninkonsistenz in der Übersicht

**Empfehlung:**
Nach dem Löschen eines OrderItems prüfen, ob die ShippingGroup noch Items hat. Falls leer, ShippingGroup automatisch entfernen oder als storniert markieren.

---

### L-04: Department-Zyklen nur direkt verhindert

- **Datei:** `app/routers/department.py:77-78`
- **Severity:** 🟡 Medium
- **Kategorie:** Logic – Department-Hierarchie

**Beschreibung:**
Beim Update wird nur geprüft ob `parent_id == id` (sich selbst als Parent). Indirekte Zyklen (A→B→A) werden nicht erkannt. `_get_editable_departments()` in `order_service.py:30-48` nutzt Rekursion ohne Zyklen-Schutz → potenzielle Endlosrekursion.

**Risiko:**
Wenn ein Admin einen Zyklus erstellt (A.parent=B, dann B.parent=A), stürzen alle rekursiven Department-Funktionen ab (RecursionError).

**Empfehlung:**
Beim Department-Update die gesamte Kette nach oben traversieren und prüfen, ob der neue Parent ein Nachfahre des aktuellen Departments ist:
```python
def _would_create_cycle(db, department_id, new_parent_id):
    current = new_parent_id
    visited = set()
    while current:
        if current == department_id:
            return True
        if current in visited:
            return True  # Bestehender Zyklus
        visited.add(current)
        parent = db.query(Department).filter(Department.id == current).first()
        current = parent.parent_id if parent else None
    return False
```

---

### L-05: _is_descendant_of crasht bei nicht existierendem Department

- **Datei:** `app/services/order_service.py:77-87`
- **Severity:** 🟡 Medium
- **Kategorie:** Logic – Fehlerbehandlung

**Beschreibung:**
```python
def _is_descendant_of(department_id, ancestor_id, db):
    department = db.query(Department).filter(Department.id == department_id).first()
    if department_id == ancestor_id:
        return True
    while department.parent_id:  # AttributeError wenn department is None
```
Wenn `department_id` nicht in der DB existiert, ist `department = None` und Zeile 83 crasht mit `AttributeError: 'NoneType' object has no attribute 'parent_id'`.

**Risiko:**
500 Internal Server Error bei ungültiger Department-ID.

**Empfehlung:**
```python
if not department:
    return False
```
nach der Query einfügen.

---

### L-06: Feiertage auf 2026-2028 und Schleswig-Holstein hardcodiert

- **Datei:** `app/services/order_service.py:93`
- **Severity:** 🟡 Medium
- **Kategorie:** Logic – Konfiguration

**Beschreibung:**
```python
sh_holidays = holidays.Germany(state="SH", years=[2026, 2027, 2028])
```
- Ab 2029 werden Feiertage bei der Lieferdatum-Berechnung nicht mehr berücksichtigt
- Bundesland ist hartcodiert auf Schleswig-Holstein

**Risiko:**
Ab 2029 werden Lieferungen auf Feiertage gelegt. Bei Standortwechsel stimmen die Feiertage nicht.

**Empfehlung:**
Dynamische Jahreszahlen und Bundesland aus der Konfiguration:
```python
current_year = date.today().year
holidays_de = holidays.Germany(
    state=settings.holiday_state,  # Neue Config-Variable
    years=[current_year, current_year + 1]
)
```

---

### L-07: Activities-Endpoint filtert Admin nicht korrekt

- **Datei:** `app/routers/activities.py:20-42`
- **Severity:** 🟡 Medium
- **Kategorie:** Logic – Authorization

**Beschreibung:**
`GET /activities/` filtert Activities für **alle** User (inkl. Admin) über `_get_visible_departments()`. Im Gegensatz dazu sehen Admins bei `GET /orders/` alle Departments. Ein Admin sieht also alle Orders, aber nicht alle zugehörigen Activities.

**Risiko:**
Admin hat keine vollständige Sicht auf alle Systemaktivitäten.

**Empfehlung:**
Admin-Bypass ergänzen:
```python
if user.role.name == "Admin":
    # Kein Department-Filter für Admin
    activities = db.query(ActivityLog)...
else:
    visible = _get_visible_departments(db, user.department_id)
    ...
```

---

### L-08: get_order Einzelabruf nutzt strengeren Check als get_orders Liste

- **Datei:** `app/routers/orders.py:108-129` vs `app/routers/orders.py:68-105`
- **Severity:** 🟡 Medium
- **Kategorie:** Logic – Authorization

**Beschreibung:**
`GET /orders/` erlaubt Non-Admin-Usern die Sicht auf Orders von Parent-, Geschwister- und Child-Departments (via `_get_visible_departments`). `GET /orders/{id}` prüft aber nur `order.department_id != current_user.department_id` – d.h. nur das eigene Department.

Ein User sieht eine Order in der Liste, bekommt aber 404 beim Einzelabruf.

**Risiko:**
Inkonsistentes Verhalten; Frontend-Bugs wenn eine Order aus der Liste angeklickt wird.

**Empfehlung:**
In `get_order` den gleichen `_get_visible_departments`-Check verwenden:
```python
if current_user.role.name != "Admin":
    visible = _get_visible_departments(db, current_user.department_id)
    if order.department_id not in visible:
        raise HTTPException(status_code=404, ...)
```

---

### L-09: add_item_to_order nutzt strengeren Check als create_order

- **Datei:** `app/services/order_service.py:224`
- **Severity:** 🟡 Medium
- **Kategorie:** Logic – Authorization

**Beschreibung:**
`create_order` erlaubt Bestellungen für Nachfahren-Departments (via `_is_descendant_of`). `add_item_to_order` prüft aber nur `order.department_id != current_user.department_id` (nur eigenes Department).

Ein User kann eine Order für ein Child-Department erstellen, aber danach keine Items mehr hinzufügen.

**Risiko:**
Funktionaler Bug: Bestellablauf für Child-Departments ist kaputt.

**Empfehlung:**
`_can_edit_order()` (das `_get_editable_departments` nutzt) statt des direkten Department-Vergleichs verwenden.

---

### L-10: Race Condition bei ShippingGroup-Erstellung

- **Datei:** `app/services/order_service.py:153-168`, `app/routers/order_items.py:167-183`
- **Severity:** 🔵 Low
- **Kategorie:** Logic – Concurrency

**Beschreibung:**
Die ShippingGroup-Suche und -Erstellung ist nicht atomar:
```python
shipping_group = db.query(ShippingGroup).filter(...).first()
if not shipping_group:
    new_shipping_group = ShippingGroup(...)
    db.add(new_shipping_group)
```
Bei gleichzeitigen Requests für den gleichen Lieferanten + Lieferdatum könnten doppelte ShippingGroups entstehen.

**Risiko:**
Doppelte ShippingGroups für den gleichen Lieferanten/Tag. Für ein internes Tool mit wenigen gleichzeitigen Nutzern gering.

**Empfehlung:**
Unique-Constraint auf (`supplier_id`, `delivery_date`, `status=OFFEN`) oder `SELECT ... FOR UPDATE`.

---

### L-11: Department-Löschung zählt inaktive Children mit

- **Datei:** `app/routers/department.py:95-102`
- **Severity:** 🔵 Low
- **Kategorie:** Logic – Soft Delete

**Beschreibung:**
```python
department = db.query(Department).options(
    joinedload(Department.children)  # Lädt ALLE Children inkl. inaktive
).filter(Department.id == id, Department.is_active == True).first()
if department.children:  # True auch wenn alle Children inaktiv sind
    raise HTTPException(status_code=400, detail="Bereich hat aktive Unterbereiche")
```
`joinedload(Department.children)` lädt alle Children (auch `is_active=False`). Die Fehlermeldung sagt "aktive Unterbereiche", aber es werden alle geprüft.

**Risiko:**
Departments mit nur inaktiven Children können nicht gelöscht werden.

**Empfehlung:**
Explicit filtern:
```python
active_children = db.query(Department).filter(
    Department.parent_id == id,
    Department.is_active == True
).count()
if active_children > 0:
    raise HTTPException(...)
```

---

### L-12: article_groups gibt inaktive Gruppen zurück

- **Datei:** `app/routers/article_groups.py:14-16`
- **Severity:** 🔵 Low
- **Kategorie:** Logic – Soft Delete

**Beschreibung:**
```python
def get_all_article_groups(...):
    return db.query(ArticleGroup).all()  # Kein is_active-Filter
```
Im Gegensatz zu anderen Entities (Suppliers, Departments, Users) werden inaktive ArticleGroups in der Liste angezeigt.

**Risiko:**
Deaktivierte Artikelgruppen erscheinen in Dropdowns/Auswahllisten.

**Empfehlung:**
`is_active`-Filter hinzufügen oder optional als Query-Parameter anbieten.

---

### L-13: HTTP 402 statt 401 in require_role Decorator

- **Datei:** `app/utils/security.py:83`
- **Severity:** 🔵 Low
- **Kategorie:** Logic – HTTP Semantik

**Beschreibung:**
```python
if not current_user:
    raise HTTPException(status_code=402, detail="Nicht eingeloggt")
```
HTTP 402 ist "Payment Required" und für zukünftige Nutzung reserviert. Korrekt wäre 401 (Unauthorized).

**Risiko:**
Kein Sicherheitsrisiko; Frontend muss ggf. auf unerwarteten Status-Code reagieren.

**Empfehlung:**
Status-Code auf 401 ändern.

---

### L-14: delivery_days Delete gibt 403 statt 404

- **Datei:** `app/routers/delivery_days.py:52`
- **Severity:** 🔵 Low
- **Kategorie:** Logic – HTTP Semantik

**Beschreibung:**
```python
if not delivery_day:
    raise HTTPException(status_code=403, detail="Liefertag nicht gefunden")
```
"Nicht gefunden" sollte 404 sein, nicht 403 (Forbidden).

**Risiko:**
Irreführender Fehlercode für Frontend.

**Empfehlung:**
`status_code=404`.

---

## Code-Fehler (Syntax/Runtime)

---

### C-01: Syntax-Fehler in article.py – IndentationError

- **Datei:** `app/routers/article.py:37-44`
- **Severity:** 🔴 Critical
- **Kategorie:** Code – Syntax Error

**Beschreibung:**
```python
if supplier_id:
    article_ids = db.query(ArticleSupplier.article_id).filter(
            ArticleSupplier.supplier_id == supplier_id)
            query = query.filter(Article.id.in_(article_ids))  # IndentationError
```
Nach der schließenden `)` auf der vorherigen Zeile ist die Einrückung der nächsten Zeile zu tief (16 Spaces statt 8). Dies verursacht einen `IndentationError`. Gleicher Fehler bei `storage_location_id`-Filter (Zeile 42-44).

**Risiko:**
Modul kann nicht importiert werden → **gesamte Applikation startet nicht**.

**Empfehlung:**
Korrekte Einrückung:
```python
if supplier_id:
    article_ids = db.query(ArticleSupplier.article_id).filter(
            ArticleSupplier.supplier_id == supplier_id)
    query = query.filter(Article.id.in_(article_ids))
```

---

### C-02: Unvollständiger Endpoint in orders.py

- **Datei:** `app/routers/orders.py:233-234`
- **Severity:** 🔴 Critical
- **Kategorie:** Code – Syntax Error

**Beschreibung:**
Die Datei endet mit einer unvollständigen Funktionsdefinition:
```python
@router.get("/{id}/activities")
def get
```
Die Funktion hat keinen Funktionsnamen, keine Parameter und keinen Body → `SyntaxError`.

**Risiko:**
Modul kann nicht importiert werden → **gesamte Applikation startet nicht**.

**Empfehlung:**
Entweder vervollständigen oder entfernen. Ein funktionierender Activity-Endpoint existiert bereits unter `GET /activities/order/{id}`.

---

### C-03: Unvollständiger Endpoint in shipping_groups.py

- **Datei:** `app/routers/shipping_groups.py:255-274`
- **Severity:** 🔴 Critical
- **Kategorie:** Code – Syntax Error

**Beschreibung:**
Die Funktion `get_shipping_group_order` hat mehrere Probleme:
1. Die Query ruft nicht `.first()` auf – `shipping_group` ist ein Query-Objekt, kein Model
2. `for order in shipping_group:` iteriert über ShippingGroup-Objekte (falscher Variablenname)
3. Der Loop-Body ist leer → `SyntaxError`

```python
shipping_group = db.query(ShippingGroup).options(...).filter(ShippingGroup.id == id)
# Fehlt: .first()
if not shipping_group:  # Query ist immer truthy
    raise HTTPException(...)
for order in shipping_group:  # Falscher Variablenname + leerer Body
```

**Risiko:**
Modul kann nicht importiert werden → **gesamte Applikation startet nicht**.

**Empfehlung:**
Funktion entweder korrekt implementieren oder entfernen (falls noch in Entwicklung).

---

## Zusammenfassung

### Findings nach Severity

| Severity | Anzahl |
|---|---|
| 🔴 Critical | 6 |
| 🟠 High | 5 |
| 🟡 Medium | 9 |
| 🔵 Low | 6 |
| **Gesamt** | **26** |

### Aufschlüsselung

| Kategorie | Critical | High | Medium | Low |
|---|---|---|---|---|
| Security – Authentication | 2 | 2 | 1 | 1 |
| Security – Authorization | – | 1 | 1 | – |
| Security – Konfiguration | 1 | – | 1 | – |
| Security – Input Validation | – | – | 1 | 1 |
| Security – Data Integrity | – | – | 1 | – |
| Security – DoS | – | – | – | 1 |
| Logic – Bestellprozess | – | 2 | 1 | 1 |
| Logic – Authorization | – | – | 3 | – |
| Logic – Department-Hierarchie | – | – | 1 | 1 |
| Logic – Fehlerbehandlung | – | – | 1 | – |
| Logic – Konfiguration | – | – | 1 | – |
| Logic – Soft Delete | – | – | – | 1 |
| Logic – HTTP Semantik | – | – | – | 2 |
| Code – Syntax Error | 3 | – | – | – |

### Top 3 Prioritäten (sofort fixen)

**1. Syntax-Fehler beheben (C-01, C-02, C-03)**
Drei Dateien (`article.py`, `orders.py`, `shipping_groups.py`) enthalten Syntax-Fehler, die den Start der Applikation verhindern. Diese müssen zuerst behoben werden, bevor das System überhaupt lauffähig ist.

**2. Deaktivierte User können weiter agieren (S-01, S-02, S-04)**
`get_current_user()` prüft nicht `is_active`. In Kombination mit dem Refresh-Endpoint (der den User gar nicht aus der DB lädt) können deaktivierte User unbegrenzt weiter arbeiten. Fix: `is_active`-Check in `get_current_user()` und User-Laden im Refresh-Endpoint.

**3. CORS-Konfiguration einschränken (S-03)**
`allow_origins=["*"]` mit `allow_credentials=True` erlaubt jedem Webserver, authentifizierte Requests im Namen eingeloggter User zu senden. Fix: Explizite Origin-Liste konfigurieren.

### Generelle Empfehlungen

1. **Einheitliche Access-Control-Funktionen:** Die Department-basierte Zugriffskontrolle ist über mehrere Stellen verstreut (`_get_visible_departments`, `_get_editable_departments`, `_can_edit_order`, direkte Department-Vergleiche). Eine zentrale Zugriffs-Schicht würde die Konsistenz sicherstellen.

2. **Token-Invalidierungs-Mechanismus:** Einen `token_version`-Counter im User-Model einführen. Wird bei Passwort-Änderung oder Deaktivierung inkrementiert und beim Token-Decoding geprüft.

3. **Pagination standardisieren:** `skip`/`limit` mit vernünftigem Default und Maximum auf allen List-Endpoints.

4. **Status-Maschine für Orders:** Die erlaubten Status-Übergänge (ENTWURF → VOLLSTAENDIG → BESTELLT → STORNIERT) explizit modellieren und zentral durchsetzen, anstatt Checks in einzelnen Endpoints zu verteilen.

5. **ShippingGroup-Lifecycle koppeln:** Die Verbindung zwischen Order-Status, OrderItem-Zuordnung und ShippingGroup-Status ist fragil. Klare Regeln definieren: Was passiert mit ShippingGroups wenn Orders/Items gelöscht werden? Wann werden Orders auf BESTELLT gesetzt?

6. **SQL Injection:** Kein Befund. Das gesamte Backend nutzt SQLAlchemy ORM mit parametrisierten Queries. Keine Raw-SQL-Statements gefunden.

7. **Data Exposure:** Kein kritischer Befund. Response-Schemas (`UserResponse`, etc.) filtern sensible Felder (`password_hash`, `totp_secret`) korrekt heraus. Der 2FA-Setup-Endpoint gibt das TOTP-Secret bewusst zurück (für QR-Code-Generierung).

8. **Secrets-Konfiguration:** Korrekt implementiert via `pydantic_settings.BaseSettings` und `.env`-Datei. Keine hardcodierten Secrets im Code. `debug`-Modus defaultet auf `False`.
