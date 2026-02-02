"""
Pytest Fixtures für das Bestellsystem.

Fixtures sind wiederverwendbare Setup-Funktionen für Tests.
Sie werden automatisch von pytest erkannt und injiziert.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4 

from app.main import app
...
from app.database import Base, get_db
from app.models import User, Role, Department, Supplier, Article, ArticleGroup, ApproverSupplier
from app.utils.security import hash_password


# ============ DATENBANK SETUP ============

# PostgreSQL Test-Datenbank
# Passe user/password an deine lokale Konfiguration an!
SQLALCHEMY_TEST_DATABASE_URL = "postgresql://testuser:testpass@localhost/bestellsystem_test"

engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ============ BASIS FIXTURES ============

@pytest.fixture(scope="function")
def db():
    """
    Erstellt eine frische Datenbank für jeden Test.
    
    scope="function" bedeutet: Für JEDEN Test neu erstellen.
    Das ist langsamer, aber Tests beeinflussen sich nicht gegenseitig.
    """
    # Tabellen erstellen
    Base.metadata.create_all(bind=engine)
    
    # Session erstellen
    db = TestingSessionLocal()
    
    try:
        yield db  # Test läuft hier
    finally:
        db.close()
        # Tabellen löschen (Clean Slate für nächsten Test)
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """
    FastAPI TestClient mit überschriebener Datenbank.
    
    Wichtig: Wir überschreiben get_db, damit die App
    unsere Test-DB verwendet statt der echten!
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    # Dependency überschreiben
    app.dependency_overrides[get_db] = override_get_db
    
    # TestClient erstellen
    with TestClient(app) as test_client:
        yield test_client
    
    # Aufräumen
    app.dependency_overrides.clear()


# ============ STAMMDATEN FIXTURES ============

@pytest.fixture
def role_admin(db):
    """Erstellt Admin-Rolle"""
    role = Role(id=uuid4(), name="Admin")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture
def role_freigeber(db):
    """Erstellt Freigeber-Rolle"""
    role = Role(id=uuid4(), name="Freigeber")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture
def role_bedarfsmelder(db):
    """Erstellt Bedarfsmelder-Rolle"""
    role = Role(id=uuid4(), name="Bedarfsmelder")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture
def department(db):
    """Erstellt Test-Department"""
    dept = Department(id=uuid4(), name="Test-Küche", is_active=True)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@pytest.fixture
def supplier(db):
    """Erstellt Test-Lieferant"""
    sup = Supplier(
        id=uuid4(),
        name="Test Gemüsehändler",
        email="gemuese@test.de",
        is_active=True,
        fixed_delivery_days=False
    )
    db.add(sup)
    db.commit()
    db.refresh(sup)
    return sup


@pytest.fixture
def article_group(db):
    """Erstellt Test-Artikelgruppe"""
    group = ArticleGroup(id=uuid4(), name="Gemüse", is_active=True)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@pytest.fixture
def article(db, article_group):
    """Erstellt Test-Artikel"""
    art = Article(
        id=uuid4(),
        name="Karotten",
        unit="kg",
        article_group_id=article_group.id,
        is_active=True
    )
    db.add(art)
    db.commit()
    db.refresh(art)
    return art


# ============ USER FIXTURES ============

@pytest.fixture
def admin_user(db, role_admin, department):
    """Erstellt Admin-User (ohne 2FA)"""
    user = User(
        id=uuid4(),
        name="Test Admin",  # ← HINZUFÜGEN
        email="admin@test.com",
        password_hash=hash_password("adminpass123"),
        role_id=role_admin.id,
        department_id=department.id,
        is_active=True,
        is_2fa_enabled=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def freigeber_user(db, role_freigeber, department):
    """Erstellt Freigeber-User (ohne 2FA)"""
    user = User(
        id=uuid4(),
        name="Test Freigeber",  # ← HINZUFÜGEN
        email="freigeber@test.com",
        password_hash=hash_password("freigeberpass123"),
        role_id=role_freigeber.id,
        department_id=department.id,
        is_active=True,
        is_2fa_enabled=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def bedarfsmelder_user(db, role_bedarfsmelder, department):
    """Erstellt Bedarfsmelder-User (ohne 2FA)"""
    user = User(
        id=uuid4(),
        name="Test Koch",  # ← HINZUFÜGEN
        email="koch@test.com",
        password_hash=hash_password("kochpass123"),
        role_id=role_bedarfsmelder.id,
        department_id=department.id,
        is_active=True,
        is_2fa_enabled=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ============ AUTH TOKEN FIXTURES ============

@pytest.fixture
def admin_token(client, admin_user):
    """Login als Admin, gibt Token zurück"""
    response = client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "adminpass123"
    })
    assert response.status_code == 200, f"Admin login failed: {response.json()}"
    return response.json()["access_token"]


@pytest.fixture
def freigeber_token(client, freigeber_user):
    """Login als Freigeber, gibt Token zurück"""
    response = client.post("/auth/login", json={
        "email": "freigeber@test.com",
        "password": "freigeberpass123"
    })
    assert response.status_code == 200, f"Freigeber login failed: {response.json()}"
    return response.json()["access_token"]


@pytest.fixture
def bedarfsmelder_token(client, bedarfsmelder_user):
    """Login als Bedarfsmelder, gibt Token zurück"""
    response = client.post("/auth/login", json={
        "email": "koch@test.com",
        "password": "kochpass123"
    })
    assert response.status_code == 200, f"Bedarfsmelder login failed: {response.json()}"
    return response.json()["access_token"]


# ============ HELPER FUNKTIONEN ============

def auth_header(token: str) -> dict:
    """Erstellt Authorization Header"""
    return {"Authorization": f"Bearer {token}"}