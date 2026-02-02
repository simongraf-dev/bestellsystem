"""
Tests für ApproverSupplier Endpoints.

Testet:
- GET /approver-suppliers/ (Liste)
- POST /approver-suppliers/ (Erstellen)
- DELETE /approver-suppliers/ (Löschen)
"""
import pytest
from uuid import uuid4

from app.models import ApproverSupplier, Supplier, User
from tests.conftest import auth_header


# ============ GET TESTS ============

class TestGetApproverSuppliers:
    """Tests für GET /approver-suppliers/"""
    
    def test_get_all_empty(self, client, admin_token):
        """Leere Liste wenn keine Berechtigungen existieren"""
        response = client.get(
            "/approver-suppliers/",
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_all_with_data(self, client, admin_token, db, freigeber_user, supplier):
        """Liste mit Daten"""
        # Arrange: Berechtigung erstellen
        approver = ApproverSupplier(
            user_id=freigeber_user.id,
            supplier_id=supplier.id
        )
        db.add(approver)
        db.commit()
        
        # Act
        response = client.get(
            "/approver-suppliers/",
            headers=auth_header(admin_token)
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["user"]["email"] == "freigeber@test.com"
        assert data[0]["supplier"]["name"] == "Test Gemüsehändler"
    
    def test_get_filtered_by_user(self, client, admin_token, db, freigeber_user, bedarfsmelder_user, supplier):
        """Filter nach User ID"""
        # Arrange: Zwei Berechtigungen für verschiedene User
        db.add(ApproverSupplier(user_id=freigeber_user.id, supplier_id=supplier.id))
        
        # Zweiten Supplier erstellen
        supplier2 = Supplier(id=uuid4(), name="Bäcker", is_active=True, fixed_delivery_days=False)
        db.add(supplier2)
        db.commit()
        
        db.add(ApproverSupplier(user_id=bedarfsmelder_user.id, supplier_id=supplier2.id))
        db.commit()
        
        # Act: Nur für Freigeber filtern
        response = client.get(
            f"/approver-suppliers/?user_id={freigeber_user.id}",
            headers=auth_header(admin_token)
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["user"]["email"] == "freigeber@test.com"
    
    def test_get_filtered_by_supplier(self, client, admin_token, db, freigeber_user, supplier):
        """Filter nach Supplier ID"""
        # Arrange
        db.add(ApproverSupplier(user_id=freigeber_user.id, supplier_id=supplier.id))
        db.commit()
        
        # Act
        response = client.get(
            f"/approver-suppliers/?supplier_id={supplier.id}",
            headers=auth_header(admin_token)
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["supplier"]["name"] == "Test Gemüsehändler"
    
    def test_get_without_auth(self, client):
        """Ohne Login → 401"""
        response = client.get("/approver-suppliers/")
        assert response.status_code == 401


# ============ POST TESTS ============

class TestCreateApproverSupplier:
    """Tests für POST /approver-suppliers/"""
    
    def test_create_success(self, client, admin_token, freigeber_user, supplier):
        """Admin kann Berechtigung erstellen"""
        response = client.post(
            "/approver-suppliers/",
            json={
                "user_id": str(freigeber_user.id),
                "supplier_id": str(supplier.id)
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "freigeber@test.com"
        assert data["supplier"]["name"] == "Test Gemüsehändler"
    
    def test_create_duplicate(self, client, admin_token, db, freigeber_user, supplier):
        """Doppelte Berechtigung → Fehler"""
        # Arrange: Berechtigung existiert schon
        db.add(ApproverSupplier(user_id=freigeber_user.id, supplier_id=supplier.id))
        db.commit()
        
        # Act: Nochmal erstellen versuchen
        response = client.post(
            "/approver-suppliers/",
            json={
                "user_id": str(freigeber_user.id),
                "supplier_id": str(supplier.id)
            },
            headers=auth_header(admin_token)
        )
        
        # Assert
        assert response.status_code == 400
        assert "existiert bereits" in response.json()["detail"]
    
    def test_create_user_not_found(self, client, admin_token, supplier):
        """User existiert nicht → 404"""
        response = client.post(
            "/approver-suppliers/",
            json={
                "user_id": str(uuid4()),  # Fake ID
                "supplier_id": str(supplier.id)
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404
        assert "User" in response.json()["detail"]
    
    def test_create_supplier_not_found(self, client, admin_token, freigeber_user):
        """Supplier existiert nicht → 404"""
        response = client.post(
            "/approver-suppliers/",
            json={
                "user_id": str(freigeber_user.id),
                "supplier_id": str(uuid4())  # Fake ID
            },
            headers=auth_header(admin_token)
        )
        
        assert response.status_code == 404
        assert "Lieferant" in response.json()["detail"]
    
    def test_create_without_auth(self, client, freigeber_user, supplier):
        """Ohne Login → 401"""
        response = client.post(
            "/approver-suppliers/",
            json={
                "user_id": str(freigeber_user.id),
                "supplier_id": str(supplier.id)
            }
        )
        assert response.status_code == 401
    
    def test_create_not_admin(self, client, bedarfsmelder_token, freigeber_user, supplier):
        """Nicht-Admin → 403"""
        response = client.post(
            "/approver-suppliers/",
            json={
                "user_id": str(freigeber_user.id),
                "supplier_id": str(supplier.id)
            },
            headers=auth_header(bedarfsmelder_token)
        )
        assert response.status_code == 403


# ============ DELETE TESTS ============

class TestDeleteApproverSupplier:
    """Tests für DELETE /approver-suppliers/"""
    
    def test_delete_success(self, client, admin_token, db, freigeber_user, supplier):
        """Admin kann Berechtigung löschen"""
        # Arrange
        db.add(ApproverSupplier(user_id=freigeber_user.id, supplier_id=supplier.id))
        db.commit()
        
        # Act
        response = client.delete(
            f"/approver-suppliers/?user_id={freigeber_user.id}&supplier_id={supplier.id}",
            headers=auth_header(admin_token)
        )
        
        # Assert
        assert response.status_code == 200
        assert "gelöscht" in response.json()["message"]
        
        # Prüfen dass wirklich weg
        remaining = db.query(ApproverSupplier).all()
        assert len(remaining) == 0
    
    def test_delete_not_found(self, client, admin_token):
        """Berechtigung existiert nicht → 404"""
        response = client.delete(
            f"/approver-suppliers/?user_id={uuid4()}&supplier_id={uuid4()}",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 404
    
    def test_delete_without_auth(self, client, freigeber_user, supplier):
        """Ohne Login → 401"""
        response = client.delete(
            f"/approver-suppliers/?user_id={freigeber_user.id}&supplier_id={supplier.id}"
        )
        assert response.status_code == 401
    
    def test_delete_not_admin(self, client, bedarfsmelder_token, db, freigeber_user, supplier):
        """Nicht-Admin → 403"""
        # Arrange
        db.add(ApproverSupplier(user_id=freigeber_user.id, supplier_id=supplier.id))
        db.commit()
        
        # Act
        response = client.delete(
            f"/approver-suppliers/?user_id={freigeber_user.id}&supplier_id={supplier.id}",
            headers=auth_header(bedarfsmelder_token)
        )
        
        # Assert
        assert response.status_code == 403