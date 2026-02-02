"""
Tests für Suppliers Endpoints.

Testet:
- GET /suppliers/
- GET /suppliers/{id}
- POST /suppliers/
- PATCH /suppliers/{id}
- DELETE /suppliers/{id}
"""
import pytest
from uuid import uuid4

from app.models import Supplier
from tests.conftest import auth_header


class TestGetSuppliers:
    """Tests für GET /suppliers/"""
    
    def test_get_suppliers_with_data(self, client, admin_token, supplier):
        """Liste mit Lieferanten"""
        response = client.get(
            "/suppliers/",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(s["name"] == "Test Gemüsehändler" for s in data)
    
    def test_get_suppliers_search(self, client, admin_token, supplier):
        """Suche nach Namen"""
        response = client.get(
            "/suppliers/?name=Gemüse",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
    
    def test_get_suppliers_without_auth(self, client):
        """Ohne Login → 401"""
        response = client.get("/suppliers/")
        assert response.status_code == 401


class TestGetSupplierById:
    """Tests für GET /suppliers/{id}"""
    
    def test_get_supplier_success(self, client, admin_token, supplier):
        """Einzelnen Lieferanten abrufen"""
        response = client.get(
            f"/suppliers/{supplier.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Gemüsehändler"
        assert data["email"] == "gemuese@test.de"
    
    def test_get_supplier_not_found(self, client, admin_token):
        """Lieferant nicht gefunden → 404"""
        response = client.get(
            f"/suppliers/{uuid4()}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404


class TestCreateSupplier:
    """Tests für POST /suppliers/"""
    
    def test_create_supplier_success(self, client, admin_token):
        """Admin kann Lieferanten erstellen"""
        response = client.post(
            "/suppliers/",
            json={
                "name": "Bäckerei Müller",
                "email": "info@baeckerei-mueller.de",
                "phone": "0123-456789",
                "fixed_delivery_days": False
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Bäckerei Müller"
        assert data["email"] == "info@baeckerei-mueller.de"
        assert data["is_active"] == True
    
    def test_create_supplier_with_fixed_days(self, client, admin_token):
        """Lieferant mit festen Liefertagen"""
        response = client.post(
            "/suppliers/",
            json={
                "name": "Fleischerei Schmidt",
                "fixed_delivery_days": True
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["fixed_delivery_days"] == True
    
    def test_create_supplier_not_admin(self, client, bedarfsmelder_token):
        """Nicht-Admin kann keine Lieferanten erstellen → 403"""
        response = client.post(
            "/suppliers/",
            json={
                "name": "Versuch",
                "fixed_delivery_days": False
            },
            headers=auth_header(bedarfsmelder_token)
        )
        
        assert response.status_code == 403


class TestUpdateSupplier:
    """Tests für PATCH /suppliers/{id}"""
    
    def test_update_supplier_success(self, client, admin_token, supplier):
        """Admin kann Lieferanten bearbeiten"""
        response = client.patch(
            f"/suppliers/{supplier.id}",
            json={"name": "Bio-Gemüsehändler"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Bio-Gemüsehändler"
    
    def test_update_supplier_email(self, client, admin_token, supplier):
        """Email ändern"""
        response = client.patch(
            f"/suppliers/{supplier.id}",
            json={"email": "neu@gemuese.de"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "neu@gemuese.de"
    
    def test_update_supplier_not_found(self, client, admin_token):
        """Lieferant nicht gefunden → 404"""
        response = client.patch(
            f"/suppliers/{uuid4()}",
            json={"name": "Test"},
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404


class TestDeleteSupplier:
    """Tests für DELETE /suppliers/{id}"""
    
    def test_delete_supplier_success(self, client, admin_token, db):
        """Admin kann Lieferanten löschen (Soft Delete)"""
        # Neuen Lieferanten zum Löschen erstellen
        sup = Supplier(
            id=uuid4(),
            name="Zum Löschen",
            is_active=True,
            fixed_delivery_days=False
        )
        db.add(sup)
        db.commit()
        
        response = client.delete(
            f"/suppliers/{sup.id}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        
        # Prüfen ob deaktiviert
        db.refresh(sup)
        assert sup.is_active == False
    
    def test_delete_supplier_not_found(self, client, admin_token):
        """Lieferant nicht gefunden → 404"""
        response = client.delete(
            f"/suppliers/{uuid4()}",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404